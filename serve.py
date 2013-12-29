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

class WebServer(object):

    def __init__(self, dis, accesslog=None):
        self.dis = dis
        if accesslog: self.accessfile = open(accesslog, 'a')

    def http_handler(self, req):
        req.url = urlparse(req.uri)
        logging.info('%s %s' % (req.method, req.uri.split('?', 1)[0]))
        res = self.dis(req)
        if res is None:
            res = response_http(500, body='service internal error')
        logging.info('%s %s' % (res.code, res.phrase))
        res.sendto(req.stream)
        return res

    def record_access(self, req, res, addr):
        if not hasattr(self, 'accessfile'): return
        if res is not None:
            code = res.code
            length = res.get_header('Content-Length')
            if length is None and hasattr(res, 'length'):
                length = str(res.length)
            if length is None: length = '-'
        else: code, length = 500, '-'
        self.accessfile.write(
            '%s:%d - - [%s] "%s" %d %s "-" %s\n' % (
                addr[0], addr[1], datetime.now().isoformat(),
                req.get_startline(), code, length,
                req.get_header('User-Agent')))
        self.accessfile.flush()

    def handler(self, sock, addr):
        stream = sock.makefile()
        res = True
        try:
            while res:
                req = http.Request.recv_msg(stream)
                res = self.http_handler(req)
                self.record_access(req, res, addr)
        except (EOFError, socket.error): logging.info('network error')
        except Exception, err: logging.exception('unknown')
        finally: sock.close()

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
    from gevent.server import StreamServer
    ws = WebServer(apps.dis, cfg.get('log.access'))
    # ws = StreamServer(addr, ws.handler)
    ws = ThreadServer(addr, ws.handler)
    try: ws.serve_forever()
    except KeyboardInterrupt: pass

if __name__ == '__main__': main()
