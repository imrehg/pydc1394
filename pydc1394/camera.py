#!/usr/bin/env python
# encoding: utf-8
#
# File: camera.py
#
# Created by Holger Rapp on 2008-07-26.
# Copyright (c) 2008 HolgerRapp@gmx.net. All rights reserved.

from _dc1394core import *
from _dc1394core import _dll
from ctypes import *


from numpy import fromstring, ndarray
from threading import *

from Queue import Queue, Full

__all__ = [ "DC1394Library", "Camera", "SynchronizedCams" ]

class DC1394Library(object):
    """
    This wraps the dc1394 library object which is a nuisance to have
    around. This is bad design on behalve of DC1394. Oh well...  This
    object must stay valid untill all cameras are closed
    But then use it well: it not only opens the library, collects 
    a reference to the library and the camera list.

    h:				a handler of the library, many functions require it

    cameralist:		a list of dicts. Each camera has a dict, containing:
            "unit":		the unit ID of the camera
            "guid":		GUID -> requested for the camera allocation
            "vendor":	vendor name
            "model" :	model name
                        Using this list the user may identify the camera and
                        pass cameralist[i]['guid'] to the Camera class below.

        close():	frees up the library
        enumerate_cameras():	reinitializes the camera list
    """
    def __init__( self ):
        # we cache the dll, so it gets not deleted before we cleanup
        self._dll = _dll 
        self._h = _dll.dc1394_new()
        self.cameralist = self.enumerate_cameras()
    #end of __init__

    def __del__(self):
        self.close()
    #end of __del__

    @property
    def h(self):
        "The handle to the library context."
        return self._h

    ###################################################################
    # Functions:
    ###################################################################

    def close( self ):
        if self._h is not None:
            self._dll.dc1394_free( self._h )
        self._h = None
        self.cameralist = []
    #end of close

    def enumerate_cameras( self ):
        """
        Enumerate the cameras currently attached to the bus. Only
        returns guid.
        """
        l = POINTER(camera_list_t)()
        
        _dll.dc1394_camera_enumerate(self.h, byref(l))

        #cams -> clist renamed for using cam as a camera
        clist = []
        for i in xrange(l.contents.num):
            ids = l.contents.ids[i]
            #we can be nice to the users, providing some more
            #than mere GUID and unitIDs
            #also, if this fails, we have a problem:
            cam = self._dll.dc1394_camera_new(self.h, ids.guid)
            
            #it seems not all cameras have these fields:
            vendor = cam.contents.vendor if cam.contents.vendor else "unknown"
            model = cam.contents.model if cam.contents.model else "unknown"

            clist.append(
                { "unit": ids.unit,
                    # For what do we need this L anyway?!?!
                  #"guid": hex(ids.guid)[2:].strip("L"),
                  "guid": ids.guid,
                  "vendor":	vendor,
                  "model":	model,
                }
            )

            self._dll.dc1394_camera_free(cam)
        #end for
        _dll.dc1394_camera_free_list(l)

        return clist
    #end enumerate_cameras
#end class Dc1394Library


class Image(ndarray):
    """
    This class is a image returned by the camera. It is basically a
    numpy array with some additional informations (like timestamps)

    Based on the video_frame structure of the dc1394 library ???

    """
    @property
    def position(self):
        "ROI position (offset)"
        return self._position
    @property
    def packet_size(self):
        "The size of a datapacket in bytes."
        return self._packet_size
    @property
    def packets_per_frame(self):
        "Number of packets per frame."
        return self._packets_per_frame
    @property
    def timestamp(self):
        "The IEEE Bustime when the picture was acquired (microseconds)"
        return self._timestamp
    @property
    def frames_behind(self):
        "the number of frames in the ring buffer that are yet to be accessed by the user"
        return self._frames_behind
    @property
    def id(self):
        "the frame position in the ring buffer"
        return self._id
    # TODO add here:
    # depth -> number of bits/pixel in the image
    # endianness or bytes are swapped bool (framge -> little_endian == False)

