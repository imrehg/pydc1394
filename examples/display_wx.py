#!/usr/bin/env python
# encoding: utf-8

"""
Display an image using wxPython and PyOpenGL

Example contributed by Peter Liebetraut, modified
by Holger Rapp.
"""
import sys
import optparse

import wx

from pydc1394 import DC1394Library, Camera
from pydc1394.ui.wx import LiveCameraDisplay
from pydc1394.cmdline import add_common_options, handle_common_options

def main():
    p = optparse.OptionParser(usage="Usage: %prog [ options ]\n"
      "This program displays a live image of your camera")

    add_common_options(p)

    options, args = p.parse_args()

    l = DC1394Library()
    cam = handle_common_options(options,l)

    if cam:
        app = wx.PySimpleApp()
        LiveCameraDisplay(cam)
        app.MainLoop()

main()

