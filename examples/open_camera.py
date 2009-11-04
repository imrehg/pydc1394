#!/usr/bin/env python
# encoding: utf-8

from pydc1394 import DC1394Library, Camera

l = DC1394Library()
cams = l.enumerate_cameras()
cam0_handle = cams[0]

print "Opening camera!"
cam0 = Camera(l, cam0_handle['guid'])

print "Vendor:", cam0.vendor
print "Model:", cam0.model
print "GUID:", cam0.guid
print "Mode:", cam0.mode
print "Framerate: ", cam0.framerate.val

print "Acquiring one frame!"
cam0.start()
i = cam0.shot()
print "Shape:", i.shape
print "Dtype:", i.dtype
cam0.stop()

print "All done!"
