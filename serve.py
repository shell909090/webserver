#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-09-03
@author: shell.xu
'''
import socket, threading
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

    def __init__(self, addr, dis, poolsize=10000):
        self.addr = addr
        self.pool = pool.Pool(poolsize)
        self.dis = dis
        self.init()

    def init(self):
        initlog('INFO', None)
        logger.info('WebServer started at %s' % str(self.addr))

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

    def serve_forever(self):
        listensock = socket.socket()
        listensock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listensock.bind(self.addr)
        listensock.listen(5)
        while True:
            sock, addr = listensock.accept()
            self.pool.spawn(self.sockloop, sock, addr)

def main():
    import apps
    ws = WebServer(('', 8080), apps.dis)
    try:
        try: ws.serve_forever()
        except KeyboardInterrupt: pass
    finally: ws.final()

if __name__ == '__main__': main()
