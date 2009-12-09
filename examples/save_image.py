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
cam0.brightness.mode = 'auto'
cam0.exposure.mode = 'auto'
cam0.white_balance.mode = 'auto'


for feat in cam0.features:
    cmd = "print feat  , cam0." + str(feat) +".val"
    print cmd
    exec(cmd)

cam0.mode = (640, 480, 'RGB8')
if len(sys.argv) > 1:
    cam0.start(interactive=False)
    matrix = cam0.shot()
    cam0.stop()
else:
    cam0.start(interactive=True)
    sleep(0.5)
    matrix = cam0.current_image
    cam0.stop()
print "Shape:", matrix.shape
#Image.fromstring("RGB", (480, 640), im, "raw").save("t.bmp")
#Image.fromstring("RGB", (640, 480), im, "raw").save("t.bmp")
Image.fromstring("RGB", (640, 480), matrix, "raw").save("t.bmp")
import os
os.system("eog t.bmp")

