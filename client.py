#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-10-17
@author: shell.xu
@license: BSD-3-clause
'''
from __future__ import absolute_import, division,\
    print_function, unicode_literals
import sys
import json
import time
import httputil
import unittest
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
from contextlib import closing

if sys.version_info.major == 3:
    unicode = str
else:
    bytes = str


def download(url):
    with closing(httputil.download(url)) as resp:
        return resp.readbody()


def prepare_apps():
    import apps
    ws = httputil.WebServer(apps.dis, StringIO())
    ts = httputil.ThreadServer(('', 18080), ws.handler, poolsize=1)
    ts.start()
    time.sleep(0.1)


prepare_apps()


class TestClientApp(unittest.TestCase):
    target = 'http://localhost:18080'

    def test_main(self):
        body = download(self.target + '/urlmatch')
        self.assertEqual(
            json.loads(body.decode('utf-8')),
            {
                'page': 'main',
                'path': 'urlmatch',
                'count': 0,
                'match': {},
                'param': {'main param': 1}
            })

    def test_getfile(self):
        with httputil.download(self.target + '/urlmatch').makefile() as f:
            body = f.read()
        self.assertEqual(
            json.loads(body.decode('utf-8')),
            {
                'page': 'main',
                'path': 'urlmatch',
                'count': 0,
                'match': {},
                'param': {'main param': 1}
            })

    def test_cached(self):
        for i in range(12):
            body = download(
                self.target + '/cached/{}'.format(int(i/3)))
            self.assertEqual(body, b'cached')

        time.sleep(0.2)
        body = download(self.target + '/cached/abc')
        self.assertEqual(body, b'cached')

    def test_test(self):
        body = download(self.target + '/test/testmatch')
        self.assertEqual(
            json.loads(body.decode('utf-8')),
            {
                'page': 'main',
                'path': 'testmatch',
                'count': 0,
                'match': {},
                'param': {'test param': 2}
            })

    def test_post(self):
        with open('httputil.py', 'rb') as fi:
            data = fi.read()
        with httputil.download(
                self.target + '/post/postmatch',
                data=data
        ).makefile() as f:
            body = f.read()
        self.assertEqual(body, str(len(data)).encode(httputil.ENCODING))

    def test_post_file(self):
        with open('httputil.py', 'rb') as fi:
            with httputil.download(self.target + '/post/postmatch',
                                   data=fi).makefile() as f:
                body = f.read()
        with open('httputil.py', 'rb') as fi:
            data = fi.read()
        self.assertEqual(body, str(len(data)).encode(httputil.ENCODING))

    def test_upload(self):
        with open('httputil.py', 'rb') as fi:
            data = fi.read()
        with httputil.upload(self.target + '/post/postmatch') as f:
            f.write(data)
        with closing(f.get_response()) as resp:
            self.assertEqual(
                resp.readbody(),
                str(len(data)).encode(httputil.ENCODING))

    def test_path(self):
        body = download(self.target + '/self/')
        self.assertIn(b'httputil.py', body)


def prepare_webpy():
    try:
        import app_webpy
    except ImportError:
        global TestClientWebpy
        TestClientWebpy = None
        return
    ws = httputil.WSGIServer(app_webpy.app.wsgifunc())
    ts = httputil.ThreadServer(('', 18081), ws.handler, poolsize=1)
    ts.start()
    time.sleep(0.1)


class TestClientWebpy(unittest.TestCase):
    target = 'http://localhost:18081'

    def test_main(self):
        body = download(self.target + '/urlmatch')
        self.assertEqual(
            body,
            b'main page, count: 0, match: urlmatch')

    def test_post(self):
        with open('httputil.py', 'rb') as fi:
            data = fi.read()
        with httputil.download(
                self.target + '/post/postmatch',
                data=data
        ).makefile() as f:
            body = f.read()
        self.assertEqual(body, str(len(data)).encode(httputil.ENCODING))

    def test_path(self):
        body = download(self.target + '/self/')
        self.assertIn(b'httputil.py', body)


prepare_webpy()
