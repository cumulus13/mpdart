#!/usr/bin/env python
# encoding:utf-8
# Author: cumulus13
# email: cumulus13@gmail.com

from __future__ import print_function

#from netifaces import interfaces, ifaddresses, AF_INET
from make_colors import make_colors
from pydebugger.debug import debug
from multiprocessing import Pool
from progressbar import ProgressBar
import re
import shutil
#import socket
import os
import io
from PIL import Image
import sys
import signal
import time
#import base64
import http.server as SimpleHTTPServer
import socketserver as SocketServer
try:
    from mutagen.id3 import ID3
    from mutagen.flac import FLAC
    MUTAGEN = True
except ImportError:
    MUTAGEN = False
    
import requests
from datetime import datetime, timedelta
if sys.version_info.major == 3:
    raw_input = input
import traceback
import argparse
import qdarkstyle
import qtmodern.styles
import qtmodern.windows
from qt_material import apply_stylesheet
try:
    from pause import pause
except:
    def pause(*args, **kwargs):
        return None
NOTIFY2 = False
if not sys.platform == 'win32':
    try:
        import notify2 as pynotify
        NOTIFY2 = True
        if not pynotify.init("MPD status"):
            logger.error("warning: Unable to initialize dbus Notifications")
    except:
        NOTIFY2 = False

from PyQt5 import Qt
from PyQt5.Qt import QStandardItemModel, QStandardItem, QKeySequence
from PyQt5.QtGui import QPixmap, QImage, QIcon, QFont, QColor
from PyQt5.QtWidgets import QDialog, QApplication, QLabel, QTableWidgetItem, QAbstractScrollArea, QAbstractItemView, QTableWidget, QHeaderView, QPushButton, QScrollArea, QWidget, QShortcut, QGraphicsPixmapItem, QGraphicsScene

from PyQt5.QtCore import *
#from PyQt5.QtWebEngineWidgets import QWebEnginePage
try:
    from .gui import *
except:
    from gui import *

import ast, json
#from jsoncolor import jprint
from configset import configset
from mpd import MPDClient
import mpd
try:
    from xnotify import notify
    XNOTIFY = True
except:
    XNOTIFY = False
try:
    from . import mimelist
except:
    import mimelist

import logging

class CustomFormatter(logging.Formatter):

    info = "\x1b[32;20m"
    debug = "\x1b[33;20m"
    fatal = "\x1b[44;97m"
    error = "\x1b[41;97m"
    warning = "\x1b[43;30m"
    critical = "\x1b[45;97m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(process)d - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: debug + format + reset,
        logging.INFO: info + format + reset,
        logging.WARNING: warning + format + reset,
        logging.ERROR: error + format + reset,
        logging.CRITICAL: critical + format + reset, 
        logging.FATAL: fatal + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

#log_format = '%(name)s %(asctime)s %(process)d - %(levelname)s - %(message)s'
#logging.basicConfig(format = log_format)
logger = logging.getLogger('MPD-Art')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)

MPD_HOST = ''
MPD_PORT = 6600
MPD_MUSIC_DIR = '' 
MPD_SLEEP = 1
APP = 'MPD-Art'
CONFIGFILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'mpdart.ini')
CONFIG = configset(CONFIGFILE)
MOD_MASK = (Qt.CTRL | Qt.ALT | Qt.SHIFT | Qt.META)

