#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-09-03
@author: shell.xu
'''
import logging
from http import *
# from os import path
# from urlparse import urlparse
# from contextlib import contextmanager
from gevent import pool, socket, dns

__all__ = []

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

def handler(req, stream):
    print req.method, req.uri, req.version
    response_http(stream, 200, body='ok')

class WebServer(object):

    def __init__(self, addr, handler, poolsize=10000):
        self.addr = addr
        self.pool = pool.Pool(poolsize)
        self.handler = handler
        self.init()

    def init(self): initlog('INFO', None)

    def sockloop(self, sock, addr):
        stream = sock.makefile()
        try:
            while self.handler(recv_msg(stream, HttpRequest), stream): pass
        except (EOFError, socket.error): logger.info('network error')
        except Exception, err: logger.exception('unknown')
        sock.close()

    def final(self): logger.info('system exit')

    def serve_forever(self):
        listensock = socket.socket()
        listensock.bind(self.addr)
        listensock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listensock.listen(5)
        while True:
            sock, addr = listensock.accept()
            self.pool.spawn(self.sockloop, sock, addr)

def main():
    ws = WebServer(('', 8080), handler)
    try:
        try: ws.serve_forever()
        except KeyboardInterrupt: pass
    finally: ws.final()

if __name__ == '__main__': main()
