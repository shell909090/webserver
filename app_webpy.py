#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-12-30
@author: shell.xu
'''
import os, copy, stat, http, urllib
from os import path
import web
from template import Template

class Test(object):
    def GET(self, name):
        print 'test params:', name
        return 'test'

class Post(object):
    def POST(self, name):
        l = len(web.data())
        print 'test post:', l
        return str(l)

class Main(object):
    def GET(self, name):
        print 'main url count: %d' % session.count
        print 'main url match:', name
        session.count += 1

def get_stat_str(mode):
    stat_list = []
    if stat.S_ISDIR(mode): stat_list.append("d")
    if stat.S_ISREG(mode): stat_list.append("f")
    if stat.S_ISLNK(mode): stat_list.append("l")
    if stat.S_ISSOCK(mode): stat_list.append("s")
    return ''.join(stat_list)

class Path(object):
    tpl = Template(template = '{%import os%}{%from os import path%}<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"/></head><body><table><thead><tr><td>file name</td><td>file mode</td><td>file size</td></tr></thead><tbody>{%for name in namelist:%}{%name=name.decode("utf-8")%}{%stat_info = os.lstat(path.join(real_path, name))%}<tr><td><a href="{%=path.join(url_path, name).replace(os.sep, "/")%}">{%=name%}</a></td><td>{%=get_stat_str(stat_info.st_mode)%}</td><td>{%=stat_info.st_size%}</td></tr>{%end%}</tbody></table></body>')
    index_set = ['index.html',]

    def file_app(self, filepath):
        with open(filepath, 'rb') as fi:
            for b in http.file_source(fi): yield b

    def GET(self, filepath):
        url_path = urllib.unquote(filepath)
        real_path = path.join(self.basedir, url_path.lstrip('/'))
        real_path = path.abspath(path.realpath(real_path))
        if not real_path.startswith(self.basedir):
            raise web.forbidden()
        if not path.isdir(real_path):
            return self.file_app(real_path)
        for i in self.index_set:
            test_path = path.join(real_path, i)
            if os.access(test_path, os.R_OK):
                return self.file_app(real_path)
        namelist = os.listdir(real_path)
        namelist.sort()
        return self.tpl.render({
            'namelist': namelist, 'get_stat_str': get_stat_str,
            'real_path': real_path, 'url_path': url_path})

def StaticPath(basedir):
    p = copy.copy(Path)
    p.basedir = path.abspath(path.realpath(path.expanduser(basedir)))
    return p

app = web.application((
    '/test/(.*)', Test,
    '/test1/(.*)', Test,
    '/self/(.*)', StaticPath('.'),
    '/post/(.*)', Post,
    '/(.*)', Main))

session = web.session.Session(
    app, web.session.DiskStore('sessions'), initializer={'count': 0})
