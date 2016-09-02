#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-09-04
@author: shell.xu
@license: BSD-3-clause
'''
from __future__ import absolute_import, division,\
    print_function, unicode_literals
import os
import stat
import time
import json
import logging
import unittest
from os import path
try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote
import httputil
import midware
from template import Template


def url_main(req):
    count = req.session.get('count', 0)
    logging.info('main url count: {}'.format(count))
    logging.info('main url match: {}'.format(req.url_match))
    logging.info('main url param: {}'.format(req.url_param))
    body = 'main page, count: {}, match: {}, param: {}'.format(
        count, json.dumps(req.url_match), json.dumps(req.url_param))
    req.session['count'] = count + 1
    res = httputil.response_http(200, body=body)
    return res


def url_cached(req):
    res = httputil.response_http(200, body='cached')
    res.cache = 0.5
    return res


def url_post(req):
    l = str(len(req.readbody()))
    logging.info('test post: {}'.format(l))
    return httputil.response_http(200, body=l)


class url_path(object):
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

    def __init__(self, basedir):
        self.basedir = path.abspath(path.realpath(path.expanduser(basedir)))

    def calc_path(self, filepath):
        url_path = unquote(filepath)
        real_path = path.join(self.basedir, url_path.lstrip('/'))
        real_path = path.abspath(path.realpath(real_path))
        if not real_path.startswith(self.basedir):
            raise httputil.HttpException(403)
        return url_path, real_path

    def get_stat_str(self, mode):
        stat_map = [
            (stat.S_ISDIR, 'd'),
            (stat.S_ISREG, 'f'),
            (stat.S_ISLNK, 'l'),
            (stat.S_ISSOCK, 's')]
        return ''.join([s for f, s in stat_map if f(mode)])

    def file_app(self, req, filename):
        def on_body():
            with open(filename, 'rb') as fi:
                for d in httputil.file_source(fi):
                    yield d
        return httputil.response_http(200, body=on_body)

    def __call__(self, req):
        url_path, real_path = self.calc_path(req.url_match[0])
        if not path.isdir(real_path):
            return self.file_app(req, real_path)
        for i in self.index_set:
            test_path = path.join(real_path, i)
            if os.access(test_path, os.R_OK):
                return self.file_app(req, test_path)
        namelist = os.listdir(real_path)
        namelist.sort()
        body = self.tpl.render({
            'namelist': namelist, 'get_stat_str': self.get_stat_str,
            'real_path': real_path, 'url_path': url_path})
        return httputil.response_http(200, body=body)

dis = midware.Dispatch((
    ('/test/(.*)', url_main, 'test param'),
    ('/cached/(.*)', url_cached),
    ('/post/(.*)', url_post),
    ('/self/(.*)', url_path('.')),
    ('/(.*)', url_main, 'main param')))
dis = midware.MemoryCache(2)(dis)
dis = midware.MemorySession(600)(dis)


class TestApp(unittest.TestCase):
    template = u'''<html><head><title>{%=r%}</title></head>
<body><table><tr><td>col1</td><td>col2</td></tr>
{%for i in objs:%}<tr><td>{%=i[0]%}</td><td>{%=i[1]%}</td></tr>
{%end%}</table></body></html>'''
    result = u'''<html><head><title>test</title></head>
<body><table><tr><td>col1</td><td>col2</td></tr>
<tr><td>1</td><td>2</td></tr>
<tr><td>3</td><td>4</td></tr>
</table></body></html>'''

    def setUp(self):
        self.ws = httputil.WebServer(dis)

    def test_main(self):
        req = httputil.request_http('/urlmatch')
        resp = self.ws.http_handler(req)
        self.assertEqual(resp.code, 200)
        self.assertEqual(
            resp.body,
            b'main page, count: 0, match: ["urlmatch"], param: ["main param"]')
        self.assertIn('Set-Cookie', resp.headers)

        req.headers['Cookie'] = resp.headers['Set-Cookie']
        resp = self.ws.http_handler(req)
        self.assertEqual(resp.code, 200)
        self.assertEqual(
            resp.body,
            b'main page, count: 1, match: ["urlmatch"], param: ["main param"]')

    def test_cached(self):
        for i in range(12):
            req = httputil.request_http('/cached/{}'.format(int(i/3)))
            resp = self.ws.http_handler(req)
            self.assertEqual(resp.code, 200)
            self.assertEqual(resp.body, b'cached')

        time.sleep(1)
        req = httputil.request_http('/cached/abc')
        resp = self.ws.http_handler(req)
        self.assertEqual(resp.code, 200)
        self.assertEqual(resp.body, b'cached')

    def test_test(self):
        req = httputil.request_http('/test/testmatch')
        resp = self.ws.http_handler(req)
        self.assertEqual(resp.code, 200)
        self.assertEqual(
            resp.body,
            b'main page, count: 0, match: ["testmatch"], param: ["test param"]'
        )

    def test_post(self):
        req = httputil.request_http('/post/postmatch', body='postinfo')
        resp = self.ws.http_handler(req)
        self.assertEqual(resp.code, 200)
        self.assertEqual(resp.body, b'8')

    def test_path(self):
        req = httputil.request_http('/self/')
        resp = self.ws.http_handler(req)
        self.assertEqual(resp.code, 200)
        self.assertIn(b'httputil.py', resp.body)