class MPD(object):
    cover = ''
    CONFIG = CONFIG
    host = CONFIG.get_config('mpd', 'host') or MPD_HOST or os.getenv('MPD_HOST') or '127.0.0.1'
    port = CONFIG.get_config('mpd', 'port') or MPD_PORT or os.getenv('MPD_PORT') or 6600
    debug(host = host)
    debug(port = port)
    music_dir = CONFIG.get_config('mpd', 'music_dir')
    
    jump_from = None
    jump_to = None
    
    sleep = CONFIG.get_config('sleep', 'time') or 1000
    icon = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'icon.png')
    timeout = CONFIG.get_config('mpd', 'timeout')
    CONN = MPDClient()
    debug(host = host)
    debug(port = port)
    #try:
        #CONN.connect(host, port)
    #except:
        #pass
    
    DEFAULT_COVER = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'no-cover.png')
    current_song = {}    
    COVER_TEMP_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'covers')
    FAIL_LAST_FM = False
    current_state = {}
    first = False
    process = None
    process1 = None
    first_current_song = False
    first_state = False
    
    @classmethod
    def conn(self, func, args = (), host = None, port = None, refresh = False, repeat = False):
        if host and not host == self.host or port and not port == self.port:
            debug(host = host)
            debug(port = port)            
            self.CONN.connect(host, port, self.timeout)
            self.host = host
            self.port = port
        else:
            host = host or self.host or '127.0.0.1'
            port = port or self.port or 6600
            try:
                self.CONN.connect(host, port, self.timeout)
            except:
                pass
        timeout = self.timeout or self.CONFIG.get_config('mpd', 'timeout') or None
        debug(host = host)
        debug(port = port)
        debug(timeout = timeout)
        debug(refresh = refresh)
        debug(func = func)
        #logger.debug("func: {}".format(func))

        if refresh:
            if (func == 'currentsong' and not self.first_current_song and not self.command == func) or (func == 'status' and not self.first_state and not self.command == func):
                #print("GET:", func)
                c = MPDClient()
                c.connect(host, port, timeout)
                self.first = True
                self.command = func
                return getattr(c, func)(*args)
        try:
            if str(repeat).isdigit():
                for i in range(0, repeat + int(repeat)):
                    result = getattr(self.CONN, func)(*args)
                    if result:
                        break
            self.command = func
            return getattr(self.CONN, func)(*args)
        except Exception as e:
            #if not self.first:
                #print(traceback.format_exc())
            if os.getenv('TRACEBACK') == '1' or os.getenv('TRACEBACK') == 1:
                logger.error(e)
            #time.sleep(1)
            try:
                c = MPDClient()
                c.connect(host, port, timeout)
                #if str(repeat).isdigit():
                    #for i in range(0, repeat + int(repeat)):
                        #result = getattr(c, func)(*args)
                        #if result:
                            #break
                self.command = func
                return getattr(c, func)(*args)                
            except Exception as e:
                logger.error("MPD:conn: {}".format(e))
                if not self.first:
                    #print(traceback.format_exc())
                    if os.getenv('TRACEBACK') == 1:
                        logger.error(traceback.format_exc())
                    self.first = True
            #self.first = True
                time.sleep(1)
        self.command = func
        return {}

    @classmethod
    def format_number(self, number, length = 10):
        number = str(number).strip()
        if not str(number).isdigit():
            return number
        zeros = len(str(length)) - len(number)
        r = ("0" * zeros) + str(number)
        if len(r) == 1:
            return "0" + r
        return r
    
    @classmethod
    def send_notify(self, current_song = None, current_state = None, event = 'stop', cover_art = None, app = 'MPD-Art'):
        label = ''
        track = '0'
        title = '~ no title / unknown ~'
        album = '~ no album / unknown ~'
        albumartist = '~ no albumartist / unknown ~'
        date = '~ no date / unknown ~'
        label = ''
        bitrate = ''
        genres = ''
        artist = ''
        disc = "0"
        duration = ''
        state = 'stop'
        
        debug(current_song = current_song)
        debug(current_state = current_state)
        logger.debug("current_song: {}".format(current_song))
        logger.debug("current_state: {}".format(current_state))
        
        debug(self_current_song = self.current_song)
        debug(self_current_state = self.current_state)
        logger.debug("self.current_song: {}".format(self.current_song))
        logger.debug("self.current_state: {}".format(self.current_state))        
        
        current_song = current_song or self.current_song
        current_state = current_state or self.current_state
        
        debug(current_song = current_song)
        debug(current_state = current_state)        
        logger.debug("current_song: {}".format(current_song))
        logger.debug("current_state: {}".format(current_state))        
        
        if current_song and current_state:
            track = current_song.get('track') or track or ''
            title = current_song.get('title') or title or ''
            album = current_song.get('album') or album or ''
            albumartist = current_song.get('albumartist') or albumartist or ''
            date = current_song.get('date') or date or ''
            artist = current_song.get('artist') or artist or ''
            disc = current_song.get('disc') or disc or '0'
            label = current_song.get('label') or label or ''
            duration = current_song.get('duration') or duration or ''
            genres = current_song.get('genre') or genres or ''
            state = current_state.get('state') or event or ''
            bitrate = current_state.get('bitrate') or bitrate or ''
            event = state or event or 'stop'
        
        message = track + "/" +\
            self.format_number(disc)  + ". " +\
            title + "\n" + \
            duration + "[" + bitrate + "] " + "\n" +\
            "Artist : " + artist + "\n" + \
            "Album  : " + album + "\n" + \
            "Genres : " + genres + "\n\n" + \
            state
            
        cover_art = cover_art or self.DEFAULT_COVER
        debug(cover_art = cover_art)
        debug(NOTIFY2 = NOTIFY2)
        debug(XNOTIFY = XNOTIFY)
        
        if NOTIFY2 and self.CONFIG.get_config('notification', 'notify2') == 1:
            logger.debug("send notify [LINUX]: {}".format(message))
            try:
                pnotify = pynotify.Notification("MPD-Art " + title + " " + event, message, "file://" + cover_art)
                pnotify.show()
            except:
                traceback.format_exc()
                
        if XNOTIFY and self.CONFIG.get_config('notification', 'xnotify') == 1:
            growl = self.CONFIG.get_config('xnotify', 'growl') or False
            growl_host = list(filter(None, [i.strip() for i in re.split(",|\n", self.CONFIG.get_config('xnotify', 'grow_host'))]))
            nmd = self.CONFIG.get_config('xnotify', 'nmd') or False
            nmd_api = self.CONFIG.get_config('xnotify', 'nmd_api')
            pushbullet = self.CONFIG.get_config('xnotify', 'pushbullet') or False
            pushbullet_api = self.CONFIG.get_config('xnotify', 'pushbullet_api')
            ntfy = self.CONFIG.get_config('xnotify', 'ntfy') or False
            ntfy_server = list(filter(None, [i.strip() for i in re.split(",|\n", self.CONFIG.get_config('xnotify', 'ntfy_server'))]))
            
            notify.active_growl = growl
            notify.active_nmd = nmd
            notify.active_pushbullet = pushbullet
            notify.active_ntfy = ntfy
            notify.host = growl_host
            notify.nmd_api = nmd_api
            notify.pushbullet_api = pushbullet_api
            notify.ntfy_server = ntfy_server
            logger.debug("send notify: {}".format(message))
            try:
                notify.send('MPD-Art:' + " " + (event or 'play'), message, app, event, growl_host, icon = cover_art, iconpath = cover_art, ntfy = ntfy, nfty_sever = ntfy_server, pushbullet_api = pushbullet_api, nmd_api = nmd_api, pushbullet = pushbullet, nmd = nmd, growl = growl)
            except:
                traceback.format_exc()
            logger.warning("send notification done ...")
        
    @classmethod
    def get_cover_tag(self, music_file, save_dir = None):
        debug(music_file = music_file)
        save_dir = save_dir or (os.getenv('TEMP') or '/tmp')
        if not os.path.isdir(save_dir):
            save_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'covers')
            if not os.path.isdir(save_dir):
                try:
                    os.makedirs(save_dir)
                except:
                    pass

        #if not os.path.isfile(music_file):
            #if not self.first:
                #print(make_colors("Invalid Music file !", 'lw', 'lr'))
            #if not sys.platform == 'win32':
                #pnotify = pynotify.Notification("Error", "Invalid Music file !", "file://" + os.path.join(os.path.dirname(os.path.realpath(__file__)), "error.png"))
                #pnotify.show()
            #if not self.first:
                #notify.send("Error", "Invalid Music file !", "MPDNotify", "error", iconpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "error.png"), sticky = True)
            #return ''
        data_cover = None
        debug(music_file = music_file)
        if music_file.lower().endswith('.mp3'):
            f = ID3(music_file)
            debug(meta_keys = f.keys())
            for i in f.keys():
                if "APIC" in i:
                    data_cover = f.get(i)
                    debug(len_data_cover = len(data_cover.data))
                    break
            if data_cover: debug(len_data_cover = len(data_cover.data))
        elif music_file.lower().endswith('.flac'):
            if MUTAGEN:
                f = FLAC(music_file)
                if f.picture:
                    data_cover = f.picture[0]
            else:
                print('"mutagen" module is not installed !')
        if not data_cover:
            if not self.first:
                logger.warn(make_colors("Music file don't containt tag Cover !", 'lw', 'r'))
            if not sys.platform == 'win32':
                if not self.first:
                    pnotify = pynotify.Notification("Error", "Music file don't containt tag Cover !", "file://" + os.path.join(os.path.dirname(os.path.realpath(__file__)), "error.png"))
                pnotify.show()
            if not self.first:
                notify.send("Error", "Music file don't containt tag Cover !", "MPDNotify", "error", iconpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "error.png"), sticky = True)
            # return self.DEFAULT_COVER
            return ''

        debug(data_cover_mime = data_cover.mime)
        ext = mimelist.get(data_cover.mime) or data_cover.mime.split("/")[-1]
        debug(ext = ext)
        save_dir = save_dir or os.path.dirname(music_file)
        if os.path.isfile(os.path.join(os.path.realpath(save_dir), 'cover2.' + ext)):
            return os.path.join(os.path.realpath(save_dir), 'cover2.' + ext)
        if isinstance(data_cover.data, bytes):
            with open(os.path.join(save_dir, 'cover2.' + ext), 'wb') as c:
                c.write(data_cover.data)
        elif isinstance(data_cover.data, str):
            with open(os.path.join(save_dir, 'cover2.' + ext), 'w') as c:
                c.write(data_cover.data)
        if not os.path.isfile(os.path.join(save_dir, 'cover2.' + ext)):
            if not self.first:
                logger.error(make_colors("Invalid Cover !", 'lw', 'r'))
            if not sys.platform == 'win32':
                if not self.first:
                    pnotify = pynotify.Notification("Error", "Invalid Cover !", "file://" + os.path.join(os.path.dirname(os.path.realpath(__file__)), "error.png"))
                pnotify.show()
            if not self.first:
                notify.send("Error", "Invalid Cover !", "MPDNotify", "error", iconpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "error.png"), sticky = True)
            return self.DEFAULT_COVER

        return os.path.join(save_dir, 'cover2.' + ext)

    @classmethod
    def get_cover_lastfm(self, current_song = None, timeout = 5, retries = 5, size = 'medium'):
        file_path = ''
        img_url = ''
        thumb = ''
        current_song = current_song or self.current_song or self.conn('currentsong')
        if not current_song or not isinstance(current_song, dict):
            return '', '', ''
        api_key = self.CONFIG.get_config('lastfm', 'api')
        if not api_key:
            try:
                import mpd_album_art
                grab = mpd_album_art.Grabber(self.COVER_TEMP_DIR)
                debug(current_song = current_song)
                file_path = grab.get_art(current_song)

                if file_path:
                    if os.path.isfile(file_path):
                        return file_path, '', ''
            except ImportError:
                logger.fatal(make_colors("Please install 'mpd_album_art' before: 'pip install git+http://jameh.github.io/mpd-album-art' or input lastfm api key in config file, '{}'".format(self.CONFIG.configname), 'lw', 'r'))
                file_path = ''

        if not file_path and api_key:
            url_artist = "http://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist={}&api_key=" + api_key + "&format=json"
            url_album = "http://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key=" + api_key + "&artist={}&album={}&format=json"
            IS_ARTIST = False
            IS_ALBUM = False
            debug(artist = current_song.get('artist'))
            debug(album = current_song.get('album'))
            n = 1
            a = None
            while 1:
                try:
                    a = requests.get(url_album.format(current_song.get('artist'), current_song.get('album'))).json()
                    debug(a = a)

                    if isinstance(a, dict):
                        if a.get('error') == 6 or a.get('message') == 'Album not found':
                            IS_ALBUM = False
                            a = requests.get(url_artist.format(current_song.get('artist'))).json()
                            debug(a = a)
                        else:
                            IS_ALBUM = True
                    else:
                        IS_ARTIST = True
                    break
                except:
                    if not n == retries:
                        n += 1
                        time.sleep(1)
                    else:
                        break
            debug(a = a)
            if a:
                debug(IS_ARTIST = IS_ARTIST)
                debug(IS_ALBUM = IS_ALBUM)
                #pause()

                try:
                    if IS_ARTIST:
                        images = a.get('album').get('image')
                        debug(images = images)
                    elif IS_ALBUM:
                        images = a.get('album').get('image')
                        debug(images = images)
                    else:
                        logger.warn(make_colors("Not Artist or Album from LaST.fm [1] !", 'lw', 'r'))
                        file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'no-cover.png')
                        if not os.path.isfile(file_path): file_path = ''
                        return file_path, '', thumb
                except AttributeError:
                    #print(traceback.format_exc())
                    logger.error(traceback.format_exc())
                    logger.warn(make_colors("Not Artist or Album from LaST.fm [2] !", 'lw', 'r'))
                    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'no-cover.png')
                    if not os.path.isfile(file_path): file_path = ''
                    return file_path, '', thumb
                debug(images = images)
                if images:
                    for i in images:
                        if i.get('size') == size:
                            img_url = i.get('#text')
                            debug(i = i)
                            debug(img_url = img_url)
                        if i.get('size') == 'small':
                            thumb = i.get('#text')
                            debug(i = i)
                            debug(img_url = img_url)                        
                        if img_url:
                            break
                    if not img_url:
                        img_url = images[0].get('#text')
                debug(img_url = img_url)
                if not os.path.isdir(self.COVER_TEMP_DIR):
                    os.makedirs(self.COVER_TEMP_DIR)
                #try:
                    ## Download the image
                    #urlretrieve(img_url, file_path)
                    #self.remove_current_link()
                #except:
                    #sys.stderr.write(traceback.format_exc() + "\n")
                    #self.remove_current_link()
                    #return None
                if img_url:
                    n = 1
                    data_img = None
                    while 1:
                        try:
                            data_img = requests.get(img_url, stream = True).content
                            debug(len_data_img = len(data_img))
                            file_path = os.path.join(self.COVER_TEMP_DIR, '{}_{}{}'.format(current_song.get('artist'), current_song.get('album').replace(" ", "_"), os.path.splitext(img_url)[-1]))
                            debug(file_path = file_path)
                            with open(file_path, 'wb') as img:
                                img.write(data_img)
                            break
                        except:
                            if not n == retries:
                                n += 1
                            else:
                                #print(make_colors("ERROR:", 'lw', 'r') + traceback.format_exc())
                                logger.error(traceback.format_exc())
                                break
        debug(file_path = file_path)
        if file_path:
            if not os.path.isfile(file_path): file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'no-cover.png')
        return file_path, img_url, thumb

    @classmethod
    def get_cover_from_cover_server(self, current_song, ext):
        try:
            chost = self.CONFIG.get_config('cover_server', 'host')
            debug(chost = chost)
            if chost == '0.0.0.0': chost = '127.0.0.1'
            #if self.process:
                #try:
                    #self.process.terminate()
                #except:
                    #pass                
            #self.process = Pool(processes = 1)
            r = None
            
            nt = 0
            while 1:
                try:
                    #r = self.process.apply_async(requests.get, args = ('http://' + chost + ":" + str(self.CONFIG.get_config('cover_server', 'port')),), kwds = {'timeout': (self.CONFIG.get_config('requests', 'timeout') or 6)})
                    logger.warning("Get cover from cover server 'http://{}:{}'".format(chost, str(self.CONFIG.get_config('cover_server', 'port'))))
                    r = requests.get(
                        'http://' + chost + ":" + str(self.CONFIG.get_config('cover_server', 'port')),
                        timeout = (self.CONFIG.get_config('requests', 'timeout') or 6)
                    )
                except Exception as e:
                    if os.getenv('TRACEBACK') == '1' or os.getenv('TRACEBACK') == 1:
                        logger.warning("get cover from cover server [ERROR]: {}".format(e))
                    else:
                        logger.warning("get cover from cover server [ERROR]")
                try:
                    logger.warning("get cover from cover server")
                    #if r.get():
                    if r:
                        logger.warning("get cover from cover server [FINISH]")
                        break
                except Exception as e:
                    if os.getenv('TRACEBACK') == '1' or os.getenv('TRACEBACK') == 1:
                        logger.warning("get cover from cover server [ERROR]: {}".format(e))
                    else:
                        logger.warning("get cover from cover server [ERROR]")
                    debug(nt = nt)
                if not nt > (self.CONFIG.get_config('cover_server', 'tries', '3') or 3):
                    nt += 1
                else:
                    r = None
                    break
                    
            #r = requests.get('http://' + chost + ":" + str(self.CONFIG.get_config('cover_server', 'port')), timeout = (self.CONFIG.get_config('requests', 'timeout') or 5))
            if r:
                #ext = r.get().headers.get('Content-type') or r.get().headers.get('content-type')
                ext = r.headers.get('Content-type') or r.headers.get('content-type')
                logger.debug("ext: {}".format(ext))
                if ext:
                    if "image" in ext: logger.warning("get cover from cover server [SUCCESS]")
                if ext: ext = mimelist.get(ext) or "jpg"
                logger.debug("ext: {}".format(ext))
                try:
                    if not os.path.isdir(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'))):
                        os.makedirs(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown')))
                    with open(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover.' + ext), 'wb') as fc:
                        try:
                            logger.warning("get cover from cover server, write file")
                            #fc.write(r.get().content)
                            fc.write(r.content)
                            logger.warning("get cover from cover server, write file [FINISH]")
                            logger.info("get cover from cover server: cover: '{}'".format(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover.' + ext)))
                        except Exception as e:
                            logger.error("Failed to make file, get cover from cover server [FAILED 0]")
                            if os.getenv('TRACEBACK') == '1' or os.getenv('TRACEBACK') == 1:
                                logger.error(e)
                except Exception as e:
                    logger.error("Failed to make file, get cover from cover server [FAILED 1]")
                    if os.getenv('TRACEBACK') == '1' or os.getenv('TRACEBACK') == 1:
                        logger.error(e)                 
            else:
                logger.error("Failed to get cover from cover server [FAILED]")
            logger.warning("get cover from cover server, check is file")
            if MPD.check_is_image(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover.' + ext)):
                self.cover = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover.' + ext)
                debug(self_cover = self.cover)
                logger.warning("cover is file [7]")
                return self.cover
            else:
                logger.error("Failed to make file, get cover from cover server [FAILED 2]")
        except Exception as e:
            logger.error(e)
            if os.getenv('TRACEBACK') == '1' or os.getenv('TRACEBACK') == 1: logger.error(traceback.format_exc())
        return False
                
    @classmethod
    def get_cover(self, current_song, music_dir = None, get_lastfm_cover = True, refresh = False):
        if refresh: self.cover = ''
        
        current_song = current_song or self.conn('currentsong')
        if current_song.get('file') == self.current_song.get('file'): self.current_song = current_song
        logger.info("self.current_song: {}".format(self.current_song))
        debug(music_dir = music_dir)
        music_dir = music_dir or MPD_MUSIC_DIR or self.music_dir
        debug(music_dir = music_dir)
        debug(current_song = current_song)
        if sys.platform == 'win32':
            sep = "\\"
        else:
            sep = "/"
        
        ############################ [start] get cover from mpd tag #############################################
        logger.debug("get cover from mpd tag")
        debug(file = current_song.get('file'))
        img_data = self.conn('albumart', (current_song.get('file'), ))
        ext = 'jpg'
        if img_data: img_data = img_data.get('binary')
        debug(img_data = len(img_data))
        
        if img_data and current_song:
            logger.debug("get cover from mpd tag, img_data is exists")
            img = Image.open(io.BytesIO(img_data))
            debug(check_ext = mimelist.get2(img.format))
            ext = mimelist.get2(img.format)[1]
            if not os.path.isdir(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'))):
                os.makedirs(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown')))
            try:
                img.save(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + "." +  ext))
            except Exception as e:
                logger.error("get cover from mpd tag, Error save imgdata")
                if os.getenv('TRACEBACK') == '1' or os.getenv('TRACEBACK') == 1: logger.error("get cover from mpd tag, Error save imgdata: {}".format(str(traceback.format_exc())))
            
        if os.path.isfile(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + "." +  ext)):
            if MPD.check_is_image(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + "." +  ext)):
                self.cover = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + "." +  ext)
                debug(self_cover_X = self.cover)
                logger.warning("get cover from mpd tag, cover is file [2]")
                logger.debug("self.cover: {}".format(self.cover))
                return os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + "." +  ext)
        debug(refresh = refresh)
        debug(self_cover = self.cover)
        debug(check_cover = MPD.check_is_image(self.cover))
        
        ############################ [end] get cover from mpd tag #############################################
        
        ############################# [start] get cover by name [.jpg|.png] #####################################
        logger.debug("get cover by name [.jpg|.png]")
        if os.path.isfile(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + ".jpg")):
            self.cover = self.cover = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + ".jpg")
        elif os.path.isfile(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + ".png")):
            self.cover = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + ".png")
        elif os.path.isfile(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'Cover' + ".jpg")):
            self.cover = self.cover = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'Cover' + ".jpg")
        elif os.path.isfile(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'Cover' + ".png")):
            self.cover = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'Cover' + ".png")
        elif os.path.isfile(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'folder' + ".jpg")):
            self.cover = self.cover = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'folder' + ".jpg")
        elif os.path.isfile(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'folder' + ".png")):
            self.cover = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'folder' + ".png")
        elif os.path.isfile(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'Folder' + ".jpg")):
            self.cover = self.cover = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'Folder' + ".jpg")
        elif os.path.isfile(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'Folder' + ".png")):
            self.cover = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'Folder' + ".png")        
        debug(self_cover = self.cover)
        if MPD.check_is_image(self.cover):
            debug(self_cover = self.cover)
            logger.warning("cover is file [1]")
            logger.debug("[SUCCESS] get cover by name [.jpg|.png]")
            logger.debug("self.cover: {}".format(self.cover))
            return self.cover

        debug('No cover')
        
        if not MPD.check_is_image(self.cover) and current_song.get('file'):
            #if not os.path.isfile(self.cover):
            if sys.platform == 'win32':
                self.cover = os.path.join(music_dir, sep.join(os.path.splitext(current_song.get('file'))[0].split("/")[1:])) + '.jpg'
            else:
                self.cover = os.path.join(music_dir, os.path.splitext(current_song.get('file'))[0]) + '.jpg'
            debug(self_cover = self.cover)
            if MPD.check_is_image(self.cover):
                logger.warning("get cover by name [.jpg|.png], cover is file [2]")
                logger.debug("self.cover: {}".format(self.cover))
                return self.cover                    
        if not MPD.check_is_image(self.cover) and current_song.get('file'):
            if sys.platform == 'win32':
                self.cover = os.path.join(music_dir, sep.join(os.path.splitext(current_song.get('file'))[0].split("/")[1:])) + '.png'
            else:
                self.cover = os.path.join(music_dir, os.path.splitext(current_song.get('file'))[0]) + '.png'
            debug(self_cover = self.cover)
            if MPD.check_is_image(self.cover):
                logger.warning("get cover by name [.jpg|.png], cover is file [3]")
                logger.debug("self.cover: {}".format(self.cover))
                return self.cover        
        if not MPD.check_is_image(self.cover) and current_song.get('file'):
            cover_file = os.path.join(music_dir, sep.join(current_song.get('file').split("/")[1:]))
            debug(cover_file = cover_file)
            try:
                if MUTAGEN:
                    self.cover = MPD.get_cover_tag(cover_file)
                    if MPD.check_is_image(cover_file):
                        logger.warning("get cover by name [.jpg|.png], cover is file [4]")
                        logger.debug("self.cover: {}".format(self.cover))
                        return self.cover
                else:
                    print('"mutagen" module is not installed !')                
            except:
                pass
        #if MPD.check_is_image(self.cover):
            #logger.warning("cover is file [4]")
            #return self.cover
        debug(self_cover = self.cover)
        valid_cover = list(filter(None, [i.strip() for i in re.split(",|\n|\t", self.CONFIG.get_config('cover', 'valid'))])) or ['cover.jpg', 'cover2.jpg', 'cover.png', 'cover2.png', 'folder.jpg', 'folder.png', 'front.jpg', 'front.png', 'albumart.jpg', 'albumart.png', 'folder1.jpg', 'folder1.png', 'back.jpg', 'back.png']
        
        debug(cover_check_1 = (current_song.get('file') or 'unknown').split("/")[1:])
        #debug(file = file)
        for i in valid_cover:
            #if sys.platform == 'win32':
            debug(split_drive = os.path.join(music_dir, sep.join(os.path.dirname((current_song.get('file') or 'unknown')).split("/")[1:]), i), sep = sep)
            if sys.platform == 'win32':
                split_drive = os.path.join(music_dir, sep.join(os.path.dirname((current_song.get('file') or 'unknown')).split("/")[1:]))
            else:
                split_drive = os.path.join(music_dir, sep.join(os.path.dirname((current_song.get('file') or 'unknown')).split("/")))
            self.cover = list(filter(lambda k: os.path.isfile(k), 
                [
                    os.path.join(split_drive, i),
                    os.path.join(split_drive, i.title()), 
                    os.path.join(split_drive, i.upper())
                ]
            ))
            debug(self_cover = self.cover)
            if self.cover:
                self.cover = self.cover[0]
            else:
                self.cover = ''
            #else:
                #self.cover = os.path.join(music_dir, os.path.dirname(current_song.get('file')), i)
            debug(self_cover = self.cover)
            #if self.cover:
            debug(self_cover = self.cover)
            if MPD.check_is_image(self.cover):
                #print('return 3.....')
                debug(self_cover = self.cover)
                logger.debug("self.cover: {}".format(self.cover))
                return self.cover

                #cover_dir = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'))
                #debug(cover_dir = cover_dir)
                #if not os.path.isdir(cover_dir):
                    #try:
                        #os.makedirs(cover_dir)
                    #except NotADirectoryError:
                        #logger.error("NotADirectoryError: '{}'".format(cover_dir))
                        #cover_dir = self.COVER_TEMP_DIR
                        #if not os.path.isdir(cover_dir):
                            #os.makedirs(cover_dir)
                #try:
                    #shutil.copy2(self.cover, cover_dir)
                    #self.cover = os.path.join(cover_dir, os.path.basename(self.cover))
                    #debug(self_cover = self.cover)
                #except Exception as e:
                    # #print(make_colors("shutil:", 'lw', 'r') + " " + make_colors(str(e), 'lw', 'bl'))
                    #logger.error(e)
                    #if os.getenv('TRACEBACK'):
                        # #print(traceback.format_exc())
                        #logger.error(traceback.format_exc())
                #logger.warning("cover is file [5]")
                #return self.cover
            else:
                self.cover: self.cover = ''

        #if self.cover and MPD.check_is_image(self.cover):
            #debug(self_cover = self.cover)
            #logger.warning("cover is file [6]")
            #return self.cover
        ############################# [end] get cover by name [.jpg|.png] #####################################
        
        ########################### get cover from cover server ##########################
        self.cover = self.get_cover_from_cover_server(current_song, ext)
        if self.cover:
            if not MPD.check_is_image(self.cover): self.cover = False
        ############################ get cover from lastfm ######################################
        if get_lastfm_cover and not self.cover:
            logger.warning("get cover from LAST.FM")
            debug(self_FAIL_LAST_FM = self.FAIL_LAST_FM)
            if not self.FAIL_LAST_FM:
                if self.process1:
                    try:
                        self.process1.terminate()
                    except:
                        pass                
                r1 = None
                self.process1 = Pool(processes = 1)
                
                #self.cover = MPD.get_cover_lastfm()[0]
                nt1 = 0
                while 1:
                    try:
                        r1 = self.process1.apply_async(MPD.get_cover_lastfm, args = ())
                    except Exception as e:
                        logger.warning("get cover from LAST.FM [ERROR]: {}".format(e))
                                        
                    try:
                        logger.warning("get cover from LAST.FM")
                        if r1.get():
                            logger.warning("get cover from LAST.FM [FINISH]")
                            break
                    except Exception as e:
                        logger.warning("get cover from LAST.FM [ERROR]: {}".format(e))
                        debug(nt1 = nt1)
                    if not nt1 > (self.CONFIG.get_config('lastfm', 'tries', '3') or 3):
                        nt1 += 1
                    else:
                        r1 = None
                        break
                
                if r1: self.cover = r1.get()[0]
                if self.cover:
                    debug(self_cover = self.cover)
                    debug(cover_split = self.cover.split(os.path.sep)[-1])
                if not self.cover or self.cover.split(os.path.sep)[-1] == 'no-cover.png': self.FAIL_LAST_FM = True
                debug(self_FAIL_LAST_FM = self.FAIL_LAST_FM)
        debug(self_cover = self.cover)
        if not MPD.check_is_image(self.cover):
            logger.warning("cover is self.DEFAULT_COVER")
            return self.DEFAULT_COVER
        logger.warning("cover is file [8]")
        return self.cover

    @classmethod
    def check_is_image(self, file):
        try:
            im = Image.open(file)
            im.verify()
            im.close()
            return True
        except:
            return False
        
    @classmethod
    def cover_server(self, host = None, port = None):
        try:
            from . cover_server import CoverServer
        except:
            from cover_server import CoverServer
            
        host = host or self.CONFIG.get_config('cover_server', 'host') or '0.0.0.0'
        port = port or self.CONFIG.get_config('cover_server', 'port') or 8800
        if host: self.CONFIG.write_config('cover_server', 'host', host)
        if port: self.CONFIG.write_config('cover_server', 'port', port)
        Handler = CoverServer
        logger.warning('Server Run on: {}:{}'.format(host, port))
        debug(host = host)
        debug(port = port)
        #server = SocketServer.TCPServer((host, port), Handler)

        try:
            server = SocketServer.TCPServer((host, port), Handler)
            server.serve_forever()
        except KeyboardInterrupt:
            logging.error("Exception occurred", exc_info=True)
            os.kill(os.getpid(), signal.SIGTERM)
        except:
            logging.error(traceback.format_exc())