#end of class Image

class _CamAcquisitonThread(Thread):
    def __init__(self,cam, condition ):
        """
        This class is created and launched whenever a camera is start()ed.
        It continously acquires the pictures from the camera and sets a
        condition to inform other threads of the arrival of a new picture
        """
        Thread.__init__(self)

        self._cam = cam
        self._should_abort = False

        self._last_frame = None
        self._condition = condition

        #create a lock object from the threading module; see LockType.__doc__
        self._abortLock = Lock()

        self.start()

    def abort(self):
        self._abortLock.acquire()
        self._should_abort = True
        self._abortLock.release()

    def run(self):
        """
        Core function which contains the acquisition loop
        """

        while 1:
            self._abortLock.acquire()
            sa = self._should_abort
            self._abortLock.release()

            if sa:
                break

            if self._last_frame:
                self._cam._dll.dc1394_capture_enqueue( self._cam._cam, self._last_frame )

            frame = POINTER(video_frame_t)()
            self._cam._dll.dc1394_capture_dequeue(self._cam._cam, CAPTURE_POLICY_WAIT, byref(frame));

            Dtype = c_char*frame.contents.image_bytes
            buf = Dtype.from_address(frame.contents.image)


            self._last_frame = frame

            self._condition.acquire()
            img = fromstring(buf, dtype=self._cam._dtype).reshape(self._cam._shape).view(Image)
            img._position,img._packet_size, img._packets_per_frame, img._timestamp, img._frames_behind, \
                    img._id = frame.contents.position, frame.contents.packet_size, frame.contents.packets_per_frame, \
                              frame.contents.timestamp, frame.contents.frames_behind,frame.contents.id
            self._cam._current_img = img
            if self._cam._queue:
                self._cam._queue.put_nowait(img) # This will throw an exception if you are to slow while processing

            self._condition.notifyAll()
            self._condition.release()

        # Return the last frame
        if self._last_frame:
            self._cam._dll.dc1394_capture_enqueue( self._cam._cam, self._last_frame )
        self._last_frame = None
#end of class _CamAcquisitonThread


