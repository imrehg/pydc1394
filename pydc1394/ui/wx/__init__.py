#!/usr/bin/python

_has_wx = False
try:
    import wx
    _has_wx = True
except ImportError:
    import warnings
    warnings.warn("This module needs wxPython!")

if _has_wx:
    from LiveImageDisplay import *
    from LiveCameraDisplay import *


