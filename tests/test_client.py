import json
import time
import unittest
from contextlib import closing
from multiprocessing import Pipe, Process
import importlib.util
import httputil


def run_server(connection, engine):
    if engine == "apps":
        import apps
        server = httputil.WebServer(apps.dis)
    else:
        import app_webpy
        server = httputil.WSGIServer(app_webpy.app.wsgifunc())
    listener = httputil.ThreadServer(("127.0.0.1", 0), server.handler)
    listener.start()
    connection.send(listener.listen_socket.getsockname()[1])
    connection.close()
    try:
        listener.join()
    except KeyboardInterrupt:
        pass
    finally:
        listener.listen_socket.close()


class HTTPTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if cls.engine == "wsgi" and importlib.util.find_spec("web") is None:
            raise unittest.SkipTest("web.py extra is not installed")
        parent, child = Pipe()
        cls.server = Process(target=run_server, args=(child, cls.engine))
        cls.server.start()
        child.close()
        cls.addClassCleanup(cls.stop_server)
        try:
            if not parent.poll(10):
                raise RuntimeError("HTTP test server startup timed out")
            cls.target = "http://127.0.0.1:" + str(parent.recv())
        finally:
            parent.close()

    @classmethod
    def stop_server(cls):
        cls.server.terminate()
        cls.server.join(3)
        if cls.server.is_alive():
            cls.server.kill()
            cls.server.join()


def download(url):
    with closing(httputil.download(url)) as response:
        return response.readbody()


class TestClientApp(HTTPTestCase):
    engine = "apps"

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


class TestClientWebpy(HTTPTestCase):
    engine = "wsgi"

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

