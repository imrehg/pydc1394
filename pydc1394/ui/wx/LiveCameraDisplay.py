#!/usr/bin/python
# encoding: utf-8
# (c) Copyright 2008 Holger Rapp. All Rights Reserved. 
# 
# HolgerRapp@gmx.net

from LiveImageDisplay import LiveImageDisplay, NewImageEvent
from threading import *
import wx

__all__ = [ "LiveCameraDisplay" ]

class _WorkerThread(Thread):
    def __init__(self,cam,ld):
        """
        This class keeps requesting images from the camera and displays them
        as fast as possible

        cam - camera 
        """
        Thread.__init__(self)
        
        self._ld = ld
        self._cam = cam
        
        self._should_abort = False
        self._abort_lock = Lock()

        self.start()
        
    def abort(self):
        self._abort_lock.acquire()
        self._should_abort = True
        self._abort_lock.release()
        
    def run(self):
        dobreak = False
        while self._cam.running:
            self._abort_lock.acquire()
            sa = self._should_abort
            self._abort_lock.release()
            if sa: break

            # Wait for a new camera picture
            self._cam.new_image.acquire()
            self._cam.new_image.wait(.25)
            if not self._cam.running:
                dobreak = True
            else:
                i = self._cam.current_image
            self._cam.new_image.release()
            
            if dobreak:
                wx.PostEvent(self._ld, wx.CloseEvent()) # we continue as normal, the ld will abort us
            elif self._ld:
                wx.PostEvent(self._ld, NewImageEvent(i))
          
            wx.Yield()

        # The parent window should close itself now

class LiveCameraDisplay(LiveImageDisplay):
    def __init__(self,cam,parent=None,id=-1,title=None,
        zoom = 1.0, pos = wx.DefaultPosition):
        """
        This class is a LiveImageDisplay which displays the picture from a
        camera image. It is mainly a LiveImageDisplay with a own grapper thread
        and is mainly usefull for interactive use from pylab/ipython. If you
        use it from within ipython/pylab make sure to close all windows prior
        to stopping the camera.
        """
        if title == None:
            title = "%s - %s (%s)" % (cam.vendor,cam.model,cam.guid)

        LiveImageDisplay.__init__( self,parent,id,title,
                cam.numpy_shape,cam.numpy_dtype,zoom,pos )
        
        
        # Well if the cam is not yet running, start it
        cam.start(interactive = True)
        
        self._worker = _WorkerThread(cam,self)
        
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        self.Bind(wx.EVT_IDLE,self.OnIdle)

        self.Show()

    def OnIdle(self,event):
        if not self._worker.isAlive():
            self.Close()

    def OnClose(self,event):
        if self._worker.isAlive():
            self._worker.abort()
            self._worker.join()
        self.Destroy()
        del self

