#!/usr/bin/env python -tt
# encoding: utf-8

import nose
from nose.tools import *

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir))

from camera import DC1394Library

def test_libcreation():
    l = DC1394Library()

def test_libclosing():
    l = DC1394Library()
    l.close()