class CameraProperty(object):
    def __init__( self, cam, name, id, absolute_capable ):
        """This class implements a simple Property of the camera"""
        self._id = id
        self._name = name
        self._absolute_capable = absolute_capable
        self._dll = cam._dll
        self._cam = cam
    #end __init__

    #Other properties:
    def val():
        doc = "The current value of this property"
        def fget(self):
            if self._name == "white_balance":
                #white has its own call since it returns 2 values
                blue = c_uint32()
                red = c_uint32()
                self._dll.dc1394_feature_whitebalance_get_value(
                    self._cam._cam, byref(blue), byref(red)
                )
                return (blue.value, red.value)
            #end if
            
            #else:
            if self._absolute_capable:
                val = c_float()
                self._dll.dc1394_feature_get_absolute_value( self._cam._cam, self._id, byref(val))

                if self._name == "shutter" :
                    # We want shutter in ms -> if it is absolute capable.
                    val.value *= 1000.
                #end if self.name

            else:
                val = c_uint32()
                self._dll.dc1394_feature_get_value( self._cam._cam, self._id, byref(val))
            #end if
            return val.value
        #end fget

        def fset(self, value):
            if self._name == "white_balance":
                #white has its own call since it returns 2 values
                blue, red = value
                self._dll.dc1394_feature_whitebalance_set_value( self._cam._cam, blue, red )

            else:

                if self._absolute_capable:
                    val = float(value)
                    # We want shutter in ms
                    if self._name == "shutter":
                        value /= 1000.
                    #end if name

                    self._dll.dc1394_feature_set_absolute_value( self._cam._cam, self._id, val)

                else:
                    val = int(value)
                    self._dll.dc1394_feature_set_value( self._cam._cam, self._id, val)
                #end if
            #end fset
        return locals()
    #end def val
    val = property(**val())

    @property
    def range(self):
        "The RO foo property."
        if self._absolute_capable:
            min, max = c_float(), c_float()
            self._dll.dc1394_feature_get_absolute_boundaries( self._cam._cam,\
                                                self._id, byref(min),byref(max))
            # We want shutter in ms
            if self._name == "shutter":
                min.value *=1000
                max.value *=1000
            #end if name
        else:
            min, max = c_uint32(), c_uint32()
            self._dll.dc1394_feature_get_boundaries( self._cam._cam, self._id, byref(min),byref(max))
        #end if absolute_capable

        return (min.value,max.value)
    #end range

    @property
    def can_be_disabled(self):
        "Can this property be disabled"
        k = bool_t()
        self._dll.dc1394_feature_is_switchable(self._cam._cam, self._id, byref(k))
        return bool(k.value)
    #end of can_be_disabled => on/off capable

    def on():
        doc = """\
        Toggle this feature on and off;
        For the trigger this means the external trigger ON/OFF"""

        def fget(self):
            k = bool_t()
            if self._name.lower() == "trigger":
                self._dll.dc1394_external_trigger_get_power(self._cam._cam, byref(k))
            else:
                self._dll.dc1394_feature_get_power( self._cam._cam, self._id, byref(k))
            return bool(k.value)
        #end fget

        def fset(self, value):
            k = bool(value)
            if self._name.lower() == "trigger":
                self._dll.dc1394_external_trigger_set_power(self._cam._cam, k)
            else :
                self._dll.dc1394_feature_set_power( self._cam._cam, self._id, k)
            #end if
        return locals()
    on = property(**on())
    #end self.on

    @property
    def pos_modes(self):
        "The possible control modes for this feature (auto,manual,...)"
        if self._name.lower() == "trigger":
            #we need a trick:
            finfo = feature_info_t()
            finfo.id = self._id
            _dll.dc1394_feature_get( self._cam._cam,  byref(finfo) )
            modes = finfo.trigger_modes

            return [ trigger_mode_vals[ modes.modes[i]] for i in xrange(modes.num)]
        #end if; else:
        modes = feature_modes_t()
        _dll.dc1394_feature_get_modes(self._cam._cam, self._id, byref(modes))
        return [ feature_mode_vals[modes.modes[i]] for i in xrange(modes.num) ]
    #end pos_modes

    def mode():
        doc = "The current control mode this feature is running in"
        def fget(self):
            if self._name.lower() == "trigger":
                mode = trigger_mode_t()
                _dll.dc1394_external_trigger_get_mode( self._cam._cam, byref(mode))
                return trigger_mode_vals[ mode.value ]
            #end if; else:

            mode = feature_mode_t()
            _dll.dc1394_feature_get_mode(self._cam._cam, self._id, byref(mode))
            return feature_mode_vals[mode.value]
        #end of fget

        def fset(self, value):
            if self._name.lower() == "trigger":
                if trigger_mode_codes.has_key( value ):
                    key = trigger_mode_codes[ value ]
                    _dll.dc1394_external_trigger_set_mode(self._cam._cam, key)
                else:
                    print "invalud external trigger mode: %s" %value
                #end if
            #end if
            if feature_mode_codes.has_key( value ):
                key = feature_mode_codes[ value ]
                _dll.dc1394_feature_set_mode(self._cam._cam, self._id,key )
            else:
                print "Invalid feature mode: %s" %value
            #end if
        return locals()
    mode = property(**mode())
    #end of mode

