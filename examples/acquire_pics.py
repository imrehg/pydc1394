#!/usr/bin/env python
# encoding: utf-8

import time
import optparse

from pydc1394 import DC1394Library, Camera
from pydc1394.ui.qt import LiveCameraWin
from pydc1394.cmdline import add_common_options, handle_common_options


def main():
    p = optparse.OptionParser(usage="Usage: %prog [ options ]\n"
      "Acquires 25 pictures and exits.")

    add_common_options(p)

    options, args = p.parse_args()

    l = DC1394Library()
    cam = handle_common_options(options,l)

    if cam:
        print "Starting camera in normal mode. We need to process all pictures!"
        cam.start(interactive=False)

        print "Better be quick now! All images are saved in a Queue object, if we"
        print "are not fast enough in acquisition, the queue will overrun and"
        print "the program will crash."

        print "Acquiring 25 images"
        for idx in range(1,26):
            i = cam.shot()
            print "The last picture %i was acquired at: " % idx, i.timestamp

        cam.stop()

        print "All done."

main()


