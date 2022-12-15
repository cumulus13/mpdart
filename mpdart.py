#!/usr/bin/env python
# encoding:utf-8
# Author: cumulus13
# email: cumulus13@gmail.com

from __future__ import print_function

from netifaces import interfaces, ifaddresses, AF_INET
from make_colors import make_colors
from pydebugger.debug import debug
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
from mutagen.id3 import ID3
from mutagen.flac import FLAC
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
        logging.CRITICAL: warning + format + reset, 
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

MPD_HOST = '127.0.0.1'
MPD_PORT = 6600
MPD_MUSIC_DIR = '' 
MPD_SLEEP = 1

MOD_MASK = (Qt.CTRL | Qt.ALT | Qt.SHIFT | Qt.META)

class MPDArt(QDialog):
    keyPressed = pyqtSignal(str)
    CONFIG = configset()
    host = CONFIG.get_config('mpd', 'host') or os.getenv('MPD_HOST') or '127.0.0.1'
    port = CONFIG.get_config('mpd', 'port') or os.getenv('MPD_PORT') or 6600
    configfile = CONFIG.get_config('config', 'file')
    sleep = CONFIG.get_config('sleep', 'time') or 1000
    icon = CONFIG.get_config('icon', 'path')
    music_dir = CONFIG.get_config('mpd', 'music_dir')
    timeout = CONFIG.get_config('mpd', 'timeout')
    CONN = MPDClient()
    debug(host = host)
    debug(port = port)
    CONN.connect(host, port)
    first_current_song = False
    first_state = False
    command = None
    last_dir = None
    cover = ''
    DEFAULT_COVER = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'no-cover.png')
    current_song = {}
    COVER_TEMP_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'covers')
    FAIL_LAST_FM = False
    current_state = {}
    first = False

    def __init__(self, host = None, port = None, sleep = None, configfile = None, icon = None, music_dir = None):
        
        if sys.version_info.major == 3:
            super().__init__()
        else:
            super(MPDArt(), self).__init__()
        #QDialog.__init__(self, None, QtCore.Qt.WindowStaysOnTopHint)
        
        self.ui = Ui_mpdart()
        self.ui.setupUi(self)        
        self.setShortcut()
        self.installEventFilter(self)
        try:
            self.installEventFilter(self.dark_view)
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
        if host and not host0 == self.host:
            self.CONN.connect(self.host, self.port)
                
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
        
        #fi = self.ui.artist.fontInfo()
        #print("font artist:", fi.pointSize())
        
        self.timer = QTimer(self)
        #self.timer.timeout.connect(self.showTime)
        self.timer.timeout.connect(self.showData)
        self.timer.start(self.CONFIG.get_config('sleep', 'time', '1000'))
        
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
            
    def send_notify(self, message, title, event = 'play', cover_art = None, app = 'MPD-Art'):
        cover_art = cover_art or self.DEFAULT_COVER
        debug(cover_art = cover_art)
        debug(NOTIFY2 = NOTIFY2)
        debug(XNOTIFY = XNOTIFY)
        if NOTIFY2 and self.CONFIG.get_config('notification', 'notify2') == 1:
            logger.debug("send notify [LINUX]: {}".format(message))
            pnotify = pynotify.Notification("MPD-Art " + title + " " + event, message, "file://" + cover_art)
            pnotify.show()            
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
            notify.send('MPD-Art: ' + title + " " + event, message, app, event, growl_host, icon = cover_art, iconpath = cover_art, ntfy = ntfy, nfty_sever = ntfy_server, pushbullet_api = pushbullet_api, nmd_api = nmd_api, pushbullet = pushbullet, nmd = nmd, growl = growl)
            
        
    def setOnTop(self):
        if self.ui.cb_top.isChecked():
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
            self.bring_to_front(self)
        else:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

    def bring_to_front(self, window = None):
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
    
    def conn(self, func, args = (), host = None, port = None, refresh = False, repeat = False):
        if host and not host == self.host or port and not port == self.port:
            self.CONN.connect(host, port, self.timeout)
            self.host = host
            self.port = port
        else:
            host = host or self.host or '127.0.0.1'
            port = port or self.port or 6600
        timeout = self.timeout or self.CONFIG.get_config('mpd', 'timeout') or None
        debug(host = host)
        debug(port = port)
        debug(timeout = timeout)
        debug(refresh = refresh)
        debug(func = func)

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
        except:
            #if not self.first:
                #print(traceback.format_exc())
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
            except:
                if not self.first:
                    #print(traceback.format_exc())
                    logger.error(traceback.format_exc)
                    self.first = True
            #self.first = True
        self.command = func
        return {}

    def setPixmap(self, image):
        pix = QPixmap(image)
        self.ui.cdart.setPixmap(pix)
        self.ui.cdart.setScaledContents(True)

        #item = QGraphicsPixmapItem(pix)
        #scene = QGraphicsScene(self)
        #scene.addItem(item)
        #self.ui.cdart.setScene(scene)        

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
            f = FLAC(music_file)
            if f.picture:
                data_cover = f.picture[0]
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

    def get_cover(self, current_song, music_dir = None, get_lastfm_cover = True, refresh = False):
        debug(music_dir = music_dir)
        music_dir = music_dir or MPD_MUSIC_DIR or self.music_dir
        debug(music_dir = music_dir)
        
        if os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + ".jpg") or os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + ".png"):
            self.cover = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + ".jpg") or os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + ".png")
            debug(self_cover = self.cover)
            if self.check_is_image(self.cover):
                debug(self_cover = self.cover)
                return os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + ".jpg") or os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + ".png")
        debug('No cover')
        
        if sys.platform == 'win32':
            sep = "\\"
        else:
            sep = "/"
        
        debug(file = current_song.get('file'))
        img_data = self.conn('albumart', (current_song.get('file'), ))
        ext = 'jpg'
        if img_data:
            img_data = img_data.get('binary')
        debug(img_data = len(img_data))
        
        if img_data and current_song:
            img = Image.open(io.BytesIO(img_data))
            debug(check_ext = mimelist.get2(img.format))
            ext = mimelist.get2(img.format)[1]
            if not os.path.isdir(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'))):
                os.makedirs(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown')))
            img.save(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + "." +  ext))
            
        if os.path.isfile(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + "." +  ext)):
            if self.check_is_image(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + "." +  ext)):
                self.cover = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + "." +  ext)
                debug(self_cover_X = self.cover)
                return os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover' + "." +  ext)
        debug(refresh = refresh)
        debug(self_cover = self.cover)
        debug(check_cover = self.check_is_image(self.cover))
        
        if refresh: self.cover = ''
        debug(self_cover = self.cover)
        
        if self.cover and self.check_is_image(self.cover):
            if not os.path.isfile(self.cover):
                if sys.platform == 'win32':
                    self.cover = os.path.join(music_dir, sep.join(os.path.splitext(current_song.get('file'))[0].split("/")[1:])) + '.jpg'
                else:
                    self.cover = os.path.join(music_dir, os.path.splitext(current_song.get('file'))[0]) + '.jpg'
            debug(self_cover = self.cover)
            if not os.path.isfile(self.cover):
                if sys.platform == 'win32':
                    self.cover = os.path.join(music_dir, sep.join(os.path.splitext(current_song.get('file'))[0].split("/")[1:])) + '.png'
                else:
                    self.cover = os.path.join(music_dir, os.path.splitext(current_song.get('file'))[0]) + '.png'
            debug(self_cover = self.cover)
            #if os.path.isfile(self.cover):
            if self.check_is_image(self.cover):
                #print('return 1.....')
                return self.cover        
            if not self.cover or not self.check_is_image(self.cover):
                cover_file = os.path.join(music_dir, sep.join(file.split("/")[1:]))
                debug(cover_file = cover_file)
                try:
                    self.cover = self.get_cover_tag(cover_file)
                except:
                    pass
            if self.check_is_image(self.cover):
                #print('return 2.....')
                return self.cover
        debug(self_cover = self.cover)
        valid_cover = list(filter(None, [i.strip() for i in re.split(",|\n|\t", self.CONFIG.get_config('cover', 'valid'))])) or ['cover.jpg', 'cover2.jpg', 'cover.png', 'cover2.png', 'folder.jpg', 'folder.png', 'front.jpg', 'front.png', 'albumart.jpg', 'albumart.png', 'folder1.jpg', 'folder1.png', 'back.jpg', 'back.png']
        
        debug(cover_check_1 = current_song.get('file').split("/")[1:])
        #debug(file = file)
        for i in valid_cover:
            #if sys.platform == 'win32':
            debug(split_drive = os.path.join(music_dir, sep.join(os.path.dirname(current_song.get('file')).split("/")[1:]), i), sep = sep)
            if sys.platform == 'win32':
                split_drive = os.path.join(music_dir, sep.join(os.path.dirname(current_song.get('file')).split("/")[1:]))
            else:
                split_drive = os.path.join(music_dir, sep.join(os.path.dirname(current_song.get('file')).split("/")))
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
            if self.cover and self.check_is_image(self.cover):
                #print('return 3.....')
                debug(self_cover = self.cover)
                #sys.exit()
                cover_dir = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'))
                if not os.path.isdir(cover_dir): os.makedirs(cover_dir)
                try:
                    shutil.copy2(self.cover, cover_dir)
                except Exception as e:
                    #print(make_colors("shutil:", 'lw', 'r') + " " + make_colors(str(e), 'lw', 'bl'))
                    logger.error(e)
                    if os.getenv('TRACEBACK'):
                        #print(traceback.format_exc())
                        logger.error(traceback.format_exc())
                return self.cover
            else:
                self.cover: self.cover = ''
        #sys.exit()
        if self.cover and self.check_is_image(self.cover):
            debug(self_cover = self.cover)
            #print('return 4.....')
            #sys.exit()
            return self.cover
        try:
            with open(os.path.join(self.COVER_TEMP_DIR, 'cover.jpg'), 'wb') as fc:
                chost = self.CONFIG.get_config('cover_server', 'host')
                debug(chost = chost)
                if chost == '0.0.0.0': chost = '127.0.0.1'
                try:
                    fc.write(requests.get('http://' + chost + ":" + str(self.CONFIG.get_config('cover_server', 'port'))).content)
                except:
                    pass
            if self.check_is_image(os.path.join(self.COVER_TEMP_DIR, 'cover.jpg')):
                self.cover = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover.jpg')
                debug(self_cover = self.cover)
                #sys.exit()
                return os.path.join(self.COVER_TEMP_DIR, 'cover.jpg')
        except:
            #print(traceback.format_exc())
            logger.error(traceback.format_exc())
        #sys.exit()
        if get_lastfm_cover:
            debug(self_FAIL_LAST_FM = self.FAIL_LAST_FM)
            if not self.FAIL_LAST_FM:
                self.cover = self.get_cover_lastfm()[0]
                debug(self_cover = self.cover)
                debug(cover_split = self.cover.split(os.path.sep)[-1])
                if not self.cover or self.cover.split(os.path.sep)[-1] == 'no-cover.png': self.FAIL_LAST_FM = True
                debug(self_FAIL_LAST_FM = self.FAIL_LAST_FM)
        debug(self_cover = self.cover)
        if not self.check_is_image(self.cover):
            return self.DEFAULT_COVER
        return self.cover

    def check_is_image(self, file):
        try:
            im = Image.open(file)
            im.verify()
            im.close()
            return True
        except:
            return False
        
    def showData(self, host = None, port = None, timeout = None):
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
        current_song = {}
        current_state = {}
        disc = "0"
        
        #c = self.conn(host, port)
        #current_state = self.conn(host, port).status()
        try:
            current_state = self.CONN.status()
        except ConnectionError:
            try:
                current_state = self.conn('status', host = host, port = port, refresh = True)
                debug(current_state = current_state)
                self.CONN.connect(host, port, timeout)
            except mpd.base.ConnectionError:
                current_state = {}
        except mpd.base.ConnectionError:
            current_state = {}        
        debug(current_state = current_state)
        try:
            current_song = self.CONN.currentsong()
        except ConnectionError:
            try:
                current_song = self.conn('currentsong', host = host, port = port, refresh = True)
                debug(current_song = current_song)
                self.CONN.connect(host, port, timeout)
            except mpd.base.CommandError:
                current_song = {}
        except mpd.base.ConnectionError:
            current_state = {}        
        if not self.current_song == current_song and current_song: self.cover = ''
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
                album + " / " + \
                albumartist + " (" + \
                date + ")"
            )
            
            self.ui.artist.setText(
                artist
            )
            
            self.ui.comment.setText(current_state.get('state'))

            self.last_dir = os.path.dirname(current_song.get('file'))
            if label: label = label + " - "
            
        if current_state.get('state') == 'play' or current_state.get('state') == 'pause':
            self.ui.pbar.setValue(int((float(current_state.get('elapsed')) / float(current_state.get('duration'))) * 100))
            bitrate = current_state.get('bitrate')
            self.ui.bitrate.setText(
                bitrate + " - " + \
                label 
            )
        #if current_song and (not os.path.isfile(os.path.join(self.COVER_TEMP_DIR, current_song.get('artist'), current_song.get('album'), 'cover.jpg')) or not os.path.isfile(os.path.join(self.COVER_TEMP_DIR, current_song.get('artist'), current_song.get('album'), 'cover.png'))):
        if current_song:
            self.cover = os.path.join(self.COVER_TEMP_DIR, current_song.get('artist'), current_song.get('album'), 'cover' + "." +  "jpg")
            debug(self_cover = self.cover)
        if not self.check_is_image(self.cover):
            self.cover = os.path.join(self.COVER_TEMP_DIR, current_song.get('artist'), current_song.get('album'), 'cover' + "." +  "png")
            debug(self_cover = self.cover)
        if not self.check_is_image(self.cover):
            self.cover = self.get_cover(current_song, self.music_dir)
            debug(self_cover = self.cover)
            
        #debug(self_cover = self.cover)
        
        if self.check_is_image(self.cover):
            #print("set-cover: {}".format(self.cover))
        #if self.cover:
            #if os.path.isfile(self.cover):
            self.setWindowIcon(QIcon(self.cover))
            self.setPixmap(self.cover)

        debug(current_song = current_song)
        debug(self_current_song = self.current_song)
        debug(current_state = current_state)
        debug(self_current_state = self.current_state)
        msg = track + "/" +\
            disc  + ". " +\
            title + " (" +\
            duration + ")" +\
            "\n" +\
            artist + "\n" +\
            album + "\n" +\
            genres + "\n" + \
            current_state.get('state')
        if not self.current_song.get('file') == current_song.get('file') and title:            
            self.send_notify(msg, '{} ...'.format(current_state.get('state')), current_state.get('state'), self.cover)
            logger.debug("send info current song")
            #self.first = True
            #self.bring_to_front(self)
            try:
                self.bring_to_front(self.dark_view)
            except:
                #self.bring_to_front(self)
                pass
        self.current_song = current_song
        
        if not self.current_state.get('state') == current_state.get('state') and not self.first:
            self.send_notify(msg, '{} ...'.format(current_state.get('state')), current_state.get('state'), self.cover)
            logger.debug("send info current state")
        self.current_state = current_state
        
        debug(current_song = current_song)
        debug(self_current_song = self.current_song)
        debug(current_state = current_state)
        debug(self_current_state = self.current_state)
        #print("-" *125)
        #sys.exit()
        self.first = True
        
    def setShortcut(self):
        self.quit_shortcut = QShortcut(QKeySequence("esc"), self)
        self.quit_shortcut.activated.connect(self.close)

        self.quit_shortcut = QShortcut(QKeySequence("q"), self)
        self.quit_shortcut.activated.connect(self.close)
        
        self.next_shortcut = QShortcut(QKeySequence("n"), self)
        self.next_shortcut.activated.connect(self.play_next)
        
        self.next_shortcut = QShortcut(QKeySequence("p"), self)
        self.next_shortcut.activated.connect(self.play_prev)        

    def eventFilter(self, obj, event):
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
        self.keyPressed.emit(keyname)
    
    def seek_next(self):
        self.conn('seek', (int(self.current_song.get('pos')), float(self.current_state.get('time').split(":")[0]) + float(self.CONFIG.get_config('playback', 'seek', '10') or 10)))
    def seek_prev(self):
        self.conn('seek', (int(self.current_song.get('pos')), float(self.current_state.get('time').split(":")[0]) - float(self.CONFIG.get_config('playback', 'seek', '10') or 10)))
    def play_next(self):
        self.conn('next')
    def play_prev(self):
        self.conn('previous')
    def get_dev_ip(self, suggest = None):
        data = []
        for ifaceName in interfaces():
            addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr':''}] )]
            debug(addresses = addresses)
            #print('{}: {}'.format(ifaceName, ", ".join(addresses)))
            data.append(", ".join(addresses))
        debug(data = data)
        data = list(filter(None, data))
        if suggest:
            ip1 = suggest.split(".")[:-1]
            debug(ip1 = ip1)
            ip = list(filter(lambda k: k.split(".")[:-1] == ip1, data))
            debug(ip = ip)
        return ip[0]
        
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

    def cover_server(self, host =None, port = None):
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

    def usage(self):
        parser = argparse.ArgumentParser('mpdart', epilog = make_colors('MPD Client info + Art', 'ly'))
        parser.add_argument('-s', '--cover-server', help = 'Run cover server',  action = 'store_true')
        parser.add_argument('-S', '--cover-server-host', help = 'Listen cover server on, default = "0.0.0.0"', action = 'store')
        parser.add_argument('-P', '--cover-server-port', help = 'Listen cover server on port, default = "8800"', action = 'store', type = int)
        parser.add_argument('-p', '--music-dir', help = 'Music dir from config file', action = 'store')
        parser.add_argument('--mpd-host', help = 'MPD Server host, default = "127.0.0.1"', action = 'store', default = '127.0.0.1')
        parser.add_argument('--mpd-port', help = 'MPD Server port, default = "6600"', action = 'store', type = int, default = 6600)
        parser.add_argument('-t', '--sleep', help = 'Time interval, default = 1 second', dest = 'second', action = 'store', type = int, default = 1)
        if len(sys.argv) == 1:
            parser.print_help()
        else:
            global MPD_HOST
            global MPD_PORT
            global MPD_MUSIC_DIR
            global MPD_SLEEP        
            args = parser.parse_args()
            self.host = args.mpd_host or os.getenv('MPD_HOST') or self.host
            self.port = args.mpd_port or os.getenv('MPD_PORT') or self.port
            debug(args_music_dir = args.music_dir)

            MPD_HOST = args.cover_server_host
            MPD_PORT = args.cover_server_port
            MPD_MUSIC_DIR = args.music_dir
            MPD_SLEEP = args.second

            debug(MPD_HOST = MPD_HOST)
            debug(MPD_PORT = MPD_PORT)
            debug(MPD_MUSIC_DIR = MPD_MUSIC_DIR)
            debug(MPD_SLEEP = MPD_SLEEP)    

            #app = QApplication(sys.argv)
            #c = MPDArt(args.mpd_host, args.mpd_port, args.second, music_dir = args.music_dir)
            if args.cover_server:
                self.cover_server(args.cover_server_host, args.cover_server_port)
            else:
                if args.music_dir:
                    app = QApplication(sys.argv)
                    #apply_stylesheet(app, theme = 'dark_yellow.xml', invert_secondary = False)
                    qtmodern.styles.dark(app)
                    #app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
                    self.dark_view = qtmodern.windows.ModernWindow(self)
                    self.dark_view.setMaximumSize(self.maximumSize())
                    self.dark_view.setMaximumHeight(self.maximumHeight())
                    self.dark_view.setMaximumWidth(self.maximumWidth())
                    self.dark_view.setFixedSize(self.maximumWidth() + 2, self.maximumHeight() + 31)
                    try:
                        self.installEventFilter(self.dark_view)
                    except:
                        pass
                    if self.CONFIG.get_config('title', 'bar'):
                        try:
                            self.dark_view.setWindowFlag(Qt.FramelessWindowHint)
                        except:
                            #print(traceback.format_exc())
                            logger.error(traceback.format_exc())
                    #self.dark_view.setWindowTitle()
                    self.dark_view.show()
                    self.show()
                    app.exec_()
                else:
                    logger.warning(make_colors("No Music dir !", 'lw', 'r'))    

