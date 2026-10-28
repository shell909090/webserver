import unittest
import json
import time
import httputil
from apps import dis


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

