#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-10-17
@author: shell.xu
@license: BSD-3-clause
'''
from __future__ import absolute_import, division,\
    print_function, unicode_literals
import time
import http
import unittest
from gevent import monkey
from contextlib import closing


monkey.patch_all()


def download(url):
    with closing(http.download(url)) as resp:
        return resp.readbody()


def getfile(url):
    with http.download(url).makefile() as f:
        return f.read()


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


def inner_main():
    import apps
    ws = http.WebServer(apps.dis)
    from gevent.server import StreamServer
    ws = StreamServer(('', 18080), ws.handler)

    import gevent
    gevent.spawn(ws.serve_forever)
    time.sleep(1)


inner_main()


class TestClient(unittest.TestCase):

    def test_main(self):
        body = download('http://localhost:18080/urlmatch')
        self.assertEqual(
            body,
            'main page, count: 0, match: ["urlmatch"], param: ["main param"]')

    def test_getfile(self):
        body = getfile('http://localhost:18080/urlmatch')
        self.assertEqual(
            body,
            'main page, count: 0, match: ["urlmatch"], param: ["main param"]')

    def test_cached(self):
        for i in range(12):
            body = download(
                'http://localhost:18080/cached/{}'.format(int(i/3)))
            self.assertEqual(body, 'cached')

        time.sleep(1)
        body = download('http://localhost:18080/cached/abc')
        self.assertEqual(body, 'cached')

    def test_test(self):
        body = download('http://localhost:18080/test/testmatch')
        self.assertEqual(
            body,
            'main page, count: 0, match: ["testmatch"], param: ["test param"]')

    def test_post(self):
        with open('http.py', 'rb') as fi:
            data = fi.read()
        with http.download('http://localhost:18080/post/postmatch',
                           data=data).makefile() as f:
            body = f.read()
        self.assertEqual(body, str(len(data)))

    def test_post_file(self):
        with open('http.py', 'rb') as fi:
            with http.download('http://localhost:18080/post/postmatch',
                               data=fi).makefile() as f:
                body = f.read()
        with open('http.py', 'rb') as fi:
            data = fi.read()
        self.assertEqual(body, str(len(data)))

    def test_upload(self):
        with open('http.py', 'rb') as fi:
            data = fi.read()
        with upload('http://localhost:18080/post/postmatch') as f:
            f.write(data)
        with closing(f.get_response()) as resp:
            self.assertEqual(resp.readbody(), str(len(data)))
