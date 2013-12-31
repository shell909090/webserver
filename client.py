#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-10-17
@author: shell.xu
'''
import os, sys, socket, logging
import utils, http

def download(url):
    resp = http.download(url)
    try: return resp.read_body()
    finally: resp.stream.close()

def getfile(url):
    return http.download(url).makefile().read()

def post(url):
    with open('http.py', 'rb') as fi:
        return http.download(url, data=fi).makefile().read()

def upload(url):
    host, port, uri = http.parseurl(url)
    req = http.request_http(uri, 'POST')
    req['Host'] = host
    req['Transfer-Encoding'] = 'chunked'
    sock = socket.socket()
    sock.connect((host, port))
    stream = sock.makefile()
    try:
        req.send_header(stream)
        return http.RequestWriteFile(stream)
    except:
        sock.close()
        raise

def test_upload(url):
    f = upload(url)
    with f:
        with open('http.py', 'rb') as fi:
            f.write(fi.read())
    resp = f.get_response()
    return resp.read_body()

def main():
    utils.initlog('DEBUG')
    print 'download self len:', len(download('http://localhost:8080/self/'))
    print 'get file self len:', len(getfile('http://localhost:8080/self/'))
    print 'post file:', post('http://localhost:8080/post/')
    print 'upload file:', test_upload('http://localhost:8080/post/')

if __name__ == '__main__': main()
