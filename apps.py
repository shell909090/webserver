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
    logging.info('main path: {}'.format(req.path))
    logging.info('main url count: {}'.format(count))
    logging.info('main url match: {}'.format(req.url_match))
    logging.info('main url param: {}'.format(req.url_param))
    body = json.dumps({
        'page': 'main',
        'path': req.path,
        'count': count,
        'match': req.url_match,
        'param': req.url_param
    })
    req.session['count'] = count + 1
    res = httputil.Response.create(200, body=body)
    return res


def url_cached(req):
    res = httputil.Response.create(200, body='cached')
    res.cache = 0.1
    return res


def url_post(req):
    l = str(len(req.readbody()))
    logging.info('test post: {}'.format(l))
    return httputil.Response.create(200, body=l)


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
        return httputil.Response.create(200, body=on_body)

    def __call__(self, req):
        url_path, real_path = self.calc_path(req.path)
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
        return httputil.Response.create(200, body=body)

dis_chain = midware.Dispatch((
    ('/chain2/', url_main, {'param2': 2}),
))
dis = midware.Dispatch((
    ('/chain', dis_chain, {'param1': 1}),
    ('/test/', url_main, {'test param': 2}),
    ('/cached/', url_cached),
    ('/post/', url_post),
    ('/self/', url_path('.')),
    ('/', url_main, {'main param': 1})
))
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
        req = httputil.Request.create('/urlmatch')
        resp = self.ws.http_handler(req)
        self.assertEqual(resp.code, 200)
        self.assertEqual(
            json.loads(resp.body.decode('utf-8')),
            {
                'page': 'main',
                'path': 'urlmatch',
                'count': 0,
                'match': {},
                'param': {'main param': 1}
            })
        self.assertIn('Set-Cookie', resp.headers)

        req = httputil.Request.create('/urlmatch')
        req.headers['Cookie'] = resp.headers['Set-Cookie']
        resp = self.ws.http_handler(req)
        self.assertEqual(resp.code, 200)
        self.assertEqual(
            json.loads(resp.body.decode('utf-8')),
            {
                'page': 'main',
                'path': 'urlmatch',
                'count': 1,
                'match': {},
                'param': {'main param': 1}
            })

    def test_cached(self):
        for i in range(12):
            req = httputil.Request.create('/cached/{}'.format(int(i/3)))
            resp = self.ws.http_handler(req)
            self.assertEqual(resp.code, 200)
            self.assertEqual(resp.body, b'cached')

        time.sleep(0.2)
        req = httputil.Request.create('/cached/abc')
        resp = self.ws.http_handler(req)
        self.assertEqual(resp.code, 200)
        self.assertEqual(resp.body, b'cached')

    def test_test(self):
        req = httputil.Request.create('/test/testmatch')
        resp = self.ws.http_handler(req)
        self.assertEqual(resp.code, 200)
        self.assertEqual(
            json.loads(resp.body.decode('utf-8')),
            {
                'page': 'main',
                'path': 'testmatch',
                'count': 0,
                'match': {},
                'param': {'test param': 2}
            })

    def test_chain(self):
        req = httputil.Request.create('/chain/chain2/chainmatch')
        resp = self.ws.http_handler(req)
        self.assertEqual(resp.code, 200)
        self.assertEqual(
            json.loads(resp.body.decode('utf-8')),
            {
                'page': 'main',
                'path': 'chainmatch',
                'count': 0,
                'match': {},
                'param': {'param1': 1, 'param2': 2}
            })
        self.assertIn('Set-Cookie', resp.headers)

    def test_post(self):
        req = httputil.Request.create('/post/postmatch', body='postinfo')
        resp = self.ws.http_handler(req)
        self.assertEqual(resp.code, 200)
        self.assertEqual(resp.body, b'8')

    def test_path(self):
        req = httputil.Request.create('/self/')
        resp = self.ws.http_handler(req)
        self.assertEqual(resp.code, 200)
        self.assertIn(b'httputil.py', resp.body)
