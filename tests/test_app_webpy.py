import unittest
try:
    from app_webpy import app
except ModuleNotFoundError as exc:
    if exc.name != "web":
        raise
    app = None


@unittest.skipIf(app is None, "web.py extra is not installed")
class TestAppWebpy(unittest.TestCase):

    def test_main(self):
        resp = app.request('/urlmatch')
        self.assertEqual(resp.status, '200 OK')
        self.assertEqual(
            resp.data,
            b'main page, count: 0, match: urlmatch')
        self.assertIn('Set-Cookie', resp.headers)

    def test_post(self):
        resp = app.request('/post/postmatch', method='POST', data='postinfo')
        self.assertEqual(resp.status, '200 OK')
        self.assertEqual(resp.data, b'8')

    def test_path(self):
        resp = app.request('/self/')
        self.assertEqual(resp.status, '200 OK')
        self.assertIn(b'httputil.py', resp.data)

