#!/usr/bin/env python
# encoding: utf-8

from __future__ import division

"""
Common cmdline arguments for programs related to cameras
"""

import optparse

from camera import Camera

__all__ = [ "add_common_options", "handle_common_options" ]

def add_common_options(p):
    p.set_defaults(fps = None, mode = None, shutter=None, gain=None, guid=None)

    p.add_option("-l", "--list", action="store_true",
                 help="List all devices on the IEEE Bus")
    p.add_option("-c", "--cam", dest="guid", type="str",
                 help="Use the camera with the given GUID")
    p.add_option("-f", "--fps", dest="fps", type="float",
                 help="Use the given framerate")
    p.add_option("-s", "--shutter", dest="shutter", type="float",
                 help="Set the shutter (integration time) to this amount in ms")
    p.add_option("-g", "--gain", dest="gain", type="float",
                 help="Sets the gain to the given floating point value")


    return p

def handle_common_options(o, l):
    cams = l.enumerate_cameras()

    if o.list:
        def pprintf(a0, a1):
            print "   %s   %s" % (a0.center(20), str(a1).center(8))
        pprintf("GUID", "Unit No")
        for cam in cams:
            pprintf(cam['guid'], cam['unit'])
        return None

    guid = o.guid or cams[0]['guid']

    camera = Camera(l, guid=guid, mode=o.mode, framerate=o.fps,
                    shutter=o.shutter, gain=o.gain)

    return camera
