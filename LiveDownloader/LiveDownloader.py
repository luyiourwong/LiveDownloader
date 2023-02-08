
from streamlink import Streamlink
from streamlink.exceptions import PluginError
from streamlink.exceptions import StreamError
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.stream.hls import HLSStream

import time
import os
from os import system
import sys
import traceback

#value
DEFAULT_TITLE = ""
DEFAULT_DOWNLOAD_FOLDER = "ArchVD"
DEFAULT_WAITING_TIME = 10
STREAM_WAITING_TIME = 0
DEFAULT_TIMEOUT = 60
DEFAULT_TIMEOUT_SEGMENT = 10
DEFAULT_THREAD = 1
DEFAULT_HLS_LIVEEDGE = 3
DEFAULT_LOG_COUNT = 16000
DEFAULT_LOG_FILE = "log.txt"
DEFAULT_COOKIE_SETKEY = "http-cookies"
DEFAULT_COOKIE_FILE = "**website**.com_cookies.txt" # **website** 公開版已移除網址
DEFAULT_YOUTUBE_STARTWITH = ".**website**.com" # **website** 公開版已移除網址
DEFAULT_COOKIE_KEYAT = 5
DEFAULT_COOKIE_VALUEAT = 6
DEFAULT_STREAM_URL = "**URL**" # **URL** 公開版已移除網址

