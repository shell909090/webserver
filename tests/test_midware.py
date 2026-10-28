import unittest
import time
from midware import ObjHeap, MemoryCache


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

