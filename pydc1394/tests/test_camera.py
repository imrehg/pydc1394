#!/usr/bin/env python -tt
# encoding: utf-8
#
# This file is part of pydc1394.
#
# pydc1394 is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# pydc1394 is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with pydc1394.  If not, see
# <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2009, 2010 by Holger Rapp <HolgerRapp@gmx.net>
# and the pydc1394 contributors (see README File)


import nose
from nose.tools import *
from nose.plugins.attrib import attr

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir))

from camera import DC1394Library, Camera, CameraError

# Is a camera connected?
def _has_cam_attached():
    l = DC1394Library()
    if len(l.enumerate_cameras()):
        return True
    return False
_has_camera = _has_cam_attached()

def need_cam(f):
    def skipper(*args, **kwargs):
        if not _has_camera:
            raise nose.SkipTest, "This test needs a camera attached!"
        else:
            return f(*args, **kwargs)
    return nose.tools.make_decorator(f)(skipper)

class LibBase(object):
    @need_cam
    def setUp(self):
        self.l = DC1394Library()
    @need_cam
    def tearDown(self):
        self.l.close()
class CamBase(LibBase):
    @need_cam
    def setUp(self):
        LibBase.setUp(self)
        cams = self.l.enumerate_cameras()
        self.c = Camera(self.l, cams[0]['guid'])
    @need_cam
    def tearDown(self):
        self.c.stop()
        self.c.close()
        LibBase.tearDown(self)

# Camera opening and closing
class TestInstantiation(LibBase):
    @need_cam
    def test(self):
        cams = self.l.enumerate_cameras()
        c = Camera(self.l, cams[0]['guid'])
        c.close()

    @need_cam
    @raises(CameraError)
    def test_failure(self):
        Camera(self.l, "deadbeef")

    @need_cam
    @raises(CameraError)
    def test_invalid_mode(self):
        cams = self.l.enumerate_cameras()
        c = Camera(self.l, cams[0]['guid'], mode=(23323,232323,"Y16"))
        c.close()

    @need_cam
    @raises(CameraError)
    def test_invalid_isospeed(self):
        cams = self.l.enumerate_cameras()
        c = Camera(self.l, cams[0]['guid'], isospeed=12393)
        c.start()
        c.shot()
        c.stop()
        c.close()

# From now on, we assume that we can get a camera instance
class TestCamera(CamBase):
    @need_cam
    def test_acquisition(self):
        self.c.start()
        i = self.c.shot()
        eq_(i.shape[0], self.c.mode[1])
        eq_(i.shape[1], self.c.mode[0])
        self.c.stop()

    @need_cam
    @attr('slow')
    def test_reset(self):
        self.c.start()
        self.c.reset_bus()

        eq_(self.c.running, False)

        self.c.start()
        self.c.shot()
        self.c.stop()


    @need_cam
    def test_manual_shutter_time_setting(self):
        try:
            self.c.shutter.mode = 'manual'
            smin, smax = self.c.shutter.range
            val = smin + (smax-smin)/2.
            self.c.shutter.val = val
            assert_almost_equal(self.c.shutter.val, val, 1)
        except AttributeError:
            pass # Maybe camera does not support this




