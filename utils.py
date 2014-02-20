#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-12-30
@author: shell.xu
'''
import logging

LOGFMT = '%(asctime)s.%(msecs)03d[%(levelname)s](%(module)s:%(lineno)d): %(message)s'
def initlog(lv, logfile=None, stream=None, longdate=False):
    if logfile.startswith('syslog:'):
        import logging.handlers
        handler = logging.handlers.SysLogHandler(logfile[7:])
    elif logfile: handler = logging.FileHandler(logfile)
    elif stream: handler = logging.StreamHandler(stream)
    else: handler = logging.StreamHandler(sys.stderr)

    datefmt = '%H:%M:%S'
    if longdate: datefmt = '%Y-%m-%d %H:%M:%S'
    handler.setFormatter(logging.Formatter(LOGFMT, datefmt))

    logger = logging.getLogger()
    if isinstance(lv, basestring): lv = getattr(logging, lv)
    logger.setLevel(lv)
    logger.addHandler(handler)

def getcfg(cfgpathes):
    from ConfigParser import SafeConfigParser
    cp = SafeConfigParser()
    cp.read(cfgpathes)
    return cp
