# MPD-Art
--------------------
    
Music Player Daemon Current playing info
    

![screenshot](https://github.com/cumulus13/mpdart/blob/8dfe1e539cd5c7bd9cfe9e501c965456be8343a8/screenshot.png "Screenshot Example")
    
## requirement
-------------------
    - netifaces
    - make_colors
    - pydebugger
    - mutagen >= 1.43.1
    - requests
    - PyQT5
    - qdarkstyle
    - qtmodern
    - qt-material
    - configset
    - python-mpd2 / python-mpd
    - xnotify
    - mimelist
    - python 3+
    
## usage
----------------
    
cover: will check image file for local/remote before if it run on local then check tag if not exist then if not valid it will get cover from cover server or last.fm (api key requirement). (`optional`) run mpd as `cover server` (`-s`) with `-S, -P and -p` options on where mpd server running before if you want get cover from cover server.
    
```bash
    usage: mpdart [-h] [-s] [-S COVER_SERVER_HOST] [-P COVER_SERVER_PORT] [-p MUSIC_DIR] [--mpd-host MPD_HOST] [--mpd-port MPD_PORT]
          [-t SECOND]
    
    optional arguments:
      -h, --help            show this help message and exit
      -s, --cover-server    Run cover server
      -S COVER_SERVER_HOST, --cover-server-host COVER_SERVER_HOST
                            Listen cover server on, default = "0.0.0.0"
      -P COVER_SERVER_PORT, --cover-server-port COVER_SERVER_PORT
                            Listen cover server on port, default = "8800"
      -p MUSIC_DIR, --music-dir MUSIC_DIR
                            Music dir from config file
      --mpd-host MPD_HOST   MPD Server host, default = "127.0.0.1"
      --mpd-port MPD_PORT   MPD Server port, default = "6600"
      -t SECOND, --sleep SECOND
                            Time interval, default = 1 second
    
    MPD Client info + Art
```
    
* example:
```bash
    # running as cover server on MPD Server
    python mpdart.py -s -S 192.168.0.3 -P 8800 -p /mnt/musics
    
    # running mpdart as a client on any guest / pc
    python mpdart.py -p /mnt/musics
```

    you can use config file `mpdart.ini` to direct setup some options
    
## author
---------
[cumulus13](cumulus13@gmail.com)
    