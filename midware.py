#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2012-09-03
@author: shell.xu
@license: BSD-3-clause
'''
from __future__ import absolute_import, division,\
    print_function, unicode_literals
import re
import time
import heapq
import random
import pickle
import logging
import unittest
import functools
try:
    from urllib import quote, unquote
except ImportError:
    from urllib.parse import quote, unquote
import http


class Dispatch(object):

    def __init__(self, urlmap=None):
        self.urlmap = [[re.compile(i[0]), ] + list(i[1:]) for i in urlmap]

    def __call__(self, req):
        for o in self.urlmap:
            m = o[0].match(req.url.path)
            if not m:
                continue
            req.url_match = m.groups()
            req.url_param = o[2:]
            return o[1](req)
        return self.default_handler(req)

    def default_handler(req):
        return http.response_http(404, body='File Not Found')


class Cache(object):

    def __call__(self, func):
        def inner(req):
            pd = self.get_data(req.url.path)
            if pd:
                logging.info('cache hit in %s', req.url.path)
                return pickle.loads(pd)
            res = func(req)
            if res is not None and res.cache and res.body:
                res['Cache-Control'] = 'max-age=%d' % res.cache
                pd = pickle.dumps(res, 2)
                self.set_data(req.url.path, pd, res.cache)
            return res
        return inner


class ObjHeap(object):
    '''\
使用lru算法的对象缓存容器，感谢Evan Prodromou <evan@bad.dynu.ca>。
注意：非线程安全。
thx for Evan Prodromou <evan@bad.dynu.ca>.
CAUTION: not satisfy with thread.
    '''

    @functools.total_ordering
    class __node(object):

        def __init__(self, k, v, f):
            self.k, self.v, self.f = k, v, f

        def __lt__(self, o):
            return self.f < o.f

    def __init__(self, size):
        self.size, self.f = size, 0
        self.__dict, self.__heap = {}, []

    def __len__(self):
        return len(self.__dict)

    def __contains__(self, k):
        return k in self.__dict

    def __setitem__(self, k, v):
        if k in self.__dict:
            n = self.__dict[k]
            n.v = v
            self.f += 1
            n.f = self.f
            heapq.heapify(self.__heap)
        else:
            while len(self.__heap) >= self.size:
                del self.__dict[heapq.heappop(self.__heap).k]
                self.f = 0
                for n in self.__heap:
                    n.f = 0
            n = self.__node(k, v, self.f)
            self.__dict[k] = n
            heapq.heappush(self.__heap, n)

    def __getitem__(self, k):
        n = self.__dict[k]
        self.f += 1
        n.f = self.f
        heapq.heapify(self.__heap)
        return n.v

    def __delitem__(self, k):
        n = self.__dict[k]
        del self.__dict[k]
        self.__heap.remove(n)
        heapq.heapify(self.__heap)
        return n.v

    def __iter__(self):
        c = self.__heap[:]
        while len(c):
            yield heapq.heappop(c).k
        raise StopIteration


# CAUTION: Although MC has expire time, but it will not work until
# trying to get data back after timeout. So maybe in some case, LRU will
# squeeze out some data not expired, when some other has expired but
# used more frequently.
#
# To fix this problem, we need another heap to trace when will those data
# timeout. It's more complex, and far as I see, not necessary.
class MemoryCache(Cache):

    def __init__(self, size):
        super(MemoryCache, self).__init__()
        self.oh = ObjHeap(size)

    def get_data(self, k):
        try:
            o = self.oh[k]
        except KeyError:
            return None
        if o[1] >= time.time():
            return o[0]
        del self.oh[k]
        return None

    def set_data(self, k, v, exp):
        self.oh[k] = (v, time.time() + exp)


class TestHeap(unittest.TestCase):

    def test_CRUD(self):
        oh = ObjHeap(2)
        oh[1] = 10
        self.assertEqual(oh[1], 10)
        oh[1] = 20
        self.assertEqual(oh[1], 20)
        del oh[1]
        self.assertNotIn(1, oh)

    def test_LRU(self):
        oh = ObjHeap(2)
        oh[1] = 10
        oh[2] = 20
        oh[3] = 30
        self.assertNotIn(1, oh)

    def test_MC(self):
        mc = MemoryCache(2)
        mc.set_data(1, 10, 1)
        mc.set_data(2, 20, 1)
        mc.set_data(3, 30, 1)
        self.assertEqual(mc.get_data(1), None)

    def test_timeout(self):
        mc = MemoryCache(2)
        mc.set_data(1, 10, 0.01)
        time.sleep(0.1)
        self.assertEqual(mc.get_data(1), None)


random.seed()
alpha = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/'


def get_rnd_sess():
    return ''.join(random.sample(alpha, 32))


def get_params_dict(data, sp='&'):
    if not data:
        return {}
    rslt = {}
    for p in data.split(sp):
        i = p.strip().split('=', 1)
        rslt[i[0]] = unquote(i[1])
    return rslt


class Cookie(object):

    def __init__(self, cookie):
        if not cookie:
            self.v = {}
        else:
            self.v = get_params_dict(cookie, ';')
        self.m = set()

    def get(self, k, d):
        return self.v.get(k, d)

    def __contains__(self, k):
        return k in self.v

    def __getitem__(self, k):
        return self.v[k]

    def __delitem__(self, k):
        self.m.add(k)
        del self.v[k]

    def __setitem__(self, k, v):
        self.m.add(k)
        self.v[k] = v

    def set_cookie(self, res):
        for k in self.m:
            res.add('Set-Cookie', '%s=%s' % (k, quote(self.v[k])))


class Session(object):

    def __init__(self, timeout):
        self.exp = timeout

    def __call__(self, func):
        def inner(req):
            req.cookie = Cookie(req.get('Cookie'))
            sessionid = req.cookie.get('sessionid', '')
            if not sessionid:
                sessionid = get_rnd_sess()
                req.cookie['sessionid'] = sessionid
                data = None
            else:
                data = self.get_data(sessionid)
            req.session = {}
            if data:
                req.session = pickle.loads(data)
            logging.info('sessionid: %s' % sessionid)
            logging.info('session: %s' % str(req.session))
            res = func(req)
            self.set_data(sessionid, pickle.dumps(req.session, 2))
            req.cookie.set_cookie(res)
            return res
        return inner


class MemorySession(Session):

    def __init__(self, timeout):
        super(MemorySession, self).__init__(timeout)
        self.sessions = {}

    def get_data(self, sessionid):
        return self.sessions.get(sessionid, None)

    def set_data(self, sessionid, data):
        self.sessions[sessionid] = data
