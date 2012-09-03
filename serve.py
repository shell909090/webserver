#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-09-03
@author: shell.xu
'''
import logging
import app
from http import *
# from os import path
from urlparse import urlparse
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

class WebServer(object):

    def __init__(self, addr, dis, poolsize=10000):
        self.addr = addr
        self.pool = pool.Pool(poolsize)
        self.dis = dis
        self.init()

    def init(self):
        initlog('INFO', None)
        logger.info('WebServer started at %s' % str(self.addr))

    def handler(self, req, stream):
        req.url = urlparse(req.uri)
        logger.info('%s %s' % (req.method, req.uri.split('?', 1)[0]))
        res = self.dis(req, stream)
        logger.info('%s %s' % (res.code, res.phrase))
        res.sendto(stream)
        if callable(res.body):
            for d in res.body(): stream.write(d)
        else: stream.write(res.body)
        return res

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
        listensock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listensock.bind(self.addr)
        listensock.listen(5)
        while True:
            sock, addr = listensock.accept()
            self.pool.spawn(self.sockloop, sock, addr)

def url_test(req, stream):
    print 'test params:', req.url_param
    return response_http(200, 'ok', body='test')

def url_main(req, stream):
    count = req.session.get('count', 0)
    print 'main url count: %d' % count
    print 'main url match:', req.url_match
    req.session['count'] = count + 1
    return response_http(200, 'ok', cache=100, body='main')

def main():
    dis = app.Dispatch((
        ('/test/(.*)', url_test),
        ('/test1/(.*)', url_test, 'new instance'),
        ('/(.*)', url_main)))
    dis = app.MemoryCache(10)(dis)
    dis = app.MemorySession(600)(dis)

    ws = WebServer(('', 8080), dis)
    try:
        try: ws.serve_forever()
        except KeyboardInterrupt: pass
    finally: ws.final()

if __name__ == '__main__': main()