class Art(QDialog):
    keyPressed = pyqtSignal(str)
    CONFIG = MPD.CONFIG
    
    sleep = CONFIG.get_config('sleep', 'time') or 1000
    icon = CONFIG.get_config('icon', 'path')
    music_dir = CONFIG.get_config('mpd', 'music_dir')
    configfile = CONFIG.get_config('config', 'file')
    timeout = CONFIG.get_config('mpd', 'timeout')
    command = None
    last_dir = None
    cover = ''
    DEFAULT_COVER = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'no-cover.png')
    current_song = {}
    COVER_TEMP_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'covers')
    FAIL_LAST_FM = False
    current_state = {}
    first = False
    process = None
    last_state = 'stop'
    last_song = ''
    current = 1
    total = 1
    host = '127.0.0.1'
    port = 6600
    
    PREFIX = '{variables.task} >> {variables.subtask} '
    VARIABLES = {'task': '--', 'subtask': '--',}
    BAR = ProgressBar(max_value = 100, max_error = False, prefix = PREFIX, variables = VARIABLES)

    def __init__(self, host = None, port = None, sleep = None, configfile = None, icon = None, music_dir = None):
        
        if sys.version_info.major == 3:
            super().__init__()
        else:
            super(MPDArt(), self).__init__()
        #QDialog.__init__(self, None, QtCore.Qt.WindowStaysOnTopHint)
        
        self.ui = Ui_mpdart()
        self.ui.setupUi(self)
        self.setMouseTracking(True)
        self.setShortcut()
        
        self.installEventFilter(self)
        try:
            self.dark_view.installEventFilter(self)
        except:
            pass
        
        self.music_dir = music_dir or self.music_dir or self.CONFIG.get_config('mpd', 'music_dir')
        debug(music_dir = music_dir)
        
        if not self.music_dir:
            logger.warn(make_colors("No Music Directory 'music_dir' setup !", 'lw', 'r'))
            #return False
        if self.music_dir:
            if not os.path.isdir(self.music_dir) and self.music_dir[1:3] == ":\\":
                logger.warn(make_colors("Invalid Music Directory 'music_dir'!, please setup before", 'lw', 'r'))
                #return False
        host0 = host
        debug(host0 = host0)
        self.host = host or self.host or '127.0.0.1'
        self.port = port or self.port or 6600
        debug(self_host = self.host)
        if host and not host0 == self.host: self.CONN.connect(self.host, self.port)
                
        self.sleep = sleep or self.sleep or 1000
        self.configfile = configfile or self.configfile
        if self.configfile:
            if os.path.isfile(self.configfile): self.CONFIG = configset(self.configfile)

        self.icon = icon or self.CONFIG.get_config('icon', 'path')
        if not os.path.isfile(self.icon): self.icon = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'icon.png')
        debug(self_icon = self.icon)
        if os.path.isfile(self.icon): self.setWindowIcon(QIcon(self.icon))
        if os.path.isfile(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'no-cover.png')):
            self.setPixmap(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'no-cover.png'))
        #self.setToolTip()
        self.ui.cb_top.stateChanged.connect(self.setOnTop)
        
        if sys.platform == "win32":
            self.change_font(self.CONFIG.get_config('font', 'all'))
        else:
            self.change_font(6)
        
        self.change_color()
        self.change_opacity()
        self.change_title_bar()
        self.setPositionbylast()
        
        #fi = self.ui.artist.fontInfo()
        #print("font artist:", fi.pointSize())
        
        self.timer = QTimer(self)
        self.timer_bar = QTimer(self)
        
        #self.showData()
        
    def quit(self):
        logger.debug("list position [1]: {}, {}".format(self.pos().x(), self.pos().y()))
        try:
            logger.debug("list position [2]: {}, {}".format(self.dark_view.pos().x(), self.dark_view.pos().y()))
        except:
            pass
        self.setLastPosition()
        self.close()
        
    def setLastPosition(self):
        try:
            if not self.dark_view.pos().x() < 2:
                self.CONFIG.write_config('position', 'x', self.dark_view.pos().x())
                self.CONFIG.write_config('position', 'y', self.dark_view.pos().y())
            else:
                self.CONFIG.write_config('position', 'x', self.geometry().x())
                self.CONFIG.write_config('position', 'y', self.geometry().y())
        except:
            traceback.format_exc()
            self.CONFIG.write_config('position', 'x', self.geometry().x())
            self.CONFIG.write_config('position', 'y', self.geometry().y())
            
    def setPositionbylast(self):
        x = self.CONFIG.get_config('position', 'x')
        y = self.CONFIG.get_config('position', 'y')
        if x or y:
            if x > 1 or y > 1:
                self.setGeometry(QRect(x, y, self.geometry().width(), self.geometry().height()))
                try:
                    self.setGeometry(QRect(x, y, self.dark_view.geometry().width(), self.dark_view.geometry().height()))
                except:
                    pass
    #def mouseMoveEvent(self, e):
        #print("pos:", e.x(), e.y())
        
    #def mousePressEvent(self, e):
        #print("pos:", e.x(), e.y())    
        
    def jump(self):
        jump = MPD.CONFIG.get_config('repeat', 'jump')
        logger.warning("config jump: {}".format(jump))
        jump_from = ''
        jump_to = ''
        if jump and "," in jump:
            try:
                jump_from, jump_to = list(filter(None, [i.strip() for i in re.split(",|\n", jump)]))
                if jump_from == '.' or jump_from == "#" or jump_from == "?":
                    jump_from = self.current_song.get('id')
                logger.warning("jump from: {}".format(jump_from))
                logger.warning("jump to: {}".format(jump_to))
            except:
                traceback.format_exc()
        if jump_from and jump_to:
            logger.warning("jump from: {}".format(jump_from))
            logger.warning("jump to: {}".format(jump_to))
            logger.warning("current song pos: {}".format(self.current_song.get('id')))
            if jump_from == self.current_song.get('pos'):                        
                try:
                    MPD.CONN.play(str(int(jump_to) - 1))
                    #MPD.CONFIG.write_config('repeat', 'jump', '')
                except:
                    try:
                        MPD.conn('play', (jump_to, ))
                        #MPD.CONFIG.write_config('repeat', 'jump', '')
                    except:
                        traceback.format_exc()
                        
    def showData(self):
        logger.debug("self_current_song: " + str(self.current_song))
        logger.debug("self_current_state: " + str(self.current_state))
        
        if not self.current_song and not self.current_state:
            debug(self_host = self.host)
            debug(self_port = self.port)
            debug(self_timeout = self.timeout)
            self._showData(self.host, self.port, self.timeout)
            logger.debug("self_current_song: " + str(self.current_song))
            logger.debug("self_current_state: " + str(self.current_state))
            
        if self.current_song and self.current_state:
            try:
                self.bring_to_front(self.dark_view)
            except:
                #self.bring_to_front(self)
                pass
            #MPD.send_notify(self.current_song, self.current_state, event=self.current_state.get('state'), cover_art=self.cover)
            
            self.last_song = self.current_song.get('file')
            self.last_state = self.current_state.get('state')
            
            current_time = self.current_state.get('time') or "1:1"
            self.current, self.total = current_time.split(":")
            debug(self_current = self.current)
            debug(self_total = self.total)
            
        self.timer_bar.timeout.connect(self.set_bar)
        self.timer_bar.start(self.CONFIG.get_config('sleep', 'time') or 1000)        
                
        #self.timer.timeout.connect(self._showData)
        #self.timer.start(int(float(self.total)) * 1000)
        
    def set_bar(self):
        self.current_state = MPD.conn('status')
        debug(self_current_state = self.current_state, debug = 1)
        debug(self_last_song = self.last_song, debug = 1)
        debug(self_current_song_get_file = self.current_song.get('file'), debug = 1)
        debug(self_current = self.current, debug = 1)
        debug(self_total = self.total, debug = 1)
        debug(duration = self.current_state.get('duration'), debug = 1)
        debug(elapsed = self.current_state.get('elapsed'), debug = 1)
        if self.current_state:
            #logger.warning("current state: {}".format(self.current_state.get('state')))
            #logger.warning('last state   : {}'.format(self.last_state))
            debug(self_current_state_get_state = self.current_state.get('state'), debug = 1)
            try:
                debug(check_duration = self.current_state.get('duration') > self.current_state.get('elapsed'), debug = 1)
            except:
                pass
            if self.current_state.get('state') == 'play':# or not self.last_song == self.current_song.get('file'):
                if self.current_state.get('duration') > self.current_state.get('elapsed'):
                    percent_value = int((float(self.current_state.get('elapsed')) / float(self.current_state.get('duration'))) * 100)
                    debug(percent_value = percent_value, debug = 1)
                    self.ui.pbar.setValue(percent_value)
                    self._showData(self.host, self.port, self.timeout, False)
                #if not float(self.current) >= float(self.total):
                    #self.ui.pbar.setValue(int((float(self.current) / float(self.total)) * 100))
                    #if not self.last_state == 'play' or not self.last_song == self.current_song.get('file'):
                    if not self.current_state.get('state') == 'play' or not self.last_song == self.current_song.get('file'):
                        logger.warning('{} --> play'.format(self.last_state))
                        try:
                            self.bring_to_front(self.dark_view)
                        except:
                            #self.bring_to_front(self)
                            pass
                        if not self.last_song == self.current_song.get('file'):
                            self._showData(self.host, self.port, self.timeout, False)
                            self.cover = self.set_cover(refresh = True)
                            #if self.current_song and self.current_state:
                            self.last_song = self.current_song.get('file')
                            self.last_state = self.current_state.get('state')
                        #if self.last_state == ('stop' or 'pause'):
                            MPD.send_notify(self.current_song, self.current_state, self.current_state.get('state'), cover_art=self.cover,)
                #else:
                elif float(self.current) >= float(self.total) or not self.last_song == self.current_song.get('file'):
                    self.jump()
                    logger.warning('prepare next song')
                    time.sleep(1)
                    self._showData(self.host, self.port, self.timeout, False)
                    self.cover = self.set_cover(refresh = True)
                    MPD.send_notify(self.current_song, self.current_state, self.current_state.get('state'), cover_art=self.cover,)
                    #if self.current_song and self.current_state:
                    logger.warning('play next song')
                    self.last_song = self.current_song.get('file')
                    self.last_state = self.current_state.get('state')
                    
                self.last_state = self.current_state.get('state')
                self.ui.comment.setText(self.current_state.get('state'))
                if self.current_state.get('state') == 'stop': self.ui.pbar.setValue(0)
                        
            elif self.current_state.get('state') == 'pause' or not self.last_song == self.current_song.get('file'):
                if not self.last_state == 'pause':
                    logger.warning('{} --> pause'.format(self.last_state))
                    try:
                        self.bring_to_front(self.dark_view)
                    except:
                        #self.bring_to_front(self)
                        pass
                    if not self.last_song == self.current_song.get('file'):
                        self._showData(self.host, self.port, self.timeout, False)
                        self.last_song = self.current_song.get('file')
                        self.last_state = self.current_state.get('state')                    
                        self.cover = self.set_cover(refresh = True)
                    MPD.send_notify(self.current_song, self.current_state, self.current_state.get('state'), cover_art=self.cover,)
                self.last_state = self.current_state.get('state')
                self.ui.comment.setText(self.current_state.get('state'))
                self.ui.pbar.setValue(int((float(self.current) / float(self.total)) * 100))
                #self._showData(self.host, self.port, self.timeout, True)
            elif self.current_state.get('state') == 'stop' or not self.last_song == self.current_song.get('file'):
                self.jump()
                if not self.last_state == "stop":
                    logger.warning('{} --> stop'.format(self.last_state))
                    try:
                        self.bring_to_front(self.dark_view)
                    except:
                        #self.bring_to_front(self)
                        pass
                    if not self.last_song == self.current_song.get('file'):
                        self._showData(self.host, self.port, self.timeout, False)
                        self.last_song = self.current_song.get('file')
                        self.last_state = self.current_state.get('state')                    
                        self.cover = self.set_cover(refresh = True)                    
                    MPD.send_notify(self.current_song, self.current_state, self.current_state.get('state'), cover_art=self.cover,)
                self.last_state = self.current_state.get('state')
                self.ui.comment.setText(self.current_state.get('state'))
                self.ui.pbar.setValue(0)
            elif float(self.current) >= float(self.total) or not self.last_song == self.current_song.get('file'):
                self.jump()
                logger.warning('prepare next song')
                time.sleep(1)
                self._showData(self.host, self.port, self.timeout, False)
                self.cover = self.set_cover(refresh = True)
                MPD.send_notify(self.current_song, self.current_state, self.current_state.get('state'), cover_art=self.cover,)
                #if self.current_song and self.current_state:
                logger.warning('play next song')
                self.last_song = self.current_song.get('file')
                self.last_state = self.current_state.get('state')
            else:
                self.jump()
                if not self.last_state == self.current_state.get('state') or not self.last_song == self.current_song.get('file'):
                    logger.warning('{} --> {}'.format(self.last_state, self.current_state.get('state')))
                    try:
                        self.bring_to_front(self.dark_view)
                    except:
                        #self.bring_to_front(self)
                        pass
                    if not self.last_song == self.current_song.get('file'):
                        self._showData(self.host, self.port, self.timeout, False)
                        self.last_song = self.current_song.get('file')
                        self.last_state = self.current_state.get('state')                    
                        self.cover = self.set_cover(refresh = True)                    
                    MPD.send_notify(self.current_song, self.current_state, self.current_state.get('state'), cover_art=self.cover,)
                self.last_state = self.current_state.get('state')
                self.ui.comment.setText(self.current_state.get('state'))
                self.ui.pbar.setValue(0)
        
        #self.jump()        
        self.current_state = MPD.conn('status')
        self.current_song = MPD.conn('currentsong')
        debug(self_current_state = self.current_state)
        debug(self_current_song = self.current_song)
        
        if not self.current_song.get('file') == self.last_song:
            self.jump()
            self._showData(self.host, self.port, self.timeout, False, self.current_song, self.current_state)
            self.cover = self.set_cover(refresh = True)
            MPD.send_notify(self.current_song, self.current_state, self.current_state.get('state'), cover_art=self.cover,)
            self.last_song = self.current_song.get('file')
            #self.last_state = self.current_state.get('state')
            try:
                self.bring_to_front(self.dark_view)
            except:
                #self.bring_to_front(self)
                pass            
        if self.current_state:
            if self.current_state.get('state') == ('play' or 'pause'): self.current, self.total = self.current_state.get('time').split(":")
                #if self.last_state == 'stop':
                    #self._showData(self.host, self.port, self.timeout, True)
            
    def _showData(self, host = None, port = None, timeout = None, show_cover = True, current_song = None, current_state = None):
        timeout = self.timeout or self.CONFIG.get_config('mpd', 'timeout') or 60
        label = ''
        title_msg = ''
        track = '0'
        title = '~ no title / unknown ~'
        album = '~ no album / unknown ~'
        albumartist = '~ no albumartist / unknown ~'
        date = '~ no date / unknown ~'
        label = ''
        bitrate = ''
        genres = ''
        artist = ''
        current_song = {}
        current_state = {}
        disc = "0"
        duration = ''
        
        #c = self.conn(host, port)
        #current_state = self.conn(host, port).status()
        MAX_TRY = 10
        nt = 0
        task = make_colors("re-connecting to MPD_HOST -> {}".format((host or os.getenv('MPD_HOST'))), 'b', 'y')
        self.BAR.max_value = MAX_TRY
        current_state = current_state or MPD.conn('status')
        debug(current_state = current_state, debug = 1)
        while 1:
            try:
                current_state = current_state or MPD.conn('status')
                debug(current_state = current_state, debug = 1)
                break
            except:# ConnectionError:
                try:
                    current_state = MPD.conn('status', host = host, port = port, refresh = True)
                    debug(current_state = current_state)
                    MPD.CONN.connect(host, port, timeout)
                except mpd.base.ConnectionError:
                    #subtask = make_colors("mpd.base.ConnectionError [1]", 'lw', 'r')
                    subtask = make_colors("mpd.base.ConnectionError", 'lw', 'r')
                    if nt == MAX_TRY:
                        current_state = {}
                        break
                    else:
                        nt += 1
                        self.BAR.update(nt, task = task, subtask = subtask)
                        time.sleep(1)
            #except mpd.base.ConnectionError:
                #subtask = make_colors("mpd.base.ConnectionError [2]", 'lw', 'r')
                # #debug(nt = nt, debug = 1)
                # #debug(MAX_TRY = MAX_TRY, debug = 1)
                #if nt == MAX_TRY:
                    #current_state = {}
                    #break
                #else:
                    #nt += 1
                    #self.BAR.update(nt, task = task, subtask = subtask)
                    #time.sleep(1)
        self.BAR.max_value = 100
        if not current_state:
            print(make_colors("Error connection to MPD_HOST -> {}".format((host or os.getenv('MPD_HOST'))), 'lw', 'r'))
            os.kill(os.getpid(), signal.SIGTERM)
            
        debug(current_state = current_state)
        try:
            current_song = current_song or MPD.CONN.currentsong()
        except ConnectionError:
            try:
                current_song = MPD.conn('currentsong', host = host, port = port, refresh = True)
                debug(current_song = current_song)
                MPD.CONN.connect(host, port, timeout)
            except mpd.base.CommandError:
                print(traceback.format_exc())
                current_song = {}
        except mpd.base.ConnectionError:
            current_state = {}
        current_song = current_song or self.current_song
        if not self.current_song == current_song and current_song:
            self.cover = ''
        debug(current_song = current_song)
        
        if current_song:
            track = current_song.get('track')
            title = current_song.get('title')
            album = current_song.get('album')
            albumartist = current_song.get('albumartist')
            date = current_song.get('date')
            artist = current_song.get('artist')
            disc = current_song.get('disc') or '0'
            label = current_song.get('label') or ''
            duration = current_song.get('duration') or ''
            genres = current_song.get('genre') or ''
            
            self.ui.track.setText(
                track.zfill(2) + "/" + \
                disc.zfill(2) + ". " + \
                title
            )

            title_msg = '{} {} / {} - {} [{}]'.format(track.zfill(2) + "/" + disc.zfill(2) + ". ", title, album, artist, current_state.get('state'))
            debug(title_msg = title_msg)
            self.setWindowTitle(title_msg)
            
            try:
                self.dark_view.setWindowTitle(title_msg)
            except:
                pass
            
            self.ui.album.setText(
                (album or '') + " / " + \
                (albumartist or '') + " (" + \
                (date or '') + ")"
            )
            
            self.ui.artist.setText(
                artist
            )
            
            self.ui.comment.setText(current_state.get('state'))

            self.last_dir = os.path.dirname(current_song.get('file'))
            if label: label = label + " - "
            
        #if current_state.get('state') == 'play' or current_state.get('state') == 'pause':
            #self.ui.pbar.setValue(int((float(current_state.get('elapsed')) / float(current_state.get('duration'))) * 100))
        bitrate = current_state.get('bitrate') or bitrate
        self.ui.bitrate.setText(
            bitrate + " - " + \
            label 
        )
        debug(show_cover = show_cover)
        debug(check = show_cover or (current_state.get('state') == ('play' or 'pause') and (current_song and current_state)))
        if show_cover or (current_state.get('state') == ('play' or 'pause') and (current_song and current_state)):
            self.cover = self.set_cover(refresh = True)
            debug(self_cover = self.cover)
            #sys.exit()
            if MPD.check_is_image(self.cover):
                logger.debug('set cover + pixmap')
                self.setWindowIcon(QIcon(self.cover))
                self.setPixmap(self.cover)
        
        debug(current_song = current_song)
        debug(self_current_song = self.current_song)
        debug(current_state = current_state)
        debug(self_current_state = self.current_state)
        
        if (not self.current_song.get('file') == current_song.get('file') and title) or (not current_state.get('state') == self.current_state.get('state')):
            debug(self_cover = self.cover)
            MPD.send_notify(current_song, current_state, current_state.get('state'), self.cover)
            logger.debug("send info current song")
            #self.first = True
            #self.bring_to_front(self)
            try:
                self.bring_to_front(self.dark_view)
            except:
                #self.bring_to_front(self)
                pass
        
        self.current_song = current_song
        self.current_state = current_state
        debug(current_song = current_song)
        debug(current_state = current_state)
        #sys.exit()
        
        debug(current_song = current_song)
        debug(self_current_song = self.current_song)
        debug(current_state = current_state)
        debug(self_current_state = self.current_state)
        
    def set_font_size(self, object, size = 6, weight = 75, bold = None, italic = None):
        font = ''
        if (size or weight): font = QtGui.QFont()
        if size and font: font.setPointSize(int(size))
        debug(weight = weight)
        if weight and font: font.setWeight(weight)
        if isinstance(bold, bool) and font: font.setBold(bold)
        if isinstance(italic, bool) and font: font.setItalic(italic)
        object.setFont(font)
        
    def set_opacity(self, n = 1.0): 
        self.setWindowOpacity(n)
    
    def set_color(self, object, fg = None, bg = None):
        bg = bg or (29, 29, 29)
        fg = fg or (170, 255, 0)
        object.setStyleSheet(
            "background-color: rgb({});\n"
            "color: rgb({});".format(*bg, *fg)
        )
        
    def parse_font(self, label):
        if isinstance(label, str):
            size, family, weight, bold, italic = 6, None, 75, '', ''
            font = self.CONFIG.get_config('font', label).split(",")
            if len(font) == 2:
                size, family = font
            elif len(font) == 3:
                size, family, weight = font
            elif len(font) == 4:
                size, family, weight, bold = font
            elif len(font) == 5:
                size, family, weight, bold, italic = font            
            elif len(font) == 1:
                if font[0].isdigit():
                    font = font[0]
                else:
                    family = font[0]
            return size, family, weight, bold, italic
        
    def parse_color(self, label):
        fg, bg = (170, 255, 0), (29, 29, 29)
        color = self.CONFIG.get_config('color', label).split("#")
        if len(color) == 2:
            fg, bg = color
            fg = (fg)
            bg = (bg)
        elif len(font) == 1:
            fg = color[0]
            fg = (fg)
        return fg, bg
        
    def change_font(self, all_size = None):
        if self.CONFIG.get_config('font', 'artist') or all_size:
            size, family, weight, bold, italic = self.parse_font('artist')
            size = all_size or size
            if size: self.set_font_size(self.ui.artist, size, weight, bold, italic)
            if family: self.ui.artist.setStyleSheet("font: {}pt \"{}\";".format(size, family))
        if self.CONFIG.get_config('font', 'album') or all_size:
            size, family, weight, bold, italic = self.parse_font('album')
            size = all_size or size
            if size: self.set_font_size(self.ui.album, size, weight, bold, italic)
            if family: self.ui.album.setStyleSheet("font: {}pt \"{}\";".format(size, family))
        if self.CONFIG.get_config('font', 'track') or all_size:
            size, family, weight, bold, italic = self.parse_font('track')
            size = all_size or size
            if size: self.set_font_size(self.ui.track, size, weight, bold, italic)
            if family: self.ui.track.setStyleSheet("font: {}pt \"{}\";".format(size, family))
        if self.CONFIG.get_config('font', 'bitrate') or all_size:
            size, family, weight, bold, italic = self.parse_font('bitrate')
            size = all_size or size
            if size: self.set_font_size(self.ui.bitrate, size, weight, bold, italic)
            if family: self.ui.bitrate.setStyleSheet("font: {}pt \"{}\";".format(size, family))
        if self.CONFIG.get_config('font', 'comment') or all_size:
            size, family, weight, bold, italic = self.parse_font('comment')
            size = all_size or size
            if size: self.set_font_size(self.ui.comment, size, weight, bold, italic)
            if family: self.ui.comment.setStyleSheet("font: {}pt \"{}\";".format(size, family))
        
    def change_color(self):
        if self.CONFIG.get_config('color', 'artist'):
            fg, bg = self.parse_color('artist')
            self.set_color(self.ui.artist, fg, bg)
        if self.CONFIG.get_config('color', 'album'):
            fg, bg = self.parse_color('album')
            self.set_color(self.ui.album, fg, bg)
        if self.CONFIG.get_config('color', 'track'):
            fg, bg = self.parse_color('track')
            self.set_color(self.ui.track, fg, bg)
        if self.CONFIG.get_config('color', 'bitrate'):
            fg, bg = self.parse_color('bitrate')
            self.set_color(self.ui.bitrate, fg, bg)
        if self.CONFIG.get_config('color', 'comment'):
            fg, bg = self.parse_color('comment')
            self.set_color(self.ui.comment, fg, bg)
        
    def change_title_bar(self):
        if self.CONFIG.get_config('title', 'bar') == 0:
            #print("change cation !")
            self.setWindowFlag(Qt.FramelessWindowHint)
            
    def change_opacity(self):
        if self.CONFIG.get_config('opacity', 'transparent'):
            try:
                v = float(self.CONFIG.get_config('opacity', 'transparent'))
                self.set_opacity(v)
            except:
                pass
            
    def setOnTop(self):
        if self.CONFIG.get_config('appereance', 'top') == 1:
            if self.ui.cb_top.isChecked():
                self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
                self.bring_to_front(self)
            else:
                self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

    def bring_to_front(self, window = None):
        if self.CONFIG.get_config('appereance', 'top') == 1:
            if not window:
                return False
            if sys.platform == 'win32':
                from win32gui import SetWindowPos
                import win32con
                SetWindowPos(window.winId(),
                              win32con.HWND_TOPMOST, # = always on top. only reliable way to bring it to the front on windows
                              0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
                SetWindowPos(window.winId(),
                             win32con.HWND_NOTOPMOST, # disable the always on top, but leave window at its top position
                             0, 0, 0, 0,
                             win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
    
            # else:
                # window.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowStayOnTopHint)
            window.raise_()
            window.show()
            window.activateWindow()
    
    def setPixmap(self, image):
        pix = QPixmap(image)
        self.ui.cdart.setPixmap(pix)
        self.ui.cdart.setScaledContents(True)

        #item = QGraphicsPixmapItem(pix)
        #scene = QGraphicsScene(self)
        #scene.addItem(item)
        #self.ui.cdart.setScene(scene)        

    def set_cover(self, getcover = True, current_song = None, refresh = False):
        current_song = current_song or self.current_song
        
        if current_song:
            self.cover = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + "." +  "jpg")
            debug(self_cover = self.cover)
        if not MPD.check_is_image(self.cover):
            self.cover = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + "." +  "png")
            debug(self_cover = self.cover)
        debug(getcover = getcover)
        if getcover:
            debug(check = MPD.check_is_image(self.cover))
            if not MPD.check_is_image(self.cover) or refresh:
                self.cover = MPD.get_cover(current_song, self.music_dir)
                debug(self_cover = self.cover)
            
        debug(self_cover = self.cover)
        
        if MPD.check_is_image(self.cover):
            self.setWindowIcon(QIcon(self.cover))
            self.setPixmap(self.cover)
        return self.cover
        
    def setShortcut(self):
        self.quit_shortcut = QShortcut(QKeySequence("esc"), self)
        self.quit_shortcut.activated.connect(self.quit)
        
        #try:
            #self.dark_view.quit_shortcut = QShortcut(QKeySequence("esc"), self)
            #self.dark_view.quit_shortcut.activated.connect(self.quit)
        #except:
            #pass

        self.quit_shortcut = QShortcut(QKeySequence("q"), self)
        self.quit_shortcut.activated.connect(self.quit)
        
        #try:
            #self.dark_view.quit_shortcut = QShortcut(QKeySequence("q"), self)
            #self.dark_view.quit_shortcut.activated.connect(self.quit)
        #except:
            #pass
        
        self.next_shortcut = QShortcut(QKeySequence("n"), self)
        self.next_shortcut.activated.connect(self.play_next)
        
        #try:
            #self.dark_view.next_shortcut = QShortcut(QKeySequence("n"), self)
            #self.dark_view.next_shortcut.activated.connect(self.play_next)
        #except:
            #pass
        
        self.next_shortcut = QShortcut(QKeySequence("r"), self)
        self.next_shortcut.activated.connect(self.play_prev)
        
        self.next_shortcut = QShortcut(QKeySequence("P"), self)
        self.next_shortcut.activated.connect(self.play_pause)
        
        self.next_shortcut = QShortcut(QKeySequence("p"), self)
        self.next_shortcut.activated.connect(self.play_pause)                
        
        #try:
            #self.dark_view.next_shortcut = QShortcut(QKeySequence("p"), self)
            #self.dark_view.next_shortcut.activated.connect(self.play_prev)
        #except:
            #pass

    def eventFilter(self, obj, event):
        #print("event.type():", event.type())
        # if (event.type() == QtCore.QEvent.Resize):
                # print( 'Inside event Filter')
        return super().eventFilter(obj, event)
    
    def keyPressEvent(self, event):
        keyname = ''
        key = event.key()
        modifiers = int(event.modifiers())

        keyname = QKeySequence(modifiers + key).toString()
        try:
            logger.debug("keyname: " + keyname)
        except:
            pass
        # print("self.ui.tabWidget.getCurrentIndex:", self.ui.tabWidget.currentIndex())

        if (modifiers and modifiers & MOD_MASK == modifiers and
            key > 0 and key != Qt.Key_Shift and key != Qt.Key_Alt and
            key != Qt.Key_Control and key != Qt.Key_Meta):

            logger.debug('event.text(): %r' % event.text())
            logger.debug('event.key(): %d, %#x, %s' % (key, key, keyname))

            #if keyname == 'Ctrl+C':
                #self.select_project_dialog()
        #if keyname == 'Down':
            #self.move_next_Scroll(event, 30)
        #elif keyname == 'Up':
            #self.move_previous_Scroll(event, 30)
        #elif keyname == 'PgDown':
            ## print("PgUp .................")
            #self.move_next_Scroll(event, 200)
        #elif keyname == 'PgUp':
            ## print("PgDown .................")
            #self.move_previous_Scroll(event, 200)
        if keyname == 'Left':
            self.seek_prev()
        elif keyname == 'Right':
            self.seek_next()
        elif keyname == 'N':
            self.play_next()
        elif keyname == 'P':
            self.play_prev()
        elif keyname == 'Q' or keyname == 'ESC':
            os.kill(os.getpid(), signal.SIGTERM)
        self.keyPressed.emit(keyname)
    
    def seek_next(self):
        MPD.conn('seek', (int(self.current_song.get('pos')), float(self.current_state.get('time').split(":")[0]) + float(self.CONFIG.get_config('playback', 'seek', '10') or 10)))
    def seek_prev(self):
        MPD.conn('seek', (int(self.current_song.get('pos')), float(self.current_state.get('time').split(":")[0]) - float(self.CONFIG.get_config('playback', 'seek', '10') or 10)))
    def play_next(self):
        MPD.conn('next')
    def play_prev(self):
        MPD.conn('previous')
    #def get_dev_ip(self, suggest = None):
        #data = []
        #for ifaceName in interfaces():
            #addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr':''}] )]
            #debug(addresses = addresses)
            ##print('{}: {}'.format(ifaceName, ", ".join(addresses)))
            #data.append(", ".join(addresses))
        #debug(data = data)
        #data = list(filter(None, data))
        #if suggest:
            #ip1 = suggest.split(".")[:-1]
            #debug(ip1 = ip1)
            #ip = list(filter(lambda k: k.split(".")[:-1] == ip1, data))
            #debug(ip = ip)
        #return ip[0]
        
    def play_pause(self):
        MPD.conn('pause')
    def play_play(self):
        MPD.conn('play')    
    def setToolTip(self):
        self.ui.read_bt.setToolTip('<b>r</b>')
        self.ui.unread_bt.setToolTip('<b>u</b>')
        self.ui.delete_bt.setToolTip('<b>d or DELETE</b>')
        self.ui.except_bt.setToolTip('<b>x</b>')
        self.ui.export_bt.setToolTip('<b>e</b>')
        self.ui.help_bt.setToolTip('<b>h ~ Show Help</b>')
        self.ui.attachment_bt.setToolTip('<b>a ~ Show attachments</b>')
        self.ui.next_bt.setToolTip('<b>. (dot) ~ go next page</b>')
        self.ui.back_bt.setToolTip('<b>, (comma) ~ go previous page</b>')
        self.ui.o_browser_bt.setToolTip('<b>o ~ open in default browser</b>')

    

