import http.server as SimpleHTTPServer
import socketserver as SocketServer
from pydebugger.debug import debug
from configset import configset
import os, signal, sys, re
import logging
from netifaces import interfaces, ifaddresses, AF_INET
from xnotify import notify
from mutagen.id3 import ID3
from mutagen.flac import FLAC
import mimelist
from make_colors import make_colors
import requests
import traceback
import time
from PIL import Image
import io
from mpd import MPDClient
import shutil
#from multiprocessing import Pool

NOTIFY2 = False
if not sys.platform == 'win32':
    try:
        import notify2 as pynotify
        NOTIFY2 = True
        if not pynotify.init("MPD status"):
            logger.error("warning: Unable to initialize dbus Notifications")
    except:
        NOTIFY2 = False


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
logger = logging.getLogger('MPD-Art-Cover-Server')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)

MPD_HOST = '127.0.0.1'
MPD_PORT = 6600
MPD_MUSIC_DIR = os.getcwd()
MPD_SLEEP = 1
DEFAULT_COVER = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'no-cover.png')
CONFIG = configset(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'mpdart.ini'))
CURRENT_SONG = {}

class CoverServer(SimpleHTTPServer.SimpleHTTPRequestHandler):
       
    debug(MPD_HOST = MPD_HOST)
    debug(MPD_PORT = MPD_PORT)
    debug(MPD_MUSIC_DIR = MPD_MUSIC_DIR)
    debug(MPD_SLEEP = MPD_SLEEP)
    first = False
    DEFAULT_COVER = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'no-cover.png')
    current_song = CURRENT_SONG
    COVER_TEMP_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'covers')
    FAIL_LAST_FM = False
    #process = None
    
    host = CONFIG.get_config('mpd', 'host') or os.getenv('MPD_HOST') or '127.0.0.1'
    port = CONFIG.get_config('mpd', 'port') or os.getenv('MPD_PORT') or 6600
    CONN = MPDClient()
    debug(host = host)
    debug(port = port)
    CONN.connect(host, port)
    first_current_song = False
    first_state = False
    
    def conn(self, func, args = (), host = None, port = None, refresh = False, repeat = False):
        if host and not host == self.host or port and not port == self.port:
            self.CONN.connect(host, port, self.timeout)
            self.host = host
            self.port = port
        else:
            host = host or self.host or '127.0.0.1'
            port = port or self.port or 6600
        timeout = self.timeout or CONFIG.get_config('mpd', 'timeout') or None
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
                    logger.error(traceback.format_exc())
                    self.first = True
            #self.first = True
        self.command = func
        return {}
    
    def check_is_image(self, file):
        try:
            im = Image.open(file)
            im.verify()
            im.close()
            return True
        except:
            return False
            
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
        api_key = CONFIG.get_config('lastfm', 'api')
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
                logger.warning(make_colors("Please install 'mpd_album_art' before: 'pip install git+http://github.com/jameh/mpd-album-art' or input lastfm api key in config file, '{}'".format(CONFIG.configname), 'lw', 'r'))
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
        music_dir = music_dir or MPD_MUSIC_DIR
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
                cover_file = os.path.join(music_dir, sep.join(current_song.get('file').split("/")[1:]))
                debug(cover_file = cover_file)
                try:
                    self.cover = self.get_cover_tag(cover_file)
                except:
                    pass
            if self.check_is_image(self.cover):
                #print('return 2.....')
                return self.cover
        debug(self_cover = self.cover)
        valid_cover = list(filter(None, [i.strip() for i in re.split(",|\n|\t", CONFIG.get_config('cover', 'valid'))])) or ['cover.jpg', 'cover2.jpg', 'cover.png', 'cover2.png', 'folder.jpg', 'folder.png', 'front.jpg', 'front.png', 'albumart.jpg', 'albumart.png', 'folder1.jpg', 'folder1.png', 'back.jpg', 'back.png']
        
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
        
        if self.check_is_image(os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover.' + ext)):
            self.cover = os.path.join(self.COVER_TEMP_DIR, (current_song.get('artist') or 'unknown'), (current_song.get('album') or 'unknown'), 'cover.' + ext)
            debug(self_cover = self.cover)
            #sys.exit()
            return self.cover
        
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
    
    def handle_one_request(self):
        logger.debug("CLIENT: " + self.client_address[0])
        if CONFIG.get_config('cover_server', 'host') == '0.0.0.0':
            debug(client_address_netiface = self.get_dev_ip(self.client_address[0]))
            CONFIG.write_config('cover_server', 'host', self.get_dev_ip(self.client_address[0]))
        
        return SimpleHTTPServer.SimpleHTTPRequestHandler.handle_one_request(self)
    
    def do_GET(self):
        current_song = self.current_song or self.conn('currentsong', refresh = True)
        logger.debug("current_song = {}".format(current_song))
        logger.debug("self.path: " + self.path)
        cover = ''
        debug(self_path = self.path)
        if self.path == '/':
            logger.debug("self.PATH OK ")
            debug(current_song = current_song)
            if current_song.get('file'):
                debug(MPD_MUSIC_DIR = MPD_MUSIC_DIR)
                cover = self.get_cover(current_song, MPD_MUSIC_DIR, refresh = True)
                logger.info("cover: {}".format(cover))
                #sys.exit()
                #if not self.check_is_image(cover) or cover.split(os.path.sep)[-1] == 'no-cover.png':
                    
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
    host, port = '127.0.0.1', 8811
    debug(len_sys_argv = len(sys.argv))
    if len(sys.argv) == 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
    elif len(sys.argv) == 2:
        host = sys.argv[1]
    elif len(sys.argv) == 4:
        host = sys.argv[1]
        port = int(sys.argv[2])
        MPD_MUSIC_DIR = sys.argv[3]
        
    debug(host = host)
    debug(port = port)
    host = host or CONFIG.get_config('cover_server', 'host') or '0.0.0.0'
    port = port or CONFIG.get_config('cover_server', 'port') or 8800
    debug(host = host)
    debug(port = port)    
    if host: CONFIG.write_config('cover_server', 'host', host)
    if port: CONFIG.write_config('cover_server', 'port', port)
    Handler = CoverServer
    if host:
        MPD_HOST = host
    if not port == MPD_PORT:
        MPD_PORT = port
    
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
    