class CoverServer(SimpleHTTPServer.SimpleHTTPRequestHandler):
    #global MPD_HOST
    #global MPD_PORT
    #global MPD_MUSIC_DIR
    #global MPD_SLEEP
    DEFAULT_COVER = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'no-cover.png')
    app = QApplication(sys.argv)
    debug(MPD_HOST = MPD_HOST)
    debug(MPD_PORT = MPD_PORT)
    debug(MPD_MUSIC_DIR = MPD_MUSIC_DIR)
    debug(MPD_SLEEP = MPD_SLEEP)    
    MPD_MUSIC_DIR = "/mnt/musics" or None
    mpdart = MPDArt(music_dir = MPD_MUSIC_DIR)
    #mpdart = MPDArt(MPD_HOST, MPD_PORT, MPD_SLEEP, MPD_MUSIC_DIR)
    #CONFIG = mpdart.CONFIG

    def handle_one_request(self):
        logger.debug("CLIENT: " + self.client_address[0])
        if self.mpdart.CONFIG.get_config('cover_server', 'host') == '0.0.0.0':
            debug(client_address_netiface = self.mpdart.get_dev_ip(self.client_address[0]))
            self.mpdart.CONFIG.write_config('cover_server', 'host', self.mpdart.get_dev_ip(self.client_address[0]))
        
        return SimpleHTTPServer.SimpleHTTPRequestHandler.handle_one_request(self)
    
    def do_GET(self):
        logger.debug("self.path: " + self.path)
        cover = ''
        debug(self_path = self.path)
        if self.path == '/':
            logger.debug("self.PATH OK ")
            current_song = self.mpdart.conn('currentsong', (), refresh = True)
            debug(current_song = current_song)
            if current_song.get('file'):
                cover = self.mpdart.get_cover(current_song, self.MPD_MUSIC_DIR, refresh = True)
                debug(cover = cover)
                #sys.exit()
                #if not self.mpdart.check_is_image(cover) or cover.split(os.path.sep)[-1] == 'no-cover.png':
                    
            debug(cover = cover)
            if cover:
                if os.path.isfile(cover):
                    f = open(cover, 'rb')
                    self.send_response(200)
                    self.send_header('Content-type', 'image/png')
                    self.end_headers()
                    self.wfile.write(f.read())
                    f.close()
            else:
                logger.debug("CHECK FILE INDEX !")
                if not os.path.isfile(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'index.html')):
                    logger.debug("NO FILE INDEX !")
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"<html><head><title>No-Cover</title></head><body><h1>No-Cover</h1></body></html>")
                    logger.debug("END WRITE 1")
                else:
                    logger.debug("FILE INDEX EXISTS !")
                    with open(os.path.isfile(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'index.html')), 'rb') as fi:
                        self.send_response(200)                    
                        self.wfile.write(fi.read())
                        logger.debug("END WRITE 2")

        return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)


if __name__ == '__main__':
    #usage()
    app = QApplication(sys.argv)
    c = MPDArt('192.168.0.2', 6600, 1, music_dir = r'f:\MUSICS')
    #c.get_cover()
    c.usage()
    #c.show()
    #c.cover_server()
    #app.exec_()
    #cs = c.conn('currentsong', refresh = True)
    #debug(cs = cs)
    #os.environ.update({'DEBUG': '1',})
    #c.get_cover_lastfm(cs)
    #os.environ.update({'DEBUG': '',})