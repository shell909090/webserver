#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-12-30
@author: shell.xu
@license: BSD-3-clause
'''
from __future__ import absolute_import, division,\
    print_function, unicode_literals
import os
import copy
import stat
import httputil
import urllib
import logging
import unittest
from os import path
import web
from template import Template


class Main(object):

    def GET(self, name):
        logging.info('main url count: {}', session.count)
        logging.info('main url match: {}', name)
        body = 'main page, count: {}, match: {}'.format(
            session.count, name)
        session.count += 1
        return body


class Post(object):

    def POST(self, name):
        l = str(len(web.data()))
        logging.info('test post: {}', l)
        return str(l)


class Path(object):
    tplstr = '''{%import os%}{%from os import path%}<html><head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
</head><body><table><thead><tr><td>file name</td><td>file mode</td>
<td>file size</td></tr></thead><tbody>{%for name in namelist:%}
{%stat_info = os.lstat(path.join(real_path, name))%}\
<tr><td><a href="{%=path.join(url_path, name).replace(os.sep, "/")%}">\
{%=name%}</a></td><td>{%=get_stat_str(stat_info.st_mode)%}</td><td>\
{%=stat_info.st_size%}</td></tr>{%end%}
</tbody></table></body>'''
    tpl = Template(template=tplstr)
    index_set = ['index.html', ]

    def file_app(self, filepath):
        with open(filepath, 'rb') as fi:
            for b in httputil.file_source(fi):
                yield b

    def get_stat_str(self, mode):
        stat_map = [
            (stat.S_ISDIR, 'd'),
            (stat.S_ISREG, 'f'),
            (stat.S_ISLNK, 'l'),
            (stat.S_ISSOCK, 's')]
        return ''.join([s for f, s in stat_map if f(mode)])

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
            'namelist': namelist, 'get_stat_str': self.get_stat_str,
            'real_path': real_path, 'url_path': url_path})


def StaticPath(basedir):
    p = copy.copy(Path)
    p.basedir = path.abspath(path.realpath(path.expanduser(basedir)))
    return p

app = web.application((
    '/post/(.*)', Post,
    '/self/(.*)', StaticPath('.'),
    '/(.*)', Main))

session = web.session.Session(
    app, web.session.DiskStore('sessions'), initializer={'count': 0})


class TestAppWebpy(unittest.TestCase):

    def test_main(self):
        resp = app.request('/urlmatch')
        self.assertEqual(resp.status, '200 OK')
        self.assertEqual(
            resp.data,
            b'main page, count: 0, match: urlmatch')
        self.assertIn('Set-Cookie', resp.headers)

    def test_post(self):
        resp = app.request('/post/postmatch', method='POST', data='postinfo')
        self.assertEqual(resp.status, '200 OK')
        self.assertEqual(resp.data, '8')

    def test_path(self):
        resp = app.request('/self/')
        self.assertEqual(resp.status, '200 OK')
        self.assertIn('httputil.py', resp.data)
