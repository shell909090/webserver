#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2016-08-24
@author: Shell.Xu
@copyright: 2016, Shell.Xu <shell909090@gmail.com>
@license: BSD-3-clause
'''
from __future__ import absolute_import, division,\
    print_function, unicode_literals
import unittest
from apps import TestApp
try:
    from app_webpy import TestAppWebpy
except ImportError:
    pass # maybe no web.py
from client import TestClient
from midware import TestHeap
from template import TestTemplate


if __name__ == '__main__':
    unittest.main()
