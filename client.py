#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2013-10-17
@author: shell.xu
'''
import os, sys, logging
from urlparse import urlparse
import http

def parseurl(url):
    u = urlparse(url)
    uri = u.path
    if u.query: uri += u.query
    if ':' not in u.netloc:
        host, port = u.netloc, 443 if u.scheme == 'https' else 80
    else: host, port = u.netloc.split(':', 1)
    return host, int(port), uri

def download(url):
    host, port, uri = parseurl(url)
    try:
        resp = http.download(host, port, uri)
        return resp.read_body()
    finally: resp.stream.close()

def getfile(url):
    host, port, uri = parseurl(url)
    return http.download(host, port, uri).makefile().read()

def post(url):
    host, port, uri = parseurl(url)
    with open('http.pyc', 'rb') as fi:
        return http.download(host, port, uri, data=fi).makefile().read()

def upload(url):
    host, port, uri = parseurl(url)
    f = http.upload(host, port, uri)
    with open('http.py', 'rb') as fi:
        for line in fi: f.write(line)
    f.close()
    resp = f.get_response()
    return resp.read_body()

def main():
    logging.basicConfig(level=logging.DEBUG)
    print 'download self len:', len(download('http://localhost:8080/self/'))
    print 'get file self len:', len(getfile('http://localhost:8080/self/'))
    print 'post file:', post('http://localhost:8080/post/')
    print 'upload file:', upload('http://localhost:8080/post/')

if __name__ == '__main__': main()
