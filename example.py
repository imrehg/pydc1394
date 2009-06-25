#!/usr/bin/env python

from Dc1394 import Camera, DC1394Library
from UI import LiveCameraDisplay

l = DC1394Library()
cams = l.enumerate_cameras()
cam0_handle = cams[0]

cam0 = Camera(l, cam0_handle['guid'], mode = (800,600,"Y8"), framerate=15)

# This will start acquiring frames in the background, use this if you only
# need pictures occasionally and if you do not care if one image might be
# skipped in between
cam0.start(interactive=True)
print cam0.current_image # always the latest acquired image, a numpy array
cam0.stop()

# If you need continously images, use
cam0.start(interactive=False)
# and
cam0.shot() # returns a numpy array
# Note though that you need to process the images fast enough, otherwise the
# internal image queue will overrun.
cam0.stop()


