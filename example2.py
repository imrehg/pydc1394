#!/usr/bin/env python
# encoding: utf-8

"""
Display an image using wxPython and PyOpenGL

Example contributed by Peter Liebetraut
"""

import wx
app = wx.PySimpleApp()

from Dc1394 import Camera, DC1394Library
from UI import LiveCameraDisplay
l = DC1394Library()
cams = l.enumerate_cameras()
cam0_handle = cams[0]
cam0 = Camera(l, cam0_handle['guid'], mode = (800,600,"Y8"), framerate=15)
LiveCameraDisplay(cam0)

app.MainLoop()

