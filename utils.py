#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-12-30
@author: shell.xu
'''
import getopt, logging

LOGFMT = '%(asctime)s.%(msecs)03d[%(levelname)s](%(module)s:%(lineno)d): %(message)s'
def initlog(lv, logfile=None, stream=None, longdate=False):
    if isinstance(lv, basestring): lv = getattr(logging, lv)
    kw = {'format': LOGFMT, 'datefmt': '%H:%M:%S', 'level': lv}
    if logfile: kw['filename'] = logfile
    if stream: kw['stream'] = stream
    if longdate: kw['datefmt'] = '%Y-%m-%d %H:%M:%S'
    logging.basicConfig(**kw)

def getcfg(cfgpathes):
    from ConfigParser import SafeConfigParser
    cp = SafeConfigParser()
    cp.read(cfgpathes)
    rslt = {}
    for sec in cp.sections():
        for k, v in cp.items(sec): rslt[sec + '.' + k] = v
    return rslt
