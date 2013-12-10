#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-04-26
@author: shell.xu
'''
import socket, logging, urlparse

logger = logging.getLogger('http')

CHUNK_MIN   = 1024
BUFSIZE     = 8192
CODE_NOBODY = [100, 101, 204, 304]
DEFAULT_PAGES = {
    100:('Continue', 'Request received, please continue'),
    101:('Switching Protocols',
          'Switching to new protocol; obey Upgrade header'),

    200:('OK', ''),
    201:('Created', 'Document created, URL follows'),
    202:('Accepted', 'Request accepted, processing continues off-line'),
    203:('Non-Authoritative Information', 'Request fulfilled from cache'),
    204:('No Content', 'Request fulfilled, nothing follows'),
    205:('Reset Content', 'Clear input form for further input.'),
    206:('Partial Content', 'Partial content follows.'),

    300:('Multiple Choices', 'Object has several resources -- see URI list'),
    301:('Moved Permanently', 'Object moved permanently -- see URI list'),
    302:('Found', 'Object moved temporarily -- see URI list'),
    303:('See Other', 'Object moved -- see Method and URL list'),
    304:('Not Modified', 'Document has not changed since given time'),
    305:('Use Proxy',
          'You must use proxy specified in Location to access this resource.'),
    307:('Temporary Redirect', 'Object moved temporarily -- see URI list'),

    400:('Bad Request', 'Bad request syntax or unsupported method'),
    401:('Unauthorized', 'No permission -- see authorization schemes'),
    402:('Payment Required', 'No payment -- see charging schemes'),
    403:('Forbidden', 'Request forbidden -- authorization will not help'),
    404:('Not Found', 'Nothing matches the given URI'),
    405:('Method Not Allowed', 'Specified method is invalid for this server.'),
    406:('Not Acceptable', 'URI not available in preferred format.'),
    407:('Proxy Authentication Required',
          'You must authenticate with this proxy before proceeding.'),
    408:('Request Timeout', 'Request timed out; try again later.'),
    409:('Conflict', 'Request conflict.'),
    410:('Gone', 'URI no longer exists and has been permanently removed.'),
    411:('Length Required', 'Client must specify Content-Length.'),
    412:('Precondition Failed', 'Precondition in headers is false.'),
    413:('Request Entity Too Large', 'Entity is too large.'),
    414:('Request-URI Too Long', 'URI is too long.'),
    415:('Unsupported Media Type', 'Entity body in unsupported format.'),
    416:('Requested Range Not Satisfiable', 'Cannot satisfy request range.'),
    417:('Expectation Failed', 'Expect condition could not be satisfied.'),

    500:('Internal Server Error', 'Server got itself in trouble'),
    501:('Not Implemented', 'Server does not support this operation'),
    502:('Bad Gateway', 'Invalid responses from another server/proxy.'),
    503:('Service Unavailable',
          'The server cannot process the request due to a high load'),
    504:('Gateway Timeout',
          'The gateway server did not receive a timely response'),
    505:('HTTP Version Not Supported', 'Cannot fulfill request.'),
}

def dummy_write(d): return

def capitalize_httptitle(k):
    return '-'.join([t.capitalize() for t in k.split('-')])

def file_source(stream, size=BUFSIZE):
    d = stream.read(size)
    while d:
        yield d
        d = stream.read(size)

def chunked(f):
    for d in f: yield '%X\r\n%s\r\n' % (len(d), d)
    yield '0\r\n\r\n'

class HttpMessage(object):
    def __init__(self): self.headers, self.body = {}, None

    def add_header(self, k, v):
        self.headers.setdefault(k, [])
        self.headers[k].append(v)

    def set_header(self, k, v):
        self.headers[k] = [v,]

    def get_header(self, k, v=None):
        if k not in self.headers or len(self.headers[k]) == 0:
            return v
        return self.headers[k][0]

    def get_headers(self, k):
        return self.headers.get(k, [])

    def has_header(self, k):
        return self.get_header(k) is not None

    def del_header(self, k):
        del self.headers[k]

    def iter_headers(self):
        for k, l in self.headers.iteritems():
            for v in l: yield k, v

    def send_header(self, stream):
        stream.write(self.get_startline() + '\r\n')
        for k, l in self.headers.iteritems():
            for v in l: stream.write("%s: %s\r\n" % (k, v))
        stream.write('\r\n')
        stream.flush()

    @classmethod
    def recv_msg(cls, stream):
        line = stream.readline().strip()
        if len(line) == 0: raise EOFError()
        r = line.split(' ', 2)
        if len(r) < 2: raise Exception('unknown format')
        if len(r) < 3: r.append(DEFAULT_PAGES[int(r[1])][0])
        msg = cls(*r)
        msg.stream = stream
        msg.recv_header(stream)
        return msg

    def recv_header(self, stream):
        while True:
            line = stream.readline()
            if not line: raise EOFError()
            line = line.strip()
            if not line: break
            if line[0] not in (' ', '\t'):
                h, v = line.split(':', 1)
                self.add_header(h.strip(), v.strip())
            else: self.add_header(h.strip(), line.strip())

    def isclose(self, hasbody=False):
        if self.get_header('Transfer-Encoding', 'identity') == 'identity' and \
           not self.has_header('Content-Length') and hasbody:
            return True
        if self.version.upper() == 'HTTP/1.1':
            return self.get_header('Connection', '').lower() == 'close'
        if self.get_header('Keep-Alive'): return False
        return self.get_header('Connection', '').lower() != 'keep-alive'

    def read_chunk(self, stream, hasbody=False):
        if self.get_header('Transfer-Encoding', 'identity') != 'identity':
            logger.debug('recv body on chunk mode')
            chunk_size = 1
            while chunk_size:
                chunk = stream.readline().rstrip().split(';')
                chunk_size = int(chunk[0], 16)
                yield stream.read(chunk_size + 2)[:-2]
        elif self.has_header('Content-Length'):
            length = int(self.get_header('Content-Length'))
            logger.debug('recv body on length mode, size: %s' % length)
            for i in xrange(0, length, BUFSIZE):
                yield stream.read(min(length - i, BUFSIZE))
        elif hasbody:
            logger.debug('recv body on close mode')
            d = stream.read(BUFSIZE)
            while d:
                yield d
                d = stream.read(BUFSIZE)

    def read_body(self, hasbody=False):
        return ''.join(self.read_chunk(self.stream, hasbody))

    def read_form(self):
        return dict(i.split('=', 1) for i in self.read_body().split('&'))

    def sendto(self, stream, body=None, *p):
        body = body or self.body
        self.send_header(stream)
        if body is None: return
        if callable(body): body = body(*p)
        if hasattr(body, '__iter__'):
            for d in body: stream.write(d)
        else: stream.write(body)
        stream.flush()

    def debug(self):
        logger.debug(self.d + self.get_startline())
        for k, l in self.headers.iteritems():
            for v in l: logger.debug('%s%s: %s' % (self.d, k, v))
        logger.debug('')

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

def request_http(uri, method=None, version=None, headers=None, body=None):
    if not method: method = 'GET' if body is None else 'POST'
    if not version: version = 'HTTP/1.1'
    req = Request(method, uri, version)
    if isinstance(headers, dict): headers = headers.items()
    if headers: req.headers = headers
    if body:
        if isinstance(body, basestring):
            req.set_header('Content-Length', str(len(body)))
        elif hasattr(body, '__iter__'):
            req.set_header('Transfer-Encoding', 'chunked')
            body = chunked(body)
        elif hasattr(body, 'read'):
            req.set_header('Transfer-Encoding', 'chunked')
            body = chunked(file_source(body))
        req.body = body
    return req

class RequestFile(FileBase):

    def __init__(self, stream):
        self.stream = stream

    def write(self, s):
        self.stream.write('%x\r\n%s\r\n' % (len(s), s,))

    def close(self):
        self.stream.write('0\r\n\r\n')
        self.stream.flush()

    def get_response(self):
        return Response.recv_msg(self.stream)

class Response(HttpMessage):
    d = '< '

    def __init__(self, version, code, phrase):
        HttpMessage.__init__(self)
        self.version, self.code, self.phrase = version, int(code), phrase
        self.connection, self.cache = False, 0

    def __nonzero__(self): return self.connection

    def get_startline(self):
        return ' '.join((self.version, str(self.code), self.phrase))

    def makefile(self):
        return ResponseFile(self)

def response_http(code, phrase=None, version=None, headers=None,
                  cache=0, body=None):
    if not phrase: phrase = DEFAULT_PAGES[code][0]
    if not version: version = 'HTTP/1.1'
    res = Response(version, code, phrase)
    if isinstance(headers, dict): headers = header.items()
    if hasattr(headers, '__iter__'):
        for k, v in header: res.add_header(k, v)
    if body:
        if isinstance(body, basestring):
            res.set_header('Content-Length', str(len(body)))
        res.body = body
    res.cache = cache
    return res

def response_to(req, code, phrase=None, headers=None, body=None):
    res = response_http(
        code, phrase=phrase, version=req.version, headers=headers, body=body)
    res.sendto(req.stream)
    return res

class ResponseFile(FileBase):

    def __init__(self, resp):
        self.resp, self.f, self.d = resp, resp.read_chunk(resp.stream), ''

    def getcode(self):
        return int(self.resp.code)

    def read(self, size=None):
        if self.f is None:
            if self.d:
                d, self.d = self.d, ''
                return self.d
            return ''
        while size is None or self.d < size:
            try: d = self.f.next()
            except StopIteration:
                self.close()
                break
            self.d += d
        if size is not None:
            d, self.d = self.d[:size], self.d[size:]
        else: d, self.d = self.d, ''
        return d

    def close(self):
        self.f = None
        if self.resp.get_header('Connection') != 'keep-alive':
            self.resp.stream.close()

def parseurl(url):
    u = urlparse.urlparse(url)
    uri = u.path
    if u.query: uri += '?' + u.query
    if ':' not in u.netloc:
        host, port = u.netloc, 443 if u.scheme == 'https' else 80
    else: host, port = u.netloc.split(':', 1)
    return host, int(port), uri

def download(url, method=None, headers=None, data=None):
    host, port, uri = parseurl(url)
    req = request_http(uri, method, headers=headers, body=data)
    req.set_header('Host', host)
    sock = socket.socket()
    sock.connect((host, port))
    stream = sock.makefile()
    try:
        req.sendto(stream)
        return Response.recv_msg(stream)
    except:
        sock.close()
        raise
