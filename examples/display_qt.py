#!/usr/bin/env python
# encoding: utf-8

import sys
import optparse

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from pydc1394 import DC1394Library, Camera
from pydc1394.ui.qt import LiveCameraWin
from pydc1394.cmdline import add_common_options, handle_common_options


def main():
    p = optparse.OptionParser(usage="Usage: %prog [ options ]\n"
      "This program displays a live image of your camera")

    add_common_options(p)

    options, args = p.parse_args()

    l = DC1394Library()
    cam = handle_common_options(options,l)

    if cam:
        app = QApplication(args)
        w1 = LiveCameraWin(cam); w1.show(); w1.raise_()
        sys.exit(app.exec_())

main()

