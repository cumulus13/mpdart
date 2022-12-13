# MPD-Art
--------------------
    
    Music Player Daemon Current playing info
    
    ![screeshoot](screenshot.png "Screenshot Example")
    
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
    
cover will check for local before if it run on local than will be valid, for remote server mpd use must run `cover server' (`-s`) with `-S, -P and -p`
    
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

    use can use config file `mpdart.ini` to direct setup some options
    
## author
---------
[cumulus13](cumulus13@gmail.com)
    