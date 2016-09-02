#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-09-03
@author: shell.xu
@license: BSD-3-clause
'''
from __future__ import absolute_import, division, \
    print_function, unicode_literals
import sys
import logging
import httputil

if sys.version_info.major == 3:
    basestring = str


LOGFMT = '%(asctime)s.%(msecs)03d[%(levelname)s]\
(%(module)s:%(lineno)d): %(message)s'


def initlog(lv, logfile=None, stream=None, longdate=False):
    if logfile and logfile.startswith('syslog:'):
        from logging import handlers
        handler = handlers.SysLogHandler(logfile[7:])
    elif logfile:
        handler = logging.FileHandler(logfile)
    elif stream:
        handler = logging.StreamHandler(stream)
    else:
        handler = logging.StreamHandler(sys.stderr)

    datefmt = '%H:%M:%S'
    if longdate:
        datefmt = '%Y-%m-%d %H:%M:%S'
    handler.setFormatter(logging.Formatter(LOGFMT, datefmt))

    logger = logging.getLogger()
    if isinstance(lv, basestring):
        lv = getattr(logging, lv)

    logger.setLevel(lv)
    logger.addHandler(handler)


def getcfg(cfgpathes):
    try:
        from ConfigParser import SafeConfigParser
    except ImportError:
        from configparser import SafeConfigParser
    cp = SafeConfigParser()
    cp.read(cfgpathes)
    return cp


def main():
    cfg = getcfg([
        'serve.conf', '~/.webserver/serve.conf', '/etc/webserver/serve.conf'])
    initlog(cfg.get('log', 'loglevel'), cfg.get('log', 'logfile'))
    addr = (cfg.get('main', 'addr'), cfg.getint('main', 'port'))

    engine = cfg.get('server', 'engine')
    if engine == 'apps':
        import apps
        ws = httputil.WebServer(apps.dis, cfg.get('log', 'access'))
    elif engine == 'wsgi':
        import app_webpy
        ws = httputil.WSGIServer(app_webpy.app.wsgifunc(),
                                 cfg.get('log', 'access'))
    else:
        raise Exception('invaild engine %s' % engine)

    server = cfg.get('server', 'server')
    if server == 'gevent':
        from gevent.server import StreamServer
        ws = StreamServer(addr, ws.handler)
    elif server == 'thread':
        ws = httputil.ThreadServer(addr, ws.handler)
    else:
        raise Exception('invaild server %s' % server)

    try:
        ws.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
