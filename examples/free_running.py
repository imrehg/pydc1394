#!/usr/bin/env python
# encoding: utf-8

import time
import optparse

from pydc1394 import DC1394Library, Camera
from pydc1394.ui.qt import LiveCameraWin
from pydc1394.cmdline import add_common_options, handle_common_options


def main():
    p = optparse.OptionParser(usage="Usage: %prog [ options ]\n"
      "This program lets the camera run in free running mode.")

    add_common_options(p)

    options, args = p.parse_args()

    l = DC1394Library()
    cam = handle_common_options(options,l)

    if cam:
        print "Starting camera in free running mode!"
        cam.start(interactive=True)

        print "We can now do whatever we want, the camera is acquiring"
        print "frames in the background in another thread. Let's sleep a while"
        for i in range(10,-1,-1):
            print i
            time.sleep(1)
            print "The last picture was acquired at: ", cam.current_image.timestamp

        cam.stop()

        print "All done."

main()