#end of common CameraProperty
#these properties work only for the trigger, but there they are needed
#class Trigger(CamProperty):
    def polarity_capable(self):
        "Any use of polarity?"
        finfo = feature_info_t()
        finfo.id = self._id
        _dll.dc1394_feature_get( self._cam._cam,  byref(finfo) )
        #polarity_capable is an bool_t = int field:
        return bool( finfo.polarity_capable )
    #end of can_be_disabled => on/off capable

    def polarity():
        doc = "Which polarity matters for the external trigger"
        def fget(self):
            pol = trigger_polarity_t()
            _dll.dc1394_external_trigger_get_polarity( self._cam._cam, byref(pol))
            if trigger_polarity_vals.has_key( pol.value ):
                return trigger_polarity_vals[ pol.value ]
            else :
                return pol.value
        #end fget

        def fset(self, pol):
            if self.polarity_capable:
                if trigger_polarity_codes.has_key( pol ):
                    key = trigger_polarity_codes[ pol ]
                    _dll.dc1394_external_trigger_set_polarity( self._cam._cam, key )
                else:
                    print "Invalid external trigger polarity: %s" %pol
                #end if
        #end fset
        return locals()
    polarity = property( **polarity())
    #end polarity
    
    def pos_polarities(self):
        return trigger_polarity_codes.keys()
    #end pos_polarities

    def source():
        doc = "Actual source of the external trigger"
        def fget(self):
            source = trigger_source_t()
            _dll.dc1394_external_trigger_get_source(self._cam._cam, byref(source))
            return trigger_source_vals[ source.value ]
        #end of fget

        def fset(self, source):
            if trigger_source_codes.has_key( source ):
                key = trigger_source_codes[ source ]
                _dll.dc1394_external_trigger_set_source(self._cam._cam, key)
            else:
                print "Invalid external trigger source: %s" %source
        #end fset
        return locals()
    source = property( **source())
    #end of source

    def pos_sources(self):
        """ List the possible external trigger sources of the camera"""
        src = trigger_sources_t()
        _dll.dc1394_external_trigger_get_supported_sources(self._cam._cam, byref(src))
        return [ trigger_source_vals[src.sources[i]] for i in xrange(src.num) ]
    #end of pos_sources

    def software_trigger():
        doc = "Set and get if the software trigger is active"
        def fget(self):
            res = switch_t()
            _dll.dc1394_software_trigger_get_power(self._cam._cam, byref(res))
            return bool( res.value )
        #end of fget
        def fset(self, value):
            k = bool(value)
            _dll.dc1394_software_trigger_set_power(self._cam._cam, k)
        #end fset
        return locals()
    software_trigger = property( **software_trigger() )
    #end of software_trigger

#end Trigger

#end of CameraProperty

