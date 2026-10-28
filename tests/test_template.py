import unittest
from template import Template


class TestTemplate(unittest.TestCase):
    template = u'''<html><head><title>{%=r%}</title></head>
<body><table><tr><td>col1</td><td>col2</td></tr>
{%for i in objs:%}<tr><td>{%=i[0]%}</td><td>{%=i[1]%}</td></tr>
{%end%}</table></body></html>'''
    result = u'''<html><head><title>test</title></head>
<body><table><tr><td>col1</td><td>col2</td></tr>
<tr><td>1</td><td>2</td></tr>
<tr><td>3</td><td>4</td></tr>
</table></body></html>'''

    def test_render(self):
        t = Template(template=self.template)
        info = {u'r': u'test', u'objs': [(1, 2), (3, 4)]}
        self.assertEqual(t.render(info), self.result)

