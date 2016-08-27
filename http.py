#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-04-26
@author: shell.xu
@license: BSD-3-clause
'''
from __future__ import absolute_import, division,\
    print_function, unicode_literals
import sys
import socket
import logging
import datetime
import threading
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

if sys.version_info.major == 3:
    basestring = str

CHUNK_MIN = 1024
BUFSIZE = 8192
CODE_NOBODY = [100, 101, 204, 304]
DEFAULT_PAGES = {
    100: ('Continue', 'Request received, please continue'),
    101: ('Switching Protocols',
          'Switching to new protocol; obey Upgrade header'),

    200: ('OK', ''),
    201: ('Created', 'Document created, URL follows'),
    202: ('Accepted', 'Request accepted, processing continues off-line'),
    203: ('Non-Authoritative Information', 'Request fulfilled from cache'),
    204: ('No Content', 'Request fulfilled, nothing follows'),
    205: ('Reset Content', 'Clear input form for further input.'),
    206: ('Partial Content', 'Partial content follows.'),

    300: ('Multiple Choices', 'Object has several resources -- see URI list'),
    301: ('Moved Permanently', 'Object moved permanently -- see URI list'),
    302: ('Found', 'Object moved temporarily -- see URI list'),
    303: ('See Other', 'Object moved -- see Method and URL list'),
    304: ('Not Modified', 'Document has not changed since given time'),
    305: ('Use Proxy',
          'You must use proxy specified in Location to access this resource.'),
    307: ('Temporary Redirect', 'Object moved temporarily -- see URI list'),

    400: ('Bad Request', 'Bad request syntax or unsupported method'),
    401: ('Unauthorized', 'No permission -- see authorization schemes'),
    402: ('Payment Required', 'No payment -- see charging schemes'),
    403: ('Forbidden', 'Request forbidden -- authorization will not help'),
    404: ('Not Found', 'Nothing matches the given URI'),
    405: ('Method Not Allowed',
          'Specified method is invalid for this server.'),
    406: ('Not Acceptable', 'URI not available in preferred format.'),
    407: ('Proxy Authentication Required',
          'You must authenticate with this proxy before proceeding.'),
    408: ('Request Timeout', 'Request timed out; try again later.'),
    409: ('Conflict', 'Request conflict.'),
    410: ('Gone', 'URI no longer exists and has been permanently removed.'),
    411: ('Length Required', 'Client must specify Content-Length.'),
    412: ('Precondition Failed', 'Precondition in headers is false.'),
    413: ('Request Entity Too Large', 'Entity is too large.'),
    414: ('Request-URI Too Long', 'URI is too long.'),
    415: ('Unsupported Media Type', 'Entity body in unsupported format.'),
    416: ('Requested Range Not Satisfiable', 'Cannot satisfy request range.'),
    417: ('Expectation Failed', 'Expect condition could not be satisfied.'),

    500: ('Internal Server Error', 'Server got itself in trouble'),
    501: ('Not Implemented', 'Server does not support this operation'),
    502: ('Bad Gateway', 'Invalid responses from another server/proxy.'),
    503: ('Service Unavailable',
          'The server cannot process the request due to a high load'),
    504: ('Gateway Timeout',
          'The gateway server did not receive a timely response'),
    505: ('HTTP Version Not Supported', 'Cannot fulfill request.'),
}

HTTPTIMEFMT = '%a, %d %b %Y %H:%M:%S %Z'


def HttpDate2Time(s):
    return datetime.datetime.strptime(s, HTTPTIMEFMT)


def Time2HttpDate(dt):
    return dt.strftime(HTTPTIMEFMT)


def file_source(stream, size=BUFSIZE):
    d = stream.read(size)
    while d:
        yield d
        d = stream.read(size)


def chunked_body(stream):
    chunk = stream.readline().rstrip().split(';')
    chunk_size = int(chunk[0], 16)
    while chunk_size:
        d = stream.read(chunk_size + 2)
        if not d:
            raise EOFError
        d = d[:-2]
        if not d:
            break
        yield d
        chunk = stream.readline().rstrip().split(';')
        chunk_size = int(chunk[0], 16)


def length_body(stream, length):
    for i in range(0, length, BUFSIZE):
        d = stream.read(min(length - i, BUFSIZE))
        if not d:
            raise EOFError
        yield d


def chunked(f):
    for d in f:
        yield '%X\r\n%s\r\n' % (len(d), d)
    yield '0\r\n\r\n'


class BufferedFile(object):

    def __init__(self, it):
        self.it, self.buf = it, ''

    def read(self, size=-1):
        try:
            while size == -1 or len(self.buf) < size:
                self.buf += self.it.next()
        except StopIteration:
            size = len(self.buf)
        r, self.buf = self.buf[:size], self.buf[size:]
        return r


class HttpMessage(object):

    def __init__(self):
        self.headers = {}
        self.sent = False
        self.length = None
        self.body = None
        self.keepalive = True
        self.cache = 0

    def add(self, k, v):
        self.headers.setdefault(k, [])
        self.headers[k].append(v)

    def __setitem__(self, k, v):
        self.headers[k] = [v, ]

    def __getitem__(self, k):
        if k not in self:
            raise KeyError
        return self.headers[k][0]

    def get(self, k, v=None):
        if k not in self:
            return v
        return self.headers[k][0]

    def get_headers(self, k):
        return self.headers.get(k, [])

    def __contains__(self, k):
        return self.headers.get(k)

    def __delitem__(self, k):
        del self.headers[k]

    def __iter__(self):
        for k, l in self.headers.iteritems():
            for v in l:
                yield k, v

    def send_header(self, stream):
        stream.write(self.get_startline() + '\r\n')
        for k, v in self:
            stream.write("%s: %s\r\n" % (k, v))
        stream.write('\r\n')
        stream.flush()
        self.sent = True

    def recv_header(self, stream):
        while True:
            line = stream.readline()
            if not line:
                raise EOFError()
            line = line.strip()
            if not line:
                break
            if line[0] not in (' ', '\t'):
                h, v = line.split(':', 1)
                self.add(h.strip(), v.strip())
            else:
                self.add(h.strip(), line.strip())

    def debug(self):
        logging.debug(self.d + self.get_startline())
        for k, v in self:
            logging.debug('%s%s: %s' % (self.d, k, v))
        logging.debug('')

    def recvdone(self):
        if self.version == 'HTTP/1.1':
            self.keepalive = self.get('Connection') != 'close'
        else:
            self.keepalive = self.get('Connection') == 'keep-alive'

    def beforesend(self):
        self['Connection'] = 'keep-alive' if self.keepalive else 'close'

    @classmethod
    def recvfrom(cls, stream, sock=None):
        line = stream.readline().strip()
        if len(line) == 0:
            raise EOFError()
        r = line.split(' ', 2)
        if len(r) < 2:
            raise Exception('unknown format', r)
        if len(r) < 3:
            r.append(DEFAULT_PAGES[int(r[1])][0])
        msg = cls(*r)
        msg.recv_header(stream)
        msg.stream, msg.sock = stream, sock
        if msg.get('Transfer-Encoding', 'identity') != 'identity':
            msg.body = chunked_body(stream)
            logging.debug('recv body on chunk mode')
        elif 'Content-Length' in msg:
            msg.length = int(msg['Content-Length'])
            msg.body = length_body(stream, msg.length)
            logging.debug('recv body on length mode, size: %s' % msg.length)
        elif msg.hasbody():
            msg.body = file_source(stream)
            logging.debug('recv body on close mode')
        else:
            logging.debug('recv body on nobody mode')
        msg.recvdone()
        return msg

    def readbody(self):
        if hasattr(self.body, '__iter__'):
            self.body = ''.join(self.body)
        if hasattr(self.body, 'read'):
            self.body = self.body.read()
        return self.body

    def readform(self):
        return dict(i.split('=', 1) for i in self.readbody().split('&'))

    def sendto(self, stream):
        self.beforesend()
        if hasattr(self.body, 'read'):  # transfer file to chunk
            self.body = file_source(self.body)
        elif isinstance(self.body, basestring):
            self.length = len(self.body)
        if self.length is not None:  # length fit for data and stream
            self['Content-Length'] = str(self.length)
        elif self.body is not None:  # set chunked if use chunk mode
            self['Transfer-Encoding'] = 'chunked'
            self.body = chunked(self.body)
        self.send_header(stream)
        if self.body is None:
            return
        if hasattr(self.body, '__iter__'):
            for b in self.body:
                stream.write(b)
        else:
            stream.write(self.body)
        stream.flush()


class FileBase(object):

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self.close()


class Request(HttpMessage):
    d = '> '

    def __init__(self, method, uri, version):
        HttpMessage.__init__(self)
        self.method, self.uri, self.version = method, uri, version

    def get_startline(self):
        return ' '.join((self.method, self.uri, self.version))

    def hasbody(self):
        return False


def request_http(uri, method=None, version=None, headers=None, body=None):
    if not method:
        method = 'GET' if body is None else 'POST'
    if not version:
        version = 'HTTP/1.1'
    req = Request(method, uri, version)
    if isinstance(headers, dict):
        headers = headers.items()
    if headers:
        for k, v in headers:
            req.add(k, v)
    if body:
        req.body = body
    return req


class RequestWriteFile(FileBase):

    def __init__(self, stream):
        self.stream = stream

    def write(self, s):
        self.stream.write('%x\r\n%s\r\n' % (len(s), s,))

    def close(self):
        self.stream.write('0\r\n\r\n')
        self.stream.flush()

    def get_response(self):
        return Response.recvfrom(self.stream)


class Response(HttpMessage):
    d = '< '

    def __init__(self, version, code, phrase):
        HttpMessage.__init__(self)
        self.version, self.code, self.phrase = version, int(code), phrase

    def __nonzero__(self):
        return self.keepalive

    def close(self):
        return self.stream.close()

    def get_startline(self):
        return ' '.join((self.version, str(self.code), self.phrase))

    def hasbody(self):
        return self.code not in CODE_NOBODY

    def makefile(self):
        return ResponseFile(self)


def response_http(code, phrase=None, version=None,
                  headers=None, body=None):
    if not phrase:
        phrase = DEFAULT_PAGES[code][0]
    if not version:
        version = 'HTTP/1.1'
    res = Response(version, code, phrase)
    if isinstance(headers, dict):
        headers = headers.items()
    if headers:
        for k, v in headers:
            res.add(k, v)
    if body:
        res.body = body
    return res


def response_to(req, code, phrase=None, headers=None, body=None):
    res = response_http(code, phrase=phrase, version=req.version,
                        headers=headers, body=body)
    res.keepalive = req.keepalive
    res.sendto(req.stream)
    return res


class ResponseFile(FileBase):

    def __init__(self, resp):
        self.resp = resp
        self.f = BufferedFile(resp.body)
        self.read = self.f.read
        self.close = resp.close

    def getcode(self):
        return int(self.resp.code)


def parseurl(url):
    u = urlparse(url)
    uri = u.path
    if u.query:
        uri += '?' + u.query
    if ':' not in u.netloc:
        host, port = u.netloc, 443 if u.scheme == 'https' else 80
    else:
        host, port = u.netloc.split(':', 1)
    return host, int(port), uri


class WebServer(object):

    def __init__(self, application, accesslog=None):
        self.application = application
        if accesslog == '':
            self.accessfile = sys.stdout
        elif accesslog:
            self.accessfile = open(accesslog, 'a')

    def record_access(self, req, res, addr):
        if not hasattr(self, 'accessfile'):
            return
        if res is None:
            code, length = 500, None
        else:
            code, length = res.code, res.length
        if length is None:
            length = '-'
        else:
            length = str(length)
        self.accessfile.write(
            '%s:%d - - [%s] "%s" %d %s "-" %s\n' % (
                addr[0], addr[1], datetime.datetime.now().isoformat(),
                req.get_startline(), code, length, req.get('User-Agent')))
        self.accessfile.flush()

    def http_handler(self, req):
        req.url = urlparse(req.uri)
        res = self.application(req)
        if res is None:
            res = response_http(500, body='service internal error')
        return res

    def handler(self, sock, addr):
        stream, res = sock.makefile(), True
        try:
            while res:
                req, res = None, None
                try:
                    req = Request.recvfrom(stream)
                    req.remote = addr
                    res = self.http_handler(req)
                    res.sendto(req.stream)
                finally:
                    if req:
                        if res is True:
                            res = None
                        self.record_access(req, res, addr)
        except (EOFError, socket.error):
            logging.info('network error')
        except Exception as err:
            logging.exception('unknown')
        finally:
            sock.close()


class WSGIServer(WebServer):

    def req2env(self, req):
        env = dict(('HTTP_' + k.upper().replace('-', '_'), v)
                   for k, v in req)
        env['REQUEST_METHOD'] = req.method
        env['SCRIPT_NAME'] = ''
        env['PATH_INFO'] = req.url.path
        env['QUERY_STRING'] = req.url.query
        env['CONTENT_TYPE'] = req.get('Content-Type')
        env['CONTENT_LENGTH'] = req.get('Content-Length', 0)
        env['SERVER_PROTOCOL'] = req.version
        if req.method in set(['POST', 'PUT']):
            env['wsgi.input'] = BufferedFile(req.body)
        return env

    def http_handler(self, req):
        req.url = urlparse(req.uri)
        env = self.req2env(req)

        res = response_http(500)

        def start_response(status, headers):
            r = status.split(' ', 1)
            res.code = int(r[0])
            if len(r) > 1:
                res.phrase = r[1]
            else:
                res.phrase = DEFAULT_PAGES[res.code][0]
            for k, v in headers:
                res.add(k, v)
            res.add('Transfer-Encoding', 'chunked')
            res.send_header(req.stream)

        try:
            for b in chunked(self.application(env, start_response)):
                req.stream.write(b)
            req.stream.flush()
        finally:  # empty all send body
            if not res.sent:
                res.send_header(req.stream)
            for b in req.body:
                pass
        return res


class SocketPool(object):

    def __init__(self, max_addr=-1):
        self._lock = threading.RLock()
        self.buf, self.max_addr = {}, max_addr

    def setmax(self, max_addr=-1):
        self.max_addr = max_addr

    def __call__(self, addr):
        host = addr[0]
        addr = (socket.gethostbyname(host), addr[1])
        stream = None
        with self._lock:
            if self.buf.get(addr):
                stream = self.buf[addr].pop(0)
                logging.debug('acquire conn %s:%d size %d' % (
                    host, addr[1], len(self.buf[addr])))
        if stream is None:
            logging.debug('create new conn: %s:%d' % (host, addr[1]))
            stream = connect_addr(addr)
            stream._close = stream.close
            stream.close = lambda: self.release(stream)
        return stream

    def release(self, stream):
        try:
            addr = stream._sock.getpeername()
        except socket.error:
            logging.debug('free conn.')
            return
        with self._lock:
            self.buf.setdefault(addr, [])
            if self.max_addr < 0 or len(self.buf[addr]) < self.max_addr:
                self.buf[addr].append(stream)
                logging.debug('release conn %s:%d back size %d' % (
                    addr[0], addr[1], len(self.buf[addr])))
                return
        logging.debug('free conn %s:%d.' % (addr[0], addr[1]))
        stream._close()

# connector = SocketPool()


def connect_addr(addr):
    s = socket.socket()
    s.connect(addr)
    return s.makefile()

connector = connect_addr


def round_trip(req):
    try:
        req.stream = connector(req.remote)
    except IOError:
        return response_to(req, 502)
    try:
        req.sendto(req.stream)
        req.stream.flush()
        return Response.recvfrom(req.stream)
    finally:
        req.stream.close()


def download(url, method=None, headers=None, data=None):
    host, port, uri = parseurl(url)
    if not uri:
        uri = '/'
    req = request_http(uri, method, headers=headers, body=data)
    req.remote = (host, port)
    req['Host'] = host
    return round_trip(req)
