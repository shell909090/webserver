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
import time
import http
import unittest
import StringIO
from gevent import monkey
from contextlib import closing

if sys.version_info.major == 3:
    unicode = str
else:
    bytes = str


monkey.patch_all()


def download(url):
    with closing(http.download(url)) as resp:
        return resp.readbody()


def prepare_apps():
    import apps
    ws = http.WebServer(apps.dis, StringIO.StringIO())
    from gevent.server import StreamServer
    ws = StreamServer(('', 18080), ws.handler)
    import gevent
    gevent.spawn(ws.serve_forever)
    time.sleep(1)


prepare_apps()


class TestClientApp(unittest.TestCase):
    target = 'http://localhost:18080'

    def test_main(self):
        body = download(self.target + '/urlmatch')
        self.assertEqual(
            body,
            b'main page, count: 0, match: ["urlmatch"], param: ["main param"]')

    def test_getfile(self):
        with http.download(self.target + '/urlmatch').makefile() as f:
            body = f.read()
        self.assertEqual(
            body,
            b'main page, count: 0, match: ["urlmatch"], param: ["main param"]')

    def test_cached(self):
        for i in range(12):
            body = download(
                self.target + '/cached/{}'.format(int(i/3)))
            self.assertEqual(body, b'cached')

        time.sleep(1)
        body = download(self.target + '/cached/abc')
        self.assertEqual(body, b'cached')

    def test_test(self):
        body = download(self.target + '/test/testmatch')
        self.assertEqual(
            body,
            b'main page, count: 0, match: ["testmatch"], param: ["test param"]'
        )

    def test_post(self):
        with open('http.py', 'rb') as fi:
            data = fi.read()
        with http.download(
                self.target + '/post/postmatch',
                data=data
        ).makefile() as f:
            body = f.read()
        self.assertEqual(body, str(len(data)).encode(http.ENCODING))

    def test_post_file(self):
        with open('http.py', 'rb') as fi:
            with http.download(self.target + '/post/postmatch',
                               data=fi).makefile() as f:
                body = f.read()
        with open('http.py', 'rb') as fi:
            data = fi.read()
        self.assertEqual(body, str(len(data)).encode(http.ENCODING))

    @staticmethod
    def upload(url):
        host, port, uri = http.parseurl(url)
        req = http.request_http(uri, 'POST')
        req.remote = (host, port)
        req['Host'] = host
        req['Transfer-Encoding'] = 'chunked'
        stream = http.connector(req.remote)
        try:
            req.send_header(stream)
            return http.RequestWriteFile(stream)
        except:
            stream.close()
            raise

    def test_upload(self):
        with open('http.py', 'rb') as fi:
            data = fi.read()
        with self.upload(self.target + '/post/postmatch') as f:
            f.write(data)
        with closing(f.get_response()) as resp:
            self.assertEqual(
                resp.readbody(),
                str(len(data)).encode(http.ENCODING))

    def test_path(self):
        body = download(self.target + '/self/')
        self.assertIn(b'http.py', body)


def prepare_webpy():
    import app_webpy
    ws = http.WSGIServer(app_webpy.app.wsgifunc())
    from gevent.server import StreamServer
    ws = StreamServer(('', 18081), ws.handler)
    import gevent
    gevent.spawn(ws.serve_forever)
    time.sleep(1)


prepare_webpy()


class TestClientWebpy(unittest.TestCase):
    target = 'http://localhost:18081'

    def test_main(self):
        body = download(self.target + '/urlmatch')
        self.assertEqual(
            body,
            b'main page, count: 0, match: urlmatch')

    def test_post(self):
        with open('http.py', 'rb') as fi:
            data = fi.read()
        with http.download(
                self.target + '/post/postmatch',
                data=data
        ).makefile() as f:
            body = f.read()
        self.assertEqual(body, str(len(data)).encode(http.ENCODING))

    def test_path(self):
        body = download(self.target + '/self/')
        self.assertIn(b'http.py', body)
