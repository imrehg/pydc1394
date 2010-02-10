#!/usr/bin/env python -tt
# encoding: utf-8
#
# File: capture.py
#
# Created by Holger Rapp on 2008-08-01.
# Copyright (c) 2008 HolgerRapp@gmx.net. All rights reserved.

from numpy import *

# import PyQt4.QtCore

def caputure(nframes, cam0, cam1 ):

    a1 = empty( (nframes,480,640), dtype="u1")
    a2 = empty( (nframes,480,640), dtype="u1")

    cam0.start(); cam1.start()

    ldiff = 100000000
    while 1:
        k,t1 = cam0.shot()
        k,t2 = cam1.shot()
        diff = abs(t1-t2)
        if diff > ldiff:
            break
        ldiff = diff
        cam0.shot()
    cam1.shot()

    for i in xrange(nframes):
        a1[i],t1 = cam0.shot()
        a2[i],t2 = cam1.shot()
        print t1-t2

    cam0.stop(); cam1.stop()

    return a1, a2

if __name__ == '__main__':
    import sys
    import time

    from camera import Camera, DC1394Library

    def main():
        l = DC1394Library()
        guid = l.enumerate_cameras()[0]['guid']

        cam = Camera(l, guid=guid, mode=(640, 480, "Y8"), framerate=60.)


        n = 1000
        print "Acquiring %i frame ... " % n
        cam.start()
        t = time.time()
        for i in xrange(n):
            i = cam.shot()
        rtime = time.time() - t
        cam.stop()

        fps = n/rtime
        print "fps: %s" % (fps)

    main()