class Camera(object):
    def __init__( self, lib, guid, mode = None, framerate = None, isospeed = 400, **feat):
        """
        This class represents a IEEE1394 Camera on the BUS. It currently
        supports all features of the cameras except white balancing.

        You can pass all features the camera supports as additional arguments
        to this classes constructor.  For example: shutter = 7.4, gain = 8

        The cameras pictures can be accessed in two ways. Either way, use
        start() to beginn the capture.  If you are always interested in the
        latest picture use the new_image Condition, wait for it, then use
        cam.current_image for your processing. This mode is called interactive
        because it is used in live displays.  An alternative way is to use
        shot() which gurantees to deliver all pictures the camera acquires
        in the correct order. Note though that you have to process these
        pictures with a certain speed, otherwise the caching queue will
        overrun. This mode is called serial. Note that you can theoretically
        also use the first acquisition mode here, but this seldom makes
        sense since you need a processing of the pictures anyway.

        lib       - the DC1394Library object is needed to open a camera
        guid      - GUID of this camera, can be a hexstring or the integer
                    value
        mode      - acquisition mode, e.g. (640, 480, "Y8"). If you pass None,
                    the first supported mode will be selected.
        framerate - wanted framerate, if you pass None, the slowest supported
                    will be selected.
        isospeed  - wanted isospeed, you might want to use 800 if your bus
                    supports it
        """
        self._lib = lib
        if isinstance(guid,basestring):
            guid = int(guid,16)
        #end if

        self._guid = guid
        self._cam = None
        #it is the same as _dll anyway...
        self._dll = lib._dll

        self._running = False
        self._running_lock = Lock()

        # For image acquisition
        self._new_image = Condition()
        self._current_img = None
        self._worker = None
        #a default numeric image type
        self._dtype = '<u1'

        self.open()

        # Gather some informations about this camera
        # Will also set the properties accordingly
        self._all_features = self.__get_all_features()
        self._all_modes = self.__get_supported_modes()

        # Set all features to manual (if possible)
        for f in self._all_features:
            if 'manual' in self.__getattribute__(f).pos_modes:
                self.__getattribute__(f).mode = 'manual'

        # Set acquisition mode and framerate
        self.mode = mode if mode is not None else self._all_modes[0]
        self.fps = framerate = framerate or \
                self.get_framerates_for_mode(self.mode)[0]

        # Convert framerate
        if framerate_codes.has_key( framerate ):
            self._wanted_frate = framerate_codes[ framerate ]
        else:
            print "Unknown framerate %s" %framerate
        #end if

        # Set isospeed
        if speed_codes.has_key( isospeed ):
            self._wanted_speed = speed_codes[ isospeed ]
        else :
            print "Unknown isospeed: %d" %isospeed
        #end if

        # If we are not using a FORMAT_7 format, set the framerate feature to auto
        # again. This control is not available on all cameras, if it is missing,
        # the framerate is only controllable by the current mode
        try:
            self.framerate.mode = "auto"
        except AttributeError:
            pass # Feature not around, so what?

        # If the speed is >= 800, set other operation mode
        self._operation_mode = "legacy" if isospeed < 800 else "1394b"

        # Set other parameters
        for n,v in feat.items():
            if v is None:
                continue
            self.__getattribute__(n).val = v
    #end __init__

    def __del__(self):
        self.close()

    def start( self, bufsize = 4, interactive = False ):
        """
        Start the camera in free running acquisition

        bufsize - how many DMA buffers should be used? If this value is high, the
                  lag between your currently processed picture and reality might
                  be higher but your risk to miss a frame is also much lower.
        interactive - If this is true, shot() is not supported and no queue overrun can occure
        """
        if self.running:
            return

        if not self._cam:
            raise RuntimeError, "The camera is not opened!"

        # Set video mode and everything
        self._dll.dc1394_video_set_iso_speed( self._cam, self._wanted_speed )
        self._dll.dc1394_video_set_mode( self._cam, self._wanted_mode )
        self._dll.dc1394_video_set_framerate( self._cam, self._wanted_frate )
        self._dll.dc1394_capture_setup( self._cam, bufsize, capture_flag_codes["CAPTURE_FLAGS_DEFAULT"])

        # Start the acquisition
        self._dll.dc1394_video_set_transmission( self._cam, 1 )

        self._queue = None if interactive else Queue(1000)

        # Now, start the Worker thread
        self._worker = _CamAcquisitonThread( self, self.new_image )

        self._running_lock.acquire()
        self._running = True
        self._running_lock.release()
    #end start

    def stop( self ):
        """Stop the camera and return all frames to the driver"""

        if not self.running:
            return

        assert(self._cam) # Otherwise it couldn't be running
        self._worker.abort()
        self._worker.join()

        self._queue = None

        self._dll.dc1394_capture_stop( self._cam )
        self._dll.dc1394_video_set_transmission( self._cam, 0 )

        self._running_lock.acquire()
        self._running = False
        self._running_lock.release()
    #end stop

    def reset_bus( self ):
        """ This is a rude way, forces all cameras on the bus to
            re-enumerate
        """
        if self.running:
            self.stop()

        self._dll.dc1394_reset_bus( self._cam )
    #end reset_bus

    def shot( self ):
        """
        If the camera is running, this will acquire one frame from it and
        return it as a Image (numpy array + some informations).The memory is
        not copied, therefore you should not write on the array.

        Note that acquisition is always running in the background. This function
        alone is guaranteed to return all frames in running order. Use this
        function for your image processing, use cam.current_image for
        visualisation.
        """
        if not self.running:
            raise RuntimeError, "Camera is not running!"
        if not self._queue:
            raise RuntimeError, "Camera is running in interactive mode!"

        return self._queue.get()
    #end shot

    def open( self ):
        """Open the camera"""
        self._cam = _dll.dc1394_camera_new( self._lib.h, self._guid )
        if not self._cam:
            raise RuntimeError, "Couldn't access camera!"
    #end open

    def close(self):
        """Close the camera. Stops it, if it was running"""
        if self.running:
            self.stop()

        if self._cam:
            _dll.dc1394_camera_free( self._cam )
            self._cam = None
    #end close

    def program_format7_mode( self, slot, offset = (0,0), mode = (640,480,"Y8")):
        """
        Program a given Format 7 slot (0 = FORMAT7_0) with the given parameters.
        The package size is always the maximum available. The framerate can
        then only be controlled through the framerate property (if available).
        This also implicitly sets the correct mode for format 7.

        If you change the mode to a normal one and want your format 7 mode again, you
        have to recall this function. The behaviour otherwise is undefined.

        slot   - 0,1,2 FORMAT7 Slot to program
        offset - picture offset (for ROI)
        mode   - Resolution and data depth is extracted. A valid mode would be
                 (121,99,"RGB")
        """
        if self.running:
            raise RuntimeError, "Can't set Format7 mode while camera is running!"

        #uslot, = [ k for k,v in video_mode_vals.items() if v == "FORMAT7_%i" % slot ]
        #Now we have an inverse dict:
        newmode = "FORMAT7_%i" %slot

        if video_mode_codes.has_key( newmode ):
            uslot = video_mode_codes[ newmode ]

        else :
            print "Available modes:"
            print filter( lambda x: "FORMAT7" in x, video_mode_codes.keys())

            return
        #end if

        #cco, = [ k for k,v in color_coding_vals.items() if v == mode[-1] ]
        
        if color_coding_codes.has_key( mode[-1] ):
            cco = color_coding_codes[ mode[-1] ]
        else:
            cco = None
        #end if

        self._dll.dc1394_format7_set_roi(
            self._cam, uslot,
            cco, USE_MAX_AVAIL,
            offset[0], offset[1],
            mode[0],mode[1])

        #this invokes the standard mode setting part, which will
        #set FORMAT7 modes with 0,0 resolution.
        self.mode = newmode

        # But directly overwrite the shape
        self._shape = [ mode[1], mode[0] ]
        if mode[-1] == 'Y8':
            self._dtype = '>u1'
        elif mode[-1] == 'Y16':
            self._dtype = '>u2'
        elif mode[-1] == 'RGB':
            self._dtype = '>u1'
            self._shape.append( 3 )

    #end program_format7_mode

    ###########################################################################
    #                     INFORMATION GATERHING FUNCTIONS                     #
    ###########################################################################
    def __get_supported_modes( self ):
        if not self._cam:
            raise RuntimeError, "The camera is not opened!"

        modes = video_modes_t()
        supmodes = []
        _dll.dc1394_video_get_supported_modes( self._cam, byref(modes))
        for i in range(modes.num):
            supmodes.append( video_mode_vals[modes.modes[i]] )
        return supmodes

    def __get_all_features( self ):
        if not self._cam:
            raise RuntimeError, "The camera is not opened!"

        fs = featureset_t()
        _dll.dc1394_feature_get_all( self._cam, byref(fs) )


        self._features = []

        # We set all features that are capabale of it to absolute values
        for i in range(FEATURE_NUM):
            s = fs.feature[i]
            if s.available:
                if s.absolute_capable:
                    _dll.dc1394_feature_set_absolute_control( self._cam, s.id, 1 )
                name = feature_vals[s.id]
                self._features.append( name )
                self.__dict__[name] = CameraProperty( self, name, s.id, s.absolute_capable)

        return self._features

    def get_register( self, offset ):
        """Get the control register value of the camera a the given offset"""
        if not self._cam:
            raise RuntimeError, "The camera is not opened!"

        val = c_uint32()
        _dll.dc1394_get_control_registers( self._cam, offset, byref(val), 1)
        return val.value
    def set_register( self, offset, value ):
        """Set the control register value of the camera at the given offset to
        the given value"""
        if not self._cam:
            raise RuntimeError, "The camera is not opened!"

        val = c_uint32(value)
        _dll.dc1394_set_control_registers( self._cam, offset, byref(val), 1)

    ###########################################################################
    #                               PROPERTIES                                #
    ###########################################################################
    def broadcast():
        doc = \
        """
        This sets if the camera tries to synchronize with other cameras on the
        bus. Note that behaviour might be strange if one camera tries to
        broadcast and another not. Note also that this feature is currently only
        supported under linux and I have not seen it working yet though I tried it
        with cameras that should support it. So use on your own risk!
        """
        def fget(self):
            if not self._cam:
                raise RuntimeError, "The camera is not opened!"

            k = bool_t()
            self._dll.dc1394_camera_get_broadcast( self._cam, byref(k))
            if k.value == 1:
                return True
            else:
                return False
        def fset(self, value):
            if not self._cam:
                raise RuntimeError, "The camera is not opened!"

            use =  1 if value else 0
            self._dll.dc1394_camera_set_broadcast( self._cam, use )
        return locals()
    broadcast = property(**broadcast())

    @property
    def current_image(self):
        "The current image of the camera. Threadsafe access to the current image."
        # We do proper locking
        self._new_image.acquire()
        self._new_image.wait()
        i = self._current_img
        self._new_image.release()
        return i
    @property
    def new_image(self):
        "The Condition to wait for when you want a new Image"
        return self._new_image

    @property
    def numpy_shape(self):
        """
        This returns the shape the camera currently delivers. It is useful
        if you want to create a matching numpy array
        """
        return self._shape
    @property
    def numpy_dtype(self):
        """
        This returns the datatype the camera currently delivers. It is useful
        if you want to create a matching numpy array
        """
        return self._dtype

    @property
    def running(self):
        """
        This is a thread safe propertie which can check
        if the camera is (still) running
        """
        self._running_lock.acquire()
        rv = self._running
        self._running_lock.release()
        return rv

    @property
    def model(self):
        "The name of this camera (string)"
        if not self._cam:
            raise RuntimeError, "The camera is not opened!"

        return self._cam.contents.model
    @property
    def guid(self):
        "The Guid of this camera as string"
        if not self._cam:
            raise RuntimeError, "The camera is not opened!"

        return hex(self._cam.contents.guid)[2:-1]
    @property
    def vendor(self):
        "The vendor of this camera (string)"
        if not self._cam:
            raise RuntimeError, "The camera is not opened!"

        return self._cam.contents.vendor

    def mode():
        doc = \
        """The requested mode. If the camera is running, this is also
        the actual mode."""
        def fget(self):
            
            if video_mode_details.has_key( self._wanted_mode ):
                return video_mode_details[self._wanted_mode]

            else :
                return (0,0, "UNKNOWN")
        #end of fget

        def fset(self, mode):
            if self.running:
                raise RuntimeError, "Can't change mode while camera is running!"

            if not self._cam:
                raise RuntimeError, "The camera is not opened!"

            if mode not in self.modes:
                raise ValueError, "This mode is not supported by this camera!"

            if mode.__class__.__name__ != 'str' :
                if "FORMAT7" not in mode[-1].upper():
                    mode = "%dx%d_%s" %(mode[0],mode[1],mode[2])
                else:
                    #probably this is the wrong place for a format7 request...
                    mode = mode[-1]
                #end if
            #end if
            #so we can search in the video_mode_codes

            if video_mode_codes.has_key( mode ):
                self._wanted_mode = video_mode_codes[ mode ]
                #now we have the code, we can set the mode back:
                mode = video_mode_details[ self._wanted_mode ]
            #self._wanted_mode, = [ k for k,v in video_mode_vals.items() if v == mode ]

            self._shape = [ mode[1], mode[0] ]
            if mode[-1] == 'Y8':
                self._dtype = '>u1'
            elif mode[-1] == 'Y16':
                self._dtype = '>u2'
            elif mode[-1] == 'RGB':
                self._dtype = '>u1'
                self._shape.append( 3 )
        return locals()
    mode = property(**mode())

    def fps():
        doc = "The framerate belonging to the current camera mode"
        def fget(self):
            return framerate_vals[self._wanted_frate]
        def fset(self, framerate):
            if not self._cam:
                raise RuntimeError, "The camera is not opened!"

            if self.running:
                raise RuntimeError, "Can't change framerate while camera is running!"
            #end if
            if framerate_codes.has_key( framerate ):
                self._wanted_frate = framerate_codes[ framerate ]
            #end if
        return locals()
    fps = property(**fps())

    @property
    def isospeed(self):
        "The isospeed must be chosen on camera opening"
        return self._wanted_speed

    def _operation_mode():
        doc = \
        """
        This can toggle the camera mode into B mode (high speeds). This is
        a private property because you definitively do not want to change
        this as a user.
        """
        def fget(self):
            if not self._cam:
                raise RuntimeError, "The camera is not opened!"

            k = c_int()
            self._dll.dc1394_video_get_operation_mode( self._cam, byref(k))
            if k.value == 480:
                return "legacy"
            else:
                return "1394b"
        def fset(self, value):
            if not self._cam:
                raise RuntimeError, "The camera is not opened!"

            use =  480 if value == "legacy" else 481
            self._dll.dc1394_video_set_operation_mode( self._cam, use )
        return locals()
    _operation_mode = property(**_operation_mode())

    @property
    def modes(self):
        "Return all supported modes for this camera"
        return self._all_modes

    def get_framerates_for_mode(self, mode = None):
        """
        Returns all framerates supported for the given mode; if mode is
        None the current mode will be used.
        """
        if not self._cam:
            raise RuntimeError, "The camera is not opened!"

        use_modes = mode or self._wanted_mode

        fpss = framerates_t()
        _dll.dc1394_video_get_supported_framerates(self._cam, self._wanted_mode,
                        byref(fpss))
        return tuple( framerate_vals[fpss.framerates[i]]
             for i in range( fpss.num ) )


    @property
    def features(self):
        """Return all features of this camera. You can use __getattr__ to
        directly access them then."""
        return self._all_features


