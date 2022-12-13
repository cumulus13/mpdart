from __future__ import print_function

import logging
logger = logging.getLogger('MPD-Art')
logger.setLevel(logging.DEBUG)

from make_colors import make_colors
from pydebugger.debug import debug
import os
import sys
import http.server as SimpleHTTPServer
import socketserver as SocketServer

class CoverServer(SimpleHTTPServer.SimpleHTTPRequestHandler):
    #global MPD_HOST
    #global MPD_PORT
    #global MPD_MUSIC_DIR
    #global MPD_SLEEP
    DEFAULT_COVER = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'no-cover.png')
    app = QApplication(sys.argv)
    #mpdart = MPDArt('192.168.0.2', 6600, 1, music_dir = r'f:\MUSICS')
    debug(MPD_HOST = MPD_HOST, debug = 1)
    debug(MPD_PORT = MPD_PORT, debug = 1)
    debug(MPD_MUSIC_DIR = MPD_MUSIC_DIR, debug = 1)
    debug(MPD_SLEEP = MPD_SLEEP, debug = 1)    
    mpdart = MPDArt(MPD_HOST, MPD_PORT, MPD_SLEEP, MPD_MUSIC_DIR)
    CONFIG = mpdart.CONFIG
    
    def do_GET(self):
        print("self.path:", self.path)
        debug(self_path = self.path, debug = 1)
        if self.path == '/':
            current_song = self.mpdart.conn('currentsong', (), refresh = True)
            cover = self.mpdart.get_cover(current_song.get('file'))
            debug(cover = cover, debug = 1)
            if os.path.isfile(cover):
                f = open(cover, 'rb')
                self.send_response(200)
                self.send_header('Content-type', 'image/png')
                self.end_headers()
                self.wfile.write(f.read())
                f.close()
            else:
                if not os.path.isfile(os.path.dirname(os.path.realpath(__file__)), 'index.html'):
                    self.wfile.write.write("<html><head><title>No-Cover</title></head><body><h1>No-Cover</h1></body></html>")
                else:
                    with open(os.path.isfile(os.path.dirname(os.path.realpath(__file__)), 'index.html'), 'rb') as fi:
                        self.send_response(200)                    
                        self.wfile.write.write(fi.read())
                        
        return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
