#!/usr/bin/env python
# encoding: utf-8

_has_qt = False
try:
    import PyQt4
    _has_qt = True
except ImportError:
    import warnings
    warnings.warn("This module needs PyQt4!")

if _has_qt:
    from display import *

