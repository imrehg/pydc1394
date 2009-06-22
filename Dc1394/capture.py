#!/usr/bin/env python
# encoding: utf-8

from numpy import *

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
