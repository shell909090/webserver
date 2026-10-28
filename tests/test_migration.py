import io
import tempfile
import unittest
from pathlib import Path

import httputil
import midware
import serve
from template import Template


class TestMigration(unittest.TestCase):
    def test_upload_unicode(self):
        stream = io.BytesIO()
        upload = httputil.RequestWriteFile(stream)
        upload.write("你好")
        upload.close()
        self.assertEqual(stream.getvalue(), b"6\r\n" + "你好".encode() + b"\r\n0\r\n\r\n")

    def test_template_include(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "part.html"
            file.write_text("你好 {%=name%}", encoding="utf-8")
            template = Template(template="{%include " + str(file) + "%}")
            self.assertEqual(template.render({"name": "world"}), "你好 world")

    def test_heap_iteration(self):
        heap = midware.ObjHeap(2)
        heap[1] = 10
        self.assertEqual(list(heap), [1])

    def test_response_truth(self):
        response = httputil.Response.create(200)
        response.keepalive = False
        self.assertFalse(response)

    def test_form(self):
        request = httputil.Request.create("/", body="text=%E4%BD%A0%E5%A5%BD&empty=")
        self.assertEqual(request.readform(), {"text": "你好", "empty": ""})

    def test_config(self):
        self.assertEqual(serve.getcfg(["serve.conf"]).get("server", "server"), "thread")
