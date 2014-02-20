#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-10-17
@author: shell.xu
'''
import os, sys, socket, logging
import utils, http
from contextlib import closing

def download(url):
    with closing(http.download(url)) as resp:
        return resp.readbody()

def getfile(url):
    with http.download(url).makefile() as f:
        return f.read()

def post(url):
    with open('http.py', 'rb') as fi:
        with http.download(url, data=fi).makefile() as f:
            return f.read()

def upload(url):
    host, port, uri = http.parseurl(url)
    req = http.request_http(uri, 'POST')
    req.remote = (host, port)
    req['Host'] = host
    req['Transfer-Encoding'] = 'chunked'
    stream = http.connector.connect(req.remote)
    try:
        req.send_header(stream)
        return http.RequestWriteFile(stream)
    except:
        stream.close()
        raise

def test_upload(url):
    f = upload(url)
    with f:
        with open('http.py', 'rb') as fi:
            f.write(fi.read())
    with closing(f.get_response()) as resp:
        return resp.readbody()

def main():
    utils.initlog('DEBUG')
    print 'download self len:', len(download('http://localhost:8080/self/'))
    print 'get file self len:', len(getfile('http://localhost:8080/self/'))
    print 'upload file:', test_upload('http://localhost:8080/post/')
    print 'post file:', post('http://localhost:8080/post/')

if __name__ == '__main__': main()
