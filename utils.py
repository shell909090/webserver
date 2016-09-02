#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-12-30
@author: shell.xu
@license: BSD-3-clause
'''
from __future__ import absolute_import, division,\
    print_function, unicode_literals
import sys
import logging

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

# import threading
# class SocketPool(object):

#     def __init__(self, max_addr=-1):
#         self._lock = threading.RLock()
#         self.buf, self.max_addr = {}, max_addr

#     def setmax(self, max_addr=-1):
#         self.max_addr = max_addr

#     def __call__(self, addr):
#         host = addr[0]
#         addr = (socket.gethostbyname(host), addr[1])
#         stream = None
#         with self._lock:
#             if self.buf.get(addr):
#                 stream = self.buf[addr].pop(0)
#                 logging.debug(
#                     'acquire conn %s:%d size %d',
#                     host, addr[1], len(self.buf[addr]))
#         if stream is None:
#             logging.debug('create new conn: %s:%d', host, addr[1])
#             stream = connect_addr(addr)
#             stream._close = stream.close
#             stream.close = lambda: self.release(stream)
#         return stream

#     def release(self, stream):
#         try:
#             addr = stream._sock.getpeername()
#         except socket.error:
#             logging.debug('free conn.')
#             return
#         with self._lock:
#             self.buf.setdefault(addr, [])
#             if self.max_addr < 0 or len(self.buf[addr]) < self.max_addr:
#                 self.buf[addr].append(stream)
#                 logging.debug(
#                     'release conn %s:%d back size %d',
#                     addr[0], addr[1], len(self.buf[addr]))
#                 return
#         logging.debug('free conn %s:%d.', addr[0], addr[1])
#         stream._close()

# connector = SocketPool()
