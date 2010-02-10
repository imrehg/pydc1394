#!/usr/bin/env python

import sys
from time import sleep
from pydc1394 import DC1394Library, Camera
import Image

l = DC1394Library()
cams = l.enumerate_cameras()
cam0_handle = cams[0]

print "Opening camera!"
cam0 = Camera(l, cam0_handle['guid'])

print "Vendor:", cam0.vendor
print "Model:", cam0.model
print "GUID:", cam0.guid
print "Mode:", cam0.mode
print "Framerate: ", cam0.fps
print "Available modes", cam0.modes
print "Available features", cam0.features

#those can be automated, the other are manual
try:
    cam0.brightness.mode = 'auto'
    cam0.exposure.mode = 'auto'
    cam0.white_balance.mode = 'auto'
except AttributeError: # thrown if the camera misses one of the features
    pass


for feat in cam0.features:
    print "%s (cam0): %s" % (feat,cam0.__getattribute__(feat).val)

#choose color mode
print cam0.modes
cam0.mode = cam0.modes[0]

if len(sys.argv) > 1:
    cam0.start(interactive=False)
    sleep(0.5) #let hardware start !
    matrix = cam0.shot()
    cam0.stop()
else:
    cam0.start(interactive=True)
    sleep(0.5) #let hardware start !
    matrix = cam0.current_image
    cam0.stop()

print "Shape:", matrix.shape
i = Image.fromarray(matrix)
i.save("t.bmp")

i.show()

