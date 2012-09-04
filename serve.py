#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-09-03
@author: shell.xu
'''
import os, stat, urllib, logging
import midware
from http import *
from template import Template
from os import path
from urlparse import urlparse
# from contextlib import contextmanager

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

def url_test(req):
    print 'test params:', req.url_param
    return response_http(200, 'ok', body='test')

def url_main(req):
    count = req.session.get('count', 0)
    print 'main url count: %d' % count
    print 'main url match:', req.url_match
    req.session['count'] = count + 1
    return response_http(200, 'ok', cache=100, body='main')

def url_path(basedir):
    tpl = Template(template = '{%import os%}{%from os import path%}<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"/></head><body><table><thead><tr><td>file name</td><td>file mode</td><td>file size</td></tr></thead><tbody>{%for name in namelist:%}{%name=name.decode("utf-8")%}{%stat_info = os.lstat(path.join(real_path, name))%}<tr><td><a href="{%=path.join(url_path, name).replace(os.sep, "/")%}">{%=name%}</a></td><td>{%=get_stat_str(stat_info.st_mode)%}</td><td>{%=stat_info.st_size%}</td></tr>{%end%}</tbody></table></body>')
    index_set = ['index.html',]
    def calc_path(filepath, basedir):
        url_path = urllib.unquote(filepath)
        real_path = path.join(basedir, url_path.lstrip('/'))
        real_path = path.abspath(path.realpath(real_path))
        if not real_path.startswith(basedir): raise basehttp.HttpException(403)
        return url_path, real_path
    basedir = path.abspath(path.realpath(path.expanduser(basedir)))

    def get_stat_str(mode):
        stat_list = []
        if stat.S_ISDIR(mode): stat_list.append("d")
        if stat.S_ISREG(mode): stat_list.append("f")
        if stat.S_ISLNK(mode): stat_list.append("l")
        if stat.S_ISSOCK(mode): stat_list.append("s")
        return ''.join(stat_list)

    def file_app(req, filename):
        def on_body():
            with open(filename, 'rb') as fi:
                while True:
                    d = fi.read(4096)
                    if len(d) == 0: break
                    yield d
        return response_http(200, body=on_body)

    def inner(req):
        url_path, real_path = calc_path(req.url_match[0], basedir)
        if path.isdir(real_path):
            for i in index_set:
                test_path = path.join(real_path, i)
                if os.access(test_path, os.R_OK):
                    return file_app(req, test_path)
            namelist = os.listdir(real_path)
            namelist.sort()
            return response_http(200, body=tpl.render({
                    'namelist': namelist, 'get_stat_str': get_stat_str,
                    'real_path': real_path, 'url_path': url_path}))
        else: return file_app(req, real_path)
    return inner

def main():
    dis = midware.Dispatch((
        ('/test/(.*)', url_test),
        ('/test1/(.*)', url_test, 'new instance'),
        ('/self/(.*)', url_path('.')),
        ('/(.*)', url_main)))
    dis = midware.MemoryCache(10)(dis)
    dis = midware.MemorySession(600)(dis)

    ws = WebServer(('', 8080), dis)
    try:
        try: ws.serve_forever()
        except KeyboardInterrupt: pass
    finally: ws.final()

if __name__ == '__main__': main()
