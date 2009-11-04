#!/usr/bin/env python
# encoding: utf-8

"""
Enumerate all cameras connected to the bus
"""

from pydc1394 import Camera, DC1394Library

print "All cameras on bus:"

l = DC1394Library()
cams = l.enumerate_cameras()
for c in cams:
    print c