class MainLivedl():
    def __init__(self):
        self.setup()
        
    def setup(self):
        info('setup start')
        self.outputpath = DEFAULT_DOWNLOAD_FOLDER
        info('set outputpath to ' + str(self.outputpath))
        
        self.session = Streamlink()

        #set default option
        dicset = {"stream-timeout":DEFAULT_TIMEOUT,
                  "stream-segment-timeout":DEFAULT_TIMEOUT_SEGMENT,
                  "stream-segment-threads":DEFAULT_THREAD,
                  "hls-live-edge":DEFAULT_HLS_LIVEEDGE}
        for key,value in dicset.items():
            self.session.set_option(key, value)
            info('set ' + str(key) + ' to ' + str(self.session.get_option(key)))
            
        #set cookies
        self.loadCookie()
        
        info('setup finish')
        
    def gettimedir(self, localtime):
        timey = time.strftime('%Y', localtime)
        timem = time.strftime('%m', localtime)
        timed = time.strftime('%d', localtime)
        td = '00'
        if int(timed) >= 20:
            td = '20'
        elif int(timed) >= 10:
            td = '10'
        return self.outputpath + os.path.sep + (str(timey) + '_' + str(timem) + '_' + str(td)) + os.path.sep
        
    def loadCookie(self):
        try:
            filename = DEFAULT_COOKIE_FILE
            with open(filename, "r") as in_file:
                lines = in_file.readlines()
        except IOError:
            warning('IO error on loading cookie, skip: ' + str(filename))
            return
        diccookie = {}
        info('loading cookie file successful: ' + str(filename))
        for line in lines:
            if line.startswith(DEFAULT_YOUTUBE_STARTWITH):
                l = line.split()
                diccookie[l[DEFAULT_COOKIE_KEYAT]] = l[DEFAULT_COOKIE_VALUEAT]
        for key,value in diccookie.items():
            self.session.set_option(DEFAULT_COOKIE_SETKEY, key + "=" + value)
        info('set ' + DEFAULT_COOKIE_SETKEY + ' to ' + str(self.session.get_option(DEFAULT_COOKIE_SETKEY)))
        
    def run(self, url):
        #setup
        info('start checking stream')
        self.waittime = DEFAULT_WAITING_TIME
        self.firstdownload = True
        self.isLive = False
        
        #set url
        if url == '':
            self.onetimedownload = False
            url = DEFAULT_STREAM_URL
            info('no requirement url, set to default')
        else:
            if url.endswith('live'):
                self.onetimedownload = False
                info('has requirement live url')
            else:
                self.onetimedownload = True
                info('has requirement url, this recorder will only run once')
        system("title " + url)
        
        #run
        while 1==1:
            self.startDownload(url)
            info('waiting ' + str(self.waittime) + ' second')
            if self.waittime >= 1:
                time.sleep(self.waittime)
    
    def startDownload(self, url):
        #setup
        timestart = time.time()
        localtime = time.localtime()
        timenow = time.strftime('%Y-%m-%d %H-%M-%S', localtime)
        
        #check stream
        info('[' + timenow + '] check streams: ' + url)
        try:
            streams = self.session.streams(url)
        except PluginError:
            self.waittime = DEFAULT_WAITING_TIME
            self.firstdownload = True
            warning('streams offline')
            return
        except:
            self.waittime = DEFAULT_WAITING_TIME
            self.firstdownload = True
            warning('error, maybe unsupported site')
            return
        
        #check quality
        info('had stream, check quality')
        try:
            stream = streams["best"]
        except KeyError:
            self.waittime = DEFAULT_WAITING_TIME
            self.firstdownload = True
            warning('no best quality, maybe the stream has not live yet')
            return
        
        #check is live or not
        if isinstance(stream, HLSStream):
            self.isLive = True
            info('this stream is a live')
        elif isinstance(stream, MuxedStream):
            self.isLive = False
            info('this stream is NOT a live')
        else:
            self.isLive = False
            info('this stream is unknown type')
            
        #one time download closed
        self.checkOneTimeDownloaded(self.isLive)
        
        #open stream
        self.waittime = STREAM_WAITING_TIME
        info('choose best, open')
        try:
            #setup file
            filename = str(timenow) + ".ts"
            dirpath = self.gettimedir(localtime)
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)
            filepath = dirpath + filename
            
            #open file
            with open(filepath, "ab") as out_file:
                fd = stream.open()
                logstr = 'opened, start download: ' + str(filepath)
                info(logstr)
                outlog(logstr)
                
                #keep writing file
                count = 0
                while 1==1:
                    #read data from stream
                    if not fd:
                        logstr = 'file buffer close, close stream'
                        info(logstr)
                        outlog(logstr)
                        fd.close()
                        out_file.close()
                        break
                    
                    try:
                        data = fd.read(1024)
                    except IOError:
                        logstr = 'read data IO error, maybe stream offline'
                        error(logstr)
                        outlog(logstr)
                        fd.close()
                        out_file.close()
                        break
                    except:
                        logstr = 'read data unknown error'
                        error(logstr)
                        outlog(logstr)
                        fd.close()
                        out_file.close()
                        break
                    
                    #check if no more data
                    if not data:
                        logstr = 'no data, close stream'
                        info(logstr)
                        outlog(logstr)
                        fd.close()
                        out_file.close()
                        break
                    
                    #write data to file
                    out_file.write(data)
                    
                    #log
                    count += 1
                    if count >= DEFAULT_LOG_COUNT:
                        timedown = time.time()
                        ss = timedown - timestart
                        m, s = divmod(ss, 60)
                        h, m = divmod(m, 60)
                        k = os.path.getsize(filepath)
                        mb = k/1000000
                        logstr = 'download ' + str(round(mb)) + ' MB during ' + ('%d:%02d:%02d' % (h, m, s))
                        info(logstr)
                        outlog(logstr)
                        count = 0
                        
        except StreamError:
            logstr = 'streams error, maybe offline, close stream'
            warning(logstr)
            outlog(logstr)
            fd.close()
        except IOError:
            logstr = 'IO error, close stream, ' + traceback.format_exc()
            error(logstr)
            outlog(logstr)
            fd.close()
        except:
            logstr = 'can not download, close stream'
            error(logstr)
            outlog(logstr)
            fd.close()
            
    def checkOneTimeDownloaded(self, onetimedownloaded):
        if self.onetimedownload == True and onetimedownloaded == False:
            sys.exit('one time download finish')

def debug(msg):
    print('[debug] ' + msg)

def info(msg):
    print('[info] ' + msg)

def warning(msg):
    print('[warning] ' + msg)

def error(msg):
    print('[error] ' + msg)
    
def outlog(msg):
    timenow = time.strftime('%Y-%m-%d %H-%M-%S', time.localtime())
    try:
        filename = DEFAULT_LOG_FILE
        with open(filename, "a") as out_file:
            out_file.write('[' + timenow + ']' + msg + '\n')
    except IOError:
        error('IO error on log !!!')
        return

if __name__ == "__main__":
    mainLive = MainLivedl()
    url = ''
    if len(sys.argv) > 1:
        url = sys.argv[1]
    mainLive.run(url)