#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-09-03
@author: shell.xu
@license: BSD-3-clause
'''
from __future__ import absolute_import, division, print_function, unicode_literals
import os, time, socket, signal, logging
import utils, http
from datetime import datetime
from threading import Thread

class ThreadServer(object):

    def __init__(self, addr, handler, poolsize=10):
        self.addr, self.poolsize, self.go = addr, poolsize, True
        self.handler = handler

    def run(self):
        while self.go:
            try: self.handler(*self.listensock.accept())
            except KeyboardInterrupt: break
            except Exception: pass

    siglist = [signal.SIGTERM, signal.SIGINT]
    def signal_handler(self, signum, frame):
        if signum in self.siglist:
            self.go = False
            raise KeyboardInterrupt()

    def serve_forever(self):
        logging.info('WebServer started at %s:%d' % self.addr)
        self.listensock = socket.socket()
        self.listensock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listensock.bind(self.addr)
        self.listensock.listen(10000)

        try:
            for si in self.siglist: signal.signal(si, self.signal_handler)
            self.pool = [Thread(target=self.run)
                         for i in xrange(self.poolsize)]
            for th in self.pool: th.setDaemon(1)
            for th in self.pool: th.start()
            while True: time.sleep(1000)
            for th in self.pool: th.join()
        finally:
            logging.info('system exit')
            self.listensock.close()

def main():
    cfg = utils.getcfg([
        'serve.conf', '~/.webserver/serve.conf', '/etc/webserver/serve.conf'])
    utils.initlog(cfg.get('log', 'loglevel'), cfg.get('log', 'logfile'))
    addr = (cfg.get('main', 'addr'), cfg.getint('main', 'port'))

    engine = cfg.get('server', 'engine')
    if engine == 'apps':
        import apps
        ws = http.WebServer(apps.dis, cfg.get('log', 'access'))
    elif engine == 'wsgi':
        import app_webpy
        ws = http.WSGIServer(app_webpy.app.wsgifunc(), cfg.get('log', 'access'))
    else: raise Exception('invaild engine %s' % engine)

    server = cfg.get('server', 'server')
    if server == 'gevent':
        from gevent.server import StreamServer
        ws = StreamServer(addr, ws.handler)
    elif server == 'thread':
        ws = ThreadServer(addr, ws.handler)
    else: raise Exception('invaild server %s' % server)

    try: ws.serve_forever()
    except KeyboardInterrupt: pass

if __name__ == '__main__': main()