class SynchronizedCams(object):
    def __init__(self, cam0,cam1):
        """This class synchronizes two (not more!) cameras
        by dropping frames from one until the timestamps
        of the acquired pictures are in sync. Make sure that the
        cameras are in the same mode (framerate, shutter)

        This function assumes point gray cameras which can do autosync
        """
        self._cam0 = cam0
        self._cam1 = cam1

    def close( self ):
        "Convenient function which closes both cams"
        self._cam0.close()
        self._cam1.close()

    @property
    def cam0(self):
        return self._cam0
    @property
    def cam1(self):
        return self._cam1

    def start(self, buffers = 4):
        self._cam0.start(buffers); self._cam1.start(buffers)

        self.sync()

    def stop(self):
        self._cam0.stop(); self._cam1.stop()

    def shot(self):
        """
        This function acquires two synchronized pictures from
        the cameras. Use this if you need pictures which were
        acquired around the same time. Do not use the cams individual shot
        functions. If you need a current image you can use cam.current_image
        at all times. You can also wait for the Condition cam.new_image
        and then use cam.current_image.

        note that the user has to check for themselves if the cameras
        are out of sync and must make sure they get back in sync.
        """
        i1 = self._cam0.shot()
        i2 = self._cam1.shot()

        # assert( abs(i1.timestamp-i2.timestamp) < 500 )

        return i1,i2


    def sync(self):
        """
        Try to sync the two cameras to each other. This will
        only work if both cameras synchronize on the bus time
        """
        ldiff = 100000000
        while 1:
            t1 = self._cam0.shot().timestamp
            t2 = self._cam1.shot().timestamp

            diff = t1-t2

            if abs(diff) < 500:
                break
            if diff < 0:
                self._cam0.shot()
            else:
                self._cam1.shot()
            ldiff = diff

