#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-09-03
@author: shell.xu
'''
import os, time, socket, signal, logging
import utils, http
from datetime import datetime
from urlparse import urlparse
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
    utils.initlog(
        cfg.get('log.loglevel', 'WARNING'), cfg.get('log.logfile'))
    addr = (cfg.get('main.addr', ''), int(cfg.get('main.port', '8080')))

    import apps
    ws = http.WebServer(apps.dis, cfg.get('log.access'))

    # import app_webpy
    # ws = http.WSGIServer(app_webpy.app.wsgifunc(), cfg.get('log.access'))

    from gevent.server import StreamServer
    ws = StreamServer(addr, ws.handler)

    # ws = ThreadServer(addr, ws.handler)

    try: ws.serve_forever()
    except KeyboardInterrupt: pass

if __name__ == '__main__': main()
