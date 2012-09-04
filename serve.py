#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-09-03
@author: shell.xu
'''
import os, time, socket, signal, threading
from urlparse import urlparse
from http import *

def initlog(lv, logfile=None):
    rootlog = logging.getLogger()
    if logfile: handler = logging.FileHandler(logfile)
    else: handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            '%(asctime)s,%(msecs)03d %(name)s[%(levelname)s]: %(message)s',
            '%H:%M:%S'))
    rootlog.addHandler(handler)
    rootlog.setLevel(lv)

logger = logging.getLogger('server')

class WebServer(object):

    def __init__(self, addr, dis, poolsize=100):
        self.addr, self.poolsize = addr, poolsize
        self.dis = dis
        self.init()

    def init(self):
        initlog('ERROR', None)
        logger.info('WebServer started at %s' % str(self.addr))

        self.listensock = socket.socket()
        self.listensock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listensock.bind(self.addr)
        self.listensock.listen(10000)

    def handler(self, req):
        req.url = urlparse(req.uri)
        logger.info('%s %s' % (req.method, req.uri.split('?', 1)[0]))
        res = self.dis(req)
        if res is None:
            res = response_http(500, body='service internal error')
        logger.info('%s %s' % (res.code, res.phrase))
        res.sendto(req.stream)
        return res

    def sockloop(self, sock, addr):
        stream = sock.makefile()
        try:
            while self.handler(recv_msg(stream, HttpRequest)): pass
        except (EOFError, socket.error): logger.info('network error')
        except Exception, err: logger.exception('unknown')
        sock.close()

    def final(self): logger.info('system exit')

    def run(self):
        sock, addr = self.listensock.accept()
        self.sockloop(sock, addr)

    siglist = [signal.SIGTERM, signal.SIGINT]
    def signal(self, signum, frame):
        if signum in self.siglist:
            for th in self.pool: th.go = False
            raise KeyboardInterrupt()

    def serve_forever(self):
        class ServiceThread(threading.Thread):
            def __init__(self, ws):
                super(ServiceThread, self).__init__()
                self.ws, self.go, self.daemon = ws, True, True
            def run(self):
                while self.go:
                    try: self.ws.run()
                    except KeyboardInterrupt: break
                    except Exception: pass
        self.pool = [ServiceThread(self) for i in xrange(self.poolsize)]
        for si in self.siglist: signal.signal(si, self.signal)
        for th in self.pool: th.start()
        while True: time.sleep(1000)
        # for th in self.pool: th.join()

    def autofork(self, num=4):
        for i in xrange(num-1):
            if os.fork() == 0: break

def main():
    ws = WebServer(('', 8080), __import__('apps').dis)
    ws.autofork()
    try:
        try: ws.serve_forever()
        except KeyboardInterrupt: pass
    finally: ws.final()

if __name__ == '__main__': main()