def usage(path=None):
    parser = argparse.ArgumentParser('mpdart', epilog = make_colors('MPD Client info + Art', 'ly'))
    parser.add_argument('-c', '--config', help = 'Prefer use config from file', action = 'store')
    parser.add_argument('-s', '--cover-server', help = 'Run cover server',  action = 'store_true')
    parser.add_argument('-S', '--cover-server-host', help = 'Listen cover server on, default = "0.0.0.0"', action = 'store')
    parser.add_argument('-P', '--cover-server-port', help = 'Listen cover server on port, default = "8800"', action = 'store', type = int)
    parser.add_argument('-p', '--music-dir', help = 'Music dir from config file', action = 'store', default = path)
    parser.add_argument('--mpd-host', help = 'MPD Server host, default = "127.0.0.1"', action = 'store')#, default = '127.0.0.1')
    parser.add_argument('--mpd-port', help = 'MPD Server port, default = "6600"', action = 'store', type = int, default = 6600)
    parser.add_argument('-t', '--sleep', help = 'Time interval, default = 1 second', dest = 'second', action = 'store', type = int, default = 1)
    parser.add_argument('-r', '--repeat-to', help = 'Repeat to number or jump after song to track playlist number, format: N1,N2 , N1 = from N2 to, if song get N1 then song will jump to N2, if N1 = ?|#|. N1 will set as curret number/pos, "c" for N1/N2 clear repeat/jump', action = 'store', nargs = 2)
    if len(sys.argv) == 1 and not path:
        parser.print_help()
        
        MPD_HOST = MPD.host
        MPD_PORT = MPD.port
        
        app = QApplication(sys.argv)
        View = Art()
        
        #apply_stylesheet(app, theme = 'dark_yellow.xml', invert_secondary = False)
        qtmodern.styles.dark(app)
        #app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        View.dark_view = qtmodern.windows.ModernWindow(View)
        View.dark_view.setMaximumSize(View.maximumSize())
        View.dark_view.setMaximumHeight(View.maximumHeight())
        View.dark_view.setMaximumWidth(View.maximumWidth())
        View.dark_view.setFixedSize(View.maximumWidth() + 2, View.maximumHeight() + 31)
        try:
            View.installEventFilter(View.dark_view)
        except:
            pass
        if MPD.CONFIG.get_config('title', 'bar'):
            try:
                View.dark_view.setWindowFlag(Qt.FramelessWindowHint)
            except:
                #print(traceback.format_exc())
                logger.error(traceback.format_exc())
        #self.dark_view.setWindowTitle()
        logger.warning('showing ....')
        View.dark_view.show()
        View.show()
        View.showData()
        app.exec_()
        
    else:
        #global MPD_HOST
        #global MPD_PORT
        #global MPD_MUSIC_DIR
        #global MPD_SLEEP
        #global APP
        
        args = parser.parse_args()
        
        if args.config and os.path.isfile(args.config):
            CONFIG = configset(args.config)
            CONFIGFILE = args.config
        
        if args.mpd_host: MPD_HOST = args.mpd_host
        if args.mpd_port: MPD_PORT = args.mpd_port        
        
        MPD.host = args.mpd_host or MPD.CONFIG.get_config('mpd', 'host') or os.getenv('MPD_HOST') or MPD.host
        MPD.port = args.mpd_port or MPD.CONFIG.get_config('mpd', 'port') or os.getenv('MPD_PORT') or MPD.port
        
        debug(args_music_dir = args.music_dir)

        MPD_HOST = MPD.host
        MPD_PORT = MPD.port
        MPD_MUSIC_DIR = args.music_dir
        print("MPD_MUSIC_DIR:", MPD_MUSIC_DIR)
        MPD_SLEEP = MPD.sleep or 1000
        if args.second: MPD_SLEEP = (args.second * 1000) or MPD_SLEEP

        debug(MPD_HOST = MPD_HOST)
        debug(MPD_PORT = MPD_PORT)
        
        debug(MPD_MUSIC_DIR = MPD_MUSIC_DIR)
        debug(MPD_SLEEP = MPD_SLEEP)    

        #app = QApplication(sys.argv)
        #c = MPDArt(args.mpd_host, args.mpd_port, args.second, music_dir = args.music_dir)
        if args.repeat_to:
            fr, to = args.repeat_to
            logger.warning("get jump from: {}".format(fr))
            logger.warning("get jump to  : {}".format(to))                                
            if fr == '.' or fr == "#" or fr == "?":
                MPD.current_song = MPD.current_song or MPD.conn('currentsong')
                fr = MPD.current_song.get('id')
            logger.warning("set jump from: {}".format(fr))
            logger.warning("set jump to  : {}".format(to))                
            if str(fr).isdigit() and str(to).isdigit():
                MPD.CONFIG.write_config('repeat', 'jump', "{},{}".format(fr, to))
                MPD.jump_from = fr
                MPD.jump_to = to
            elif fr == 'c' and to == 'c':
                MPD.CONFIG.write_config('repeat', 'jump', '')
                
        if args.cover_server:
            MPD.cover_server(args.cover_server_host, args.cover_server_port)
        else:
            if args.music_dir:
                app = QApplication(sys.argv)
                View = Art(MPD_HOST, MPD_PORT, MPD_SLEEP, None, MPD.icon, MPD_MUSIC_DIR)
                
                #apply_stylesheet(app, theme = 'dark_yellow.xml', invert_secondary = False)
                qtmodern.styles.dark(app)
                #app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
                View.dark_view = qtmodern.windows.ModernWindow(View)
                View.dark_view.setMaximumSize(View.maximumSize())
                View.dark_view.setMaximumHeight(View.maximumHeight())
                View.dark_view.setMaximumWidth(View.maximumWidth())
                View.dark_view.setFixedSize(View.maximumWidth() + 2, View.maximumHeight() + 31)
                try:
                    View.installEventFilter(View.dark_view)
                except:
                    pass
                if MPD.CONFIG.get_config('title', 'bar'):
                    try:
                        View.dark_view.setWindowFlag(Qt.FramelessWindowHint)
                    except:
                        #print(traceback.format_exc())
                        logger.error(traceback.format_exc())
                #self.dark_view.setWindowTitle()
                logger.warning('showing ....')
                View.dark_view.show()
                View.show()
                View.showData()
                app.exec_()
                #View.showData()
            else:
                logger.warning(make_colors("No Music dir !", 'lw', 'r'))    

if __name__ == '__main__':
    #usage()
    #app = QApplication(sys.argv)
    #c = MPDArt('192.168.0.2', 6600, 1, music_dir = r'f:\MUSICS')
    #c.get_cover()
    #MPD.usage()
    usage()
    #c.show()
    #c.cover_server()
    #app.exec_()
    #cs = c.conn('currentsong', refresh = True)
    #debug(cs = cs)
    #os.environ.update({'DEBUG': '1',})
    #c.get_cover_lastfm(cs)
    #os.environ.update({'DEBUG': '',})
