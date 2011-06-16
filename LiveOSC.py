"""
# Copyright (C) 2007 Nathan Ramella (nar@remix.net)
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# For questions regarding this module contact
# Nathan Ramella <nar@remix.net> or visit http://www.remix.net

This script is based off the Ableton Live supplied MIDI Remote Scripts, customised
for OSC request delivery and response. This script can be run without any extra
Python libraries out of the box. 

This is the second file that is loaded, by way of being instantiated through
__init__.py

"""

import Live
import LiveOSCCallbacks
import RemixNet
import OSC
import LiveUtils
import sys
from Logger import log

class LiveOSC:
    __module__ = __name__
    __doc__ = "Main class that establishes the LiveOSC Component"
    
    prlisten = {}
    plisten = {}
    dlisten = {}
    clisten = {}
    slisten = {}
    pplisten = {}
    cnlisten = {}
    cclisten = {}
    
    mlisten = { "solo": {}, "mute": {}, "arm": {}, "panning": {}, "volume": {}, "sends": {}, "name": {}, "oml": {}, "omr": {} }
    rlisten = { "solo": {}, "mute": {}, "panning": {}, "volume": {}, "sends": {}, "name": {} }
    masterlisten = { "panning": {}, "volume": {}, "crossfader": {} }
    scenelisten = {}
    
    scene = 0
    track = 0

    def __init__(self, c_instance):
        self._LiveOSC__c_instance = c_instance
      
        self.basicAPI = 0       
        self.oscEndpoint = RemixNet.OSCEndpoint()
        self.oscEndpoint.send('/remix/oscserver/startup', 1)
        
        log("LiveOSC initialized")
        
        # Visible tracks listener
        if self.song().visible_tracks_has_listener(self.refresh_state) != 1:
            self.song().add_visible_tracks_listener(self.refresh_state)
        
######################################################################
# Standard Ableton Methods

    def connect_script_instances(self, instanciated_scripts):
        """
        Called by the Application as soon as all scripts are initialized.
        You can connect yourself to other running scripts here, as we do it
        connect the extension modules
        """
        return

    def is_extension(self):
        return False

    def request_rebuild_midi_map(self):
        """
        To be called from any components, as soon as their internal state changed in a 
        way, that we do need to remap the mappings that are processed directly by the 
        Live engine.
        Dont assume that the request will immediately result in a call to
        your build_midi_map function. For performance reasons this is only
        called once per GUI frame.
        """
        return
    
    def update_display(self):
        """
        This function is run every 100ms, so we use it to initiate our Song.current_song_time
        listener to allow us to process incoming OSC commands as quickly as possible under
        the current listener scheme.
        """
        ######################################################
        # START OSC LISTENER SETUP
              
        if self.basicAPI == 0:
            # By default we have set basicAPI to 0 so that we can assign it after
            # initialization. We try to get the current song and if we can we'll
            # connect our basicAPI callbacks to the listener allowing us to 
            # respond to incoming OSC every 60ms.
            #
            # Since this method is called every 100ms regardless of the song time
            # changing, we use both methods for processing incoming UDP requests
            # so that from a resting state you can initiate play/clip triggering.

            try:
                doc = self.song()
            except:
                log('could not get song handle')
                return
            try:
                self.basicAPI = LiveOSCCallbacks.LiveOSCCallbacks(self._LiveOSC__c_instance, self.oscEndpoint)
                # Commented for stability
                self.time = 0
                doc.add_current_song_time_listener(self.current_song_time_changed)
            except:
                self.oscEndpoint.send('/remix/echo', 'setting up basicAPI failed')
                log('setting up basicAPI failed');
                return
            
            # If our OSC server is listening, try processing incoming requests.
            # Any 'play' initiation will trigger the current_song_time listener
            # and bump updates from 100ms to 60ms.
            
        if self.oscEndpoint:
            try:
                self.oscEndpoint.processIncomingUDP()
            except:
                log('error processing incoming UDP packets:', sys.exc_info());
            
        # END OSC LISTENER SETUP
        ######################################################

    def current_song_time_changed(self):
        time = self.song().current_song_time
        if int(time) != self.time:
            self.time = int(time)
            self.oscEndpoint.send("/live/beat", self.time)

    def send_midi(self, midi_event_bytes):
        """
        Use this function to send MIDI events through Live to the _real_ MIDI devices 
        that this script is assigned to.
        """
        pass

    def receive_midi(self, midi_bytes):
        return

    def can_lock_to_devices(self):
        return False

    def suggest_input_port(self):
        return ''

    def suggest_output_port(self):
        return ''

    def __handle_display_switch_ids(self, switch_id, value):
	pass
    
    
######################################################################
# Useful Methods

    def application(self):
        """returns a reference to the application that we are running in"""
        return Live.Application.get_application()

    def song(self):
        """returns a reference to the Live Song that we do interact with"""
        return self._LiveOSC__c_instance.song()

    def handle(self):
        """returns a handle to the c_interface that is needed when forwarding MIDI events via the MIDI map"""
        return self._LiveOSC__c_instance.handle()
            
    def getslots(self):
        tracks = self.song().visible_tracks

        clipSlots = []
        for track in tracks:
            clipSlots.append(track.clip_slots)
        return clipSlots

    def trBlock(self, trackOffset, blocksize):
        block = []
        tracks = self.song().visible_tracks
        
        for track in range(0, blocksize):
            block.extend([str(tracks[trackOffset+track].name)])                            
        self.oscEndpoint.send("/live/name/trackblock", block)        

######################################################################
# Used Ableton Methods

    def disconnect(self):
        self.rem_clip_listeners()
        self.rem_mixer_listeners()
        self.rem_scene_listeners()
        self.rem_tempo_listener()
        self.rem_overdub_listener()
        self.rem_tracks_listener()
        self.rem_device_listeners()
        self.rem_transport_listener()
        
        self.song().remove_visible_tracks_listener(self.refresh_state)
        
        self.oscEndpoint.send('/remix/oscserver/shutdown', 1)
        self.oscEndpoint.shutdown()
            
    def build_midi_map(self, midi_map_handle):
        self.refresh_state()            
            
    def refresh_state(self):
        self.add_clip_listeners()
        self.add_mixer_listeners()
        self.add_scene_listeners()
        self.add_tempo_listener()
        self.add_overdub_listener()
        self.add_tracks_listener()
        self.add_device_listeners()
        self.add_transport_listener()

        trackNumber = 0
        clipNumber = 0
        
        bundle = OSC.OSCBundle()
        for track in self.song().visible_tracks:
            bundle.append("/live/name/track", (trackNumber, str(track.name)))
            
            for clipSlot in track.clip_slots:
                if clipSlot.clip != None:
                    bundle.append("/live/name/clip", (trackNumber, clipNumber, str(clipSlot.clip.name), clipSlot.clip.color))
                clipNumber = clipNumber + 1
            clipNumber = 0
            trackNumber = trackNumber + 1

        self.oscEndpoint.sendMessage(bundle)
        self.trBlock(0, len(self.song().visible_tracks))

######################################################################
# Add / Remove Listeners   
    def add_scene_listeners(self):
        self.rem_scene_listeners()
    
        if self.song().view.selected_scene_has_listener(self.scene_change) != 1:
            self.song().view.add_selected_scene_listener(self.scene_change)

        if self.song().view.selected_track_has_listener(self.track_change) != 1:
            self.song().view.add_selected_track_listener(self.track_change)

    def rem_scene_listeners(self):
        if self.song().view.selected_scene_has_listener(self.scene_change) == 1:
            self.song().view.remove_selected_scene_listener(self.scene_change)
            
        if self.song().view.selected_track_has_listener(self.track_change) == 1:
            self.song().view.remove_selected_track_listener(self.track_change)

    def track_change(self):
        selected_track = self.song().view.selected_track
        tracks = self.song().visible_tracks
        index = 0
        selected_index = 0
        for track in tracks:
            index = index + 1        
            if track == selected_track:
                selected_index = index
                
        if selected_index != self.track:
            self.track = selected_index
            self.oscEndpoint.send("/live/track", (selected_index))

    def scene_change(self):
        selected_scene = self.song().view.selected_scene
        scenes = self.song().scenes
        index = 0
        selected_index = 0
        for scene in scenes:
            index = index + 1        
            if scene == selected_scene:
                selected_index = index
                
        if selected_index != self.scene:
            self.scene = selected_index
            self.oscEndpoint.send("/live/scene", (selected_index))
	
    def add_tempo_listener(self):
        self.rem_tempo_listener()
    
        print "add tempo listener"
        if self.song().tempo_has_listener(self.tempo_change) != 1:
            self.song().add_tempo_listener(self.tempo_change)
        
    def rem_tempo_listener(self):
        if self.song().tempo_has_listener(self.tempo_change) == 1:
            self.song().remove_tempo_listener(self.tempo_change)
    
    def tempo_change(self):
        tempo = LiveUtils.getTempo()
        self.oscEndpoint.send("/live/tempo", (tempo))
	
    def add_transport_listener(self):
        if self.song().is_playing_has_listener(self.transport_change) != 1:
            self.song().add_is_playing_listener(self.transport_change)
            
    def rem_transport_listener(self):
        if self.song().is_playing_has_listener(self.transport_change) == 1:
            self.song().remove_is_playing_listener(self.transport_change)    
    
    def transport_change(self):
        self.oscEndpoint.send("/live/play", (self.song().is_playing and 2 or 1))
    
    def add_overdub_listener(self):
        self.rem_overdub_listener()
    
        if self.song().overdub_has_listener(self.overdub_change) != 1:
            self.song().add_overdub_listener(self.overdub_change)
	    
    def rem_overdub_listener(self):
        if self.song().overdub_has_listener(self.overdub_change) == 1:
            self.song().remove_overdub_listener(self.overdub_change)
	    
    def overdub_change(self):
        overdub = LiveUtils.getSong().overdub
        self.oscEndpoint.send("/live/overdub", (int(overdub) + 1))
	
    def add_tracks_listener(self):
        self.rem_tracks_listener()
    
        if self.song().tracks_has_listener(self.tracks_change) != 1:
            self.song().add_tracks_listener(self.tracks_change)
    
    def rem_tracks_listener(self):
        if self.song().tracks_has_listener(self.tempo_change) == 1:
            self.song().remove_tracks_listener(self.tracks_change)
    
    def tracks_change(self):
        self.oscEndpoint.send("/live/refresh", (1))

    def rem_clip_listeners(self):
        for slot in self.slisten:
            if slot != None:
                if slot.has_clip_has_listener(self.slisten[slot]) == 1:
                    slot.remove_has_clip_listener(self.slisten[slot])
    
        self.slisten = {}
        
        for clip in self.clisten:
            if clip != None:
                if clip.playing_status_has_listener(self.clisten[clip]) == 1:
                    clip.remove_playing_status_listener(self.clisten[clip])
                
        self.clisten = {}

        for clip in self.pplisten:
            if clip != None:
                if clip.playing_position_has_listener(self.pplisten[clip]) == 1:
                    clip.remove_playing_position_listener(self.pplisten[clip])
                
        self.pplisten = {}

        for clip in self.cnlisten:
            if clip != None:
                if clip.name_has_listener(self.cnlisten[clip]) == 1:
                    clip.remove_name_listener(self.cnlisten[clip])
                
        self.cnlisten = {}

        for clip in self.cclisten:
            if clip != None:
                if clip.color_has_listener(self.cclisten[clip]) == 1:
                    clip.remove_color_listener(self.cclisten[clip])
                
        self.cclisten = {}
        
    def add_clip_listeners(self):
        self.rem_clip_listeners()
    
        tracks = self.getslots()
        for track in range(len(tracks)):
            for clip in range(len(tracks[track])):
                c = tracks[track][clip]
                if c.clip != None:
                    self.add_cliplistener(c.clip, track, clip)
                    log("ClipLauncher: added clip listener tr: " + str(track) + " clip: " + str(clip));
                
                self.add_slotlistener(c, track, clip)
        
    def add_cliplistener(self, clip, tid, cid):
        cb = lambda :self.clip_changestate(clip, tid, cid)
        
        if self.clisten.has_key(clip) != 1:
            clip.add_playing_status_listener(cb)
            self.clisten[clip] = cb
            
        cb2 = lambda :self.clip_position(clip, tid, cid)
        if self.pplisten.has_key(clip) != 1:
            clip.add_playing_position_listener(cb2)
            self.pplisten[clip] = cb2
            
        cb3 = lambda :self.clip_name(clip, tid, cid)
        if self.cnlisten.has_key(clip) != 1:
            clip.add_name_listener(cb3)
            self.cnlisten[clip] = cb3

        if self.cclisten.has_key(clip) != 1:
            clip.add_color_listener(cb3)
            self.cclisten[clip] = cb3
        
    def add_slotlistener(self, slot, tid, cid):
        cb = lambda :self.slot_changestate(slot, tid, cid)
        
        if self.slisten.has_key(slot) != 1:
            slot.add_has_clip_listener(cb)
            self.slisten[slot] = cb   
            
    
    def rem_mixer_listeners(self):
        # Master Track
        for type in ("volume", "panning", "crossfader"):
            for tr in self.masterlisten[type]:
                if tr != None:
                    cb = self.masterlisten[type][tr]
                
                    test = eval("tr.mixer_device." + type+ ".value_has_listener(cb)")
                
                    if test == 1:
                        eval("tr.mixer_device." + type + ".remove_value_listener(cb)")

        # Normal Tracks
        for type in ("arm", "solo", "mute"):
            for tr in self.mlisten[type]:
                if tr != None:
                    cb = self.mlisten[type][tr]
                    
                    if type == "arm":
                        if tr.can_be_armed == 1:
                            if tr.arm_has_listener(cb) == 1:
                                tr.remove_arm_listener(cb)
                                
                    else:
                        test = eval("tr." + type+ "_has_listener(cb)")
                
                        if test == 1:
                            eval("tr.remove_" + type + "_listener(cb)")
                
        for type in ("volume", "panning"):
            for tr in self.mlisten[type]:
                if tr != None:
                    cb = self.mlisten[type][tr]
                
                    test = eval("tr.mixer_device." + type+ ".value_has_listener(cb)")
                
                    if test == 1:
                        eval("tr.mixer_device." + type + ".remove_value_listener(cb)")
         
        for tr in self.mlisten["sends"]:
            if tr != None:
                for send in self.mlisten["sends"][tr]:
                    if send != None:
                        cb = self.mlisten["sends"][tr][send]

                        if send.value_has_listener(cb) == 1:
                            send.remove_value_listener(cb)
                        
                        
        for tr in self.mlisten["name"]:
            if tr != None:
                cb = self.mlisten["name"][tr]

                if tr.name_has_listener(cb) == 1:
                    tr.remove_name_listener(cb)

        for tr in self.mlisten["oml"]:
            if tr != None:
                cb = self.mlisten["oml"][tr]

                if tr.output_meter_left_has_listener(cb) == 1:
                    tr.remove_output_meter_left_listener(cb)

        for tr in self.mlisten["omr"]:
            if tr != None:
                cb = self.mlisten["omr"][tr]

                if tr.output_meter_right_has_listener(cb) == 1:
                    tr.remove_output_meter_right_listener(cb)
                    
        # Return Tracks                
        for type in ("solo", "mute"):
            for tr in self.rlisten[type]:
                if tr != None:
                    cb = self.rlisten[type][tr]
                
                    test = eval("tr." + type+ "_has_listener(cb)")
                
                    if test == 1:
                        eval("tr.remove_" + type + "_listener(cb)")
                
        for type in ("volume", "panning"):
            for tr in self.rlisten[type]:
                if tr != None:
                    cb = self.rlisten[type][tr]
                
                    test = eval("tr.mixer_device." + type+ ".value_has_listener(cb)")
                
                    if test == 1:
                        eval("tr.mixer_device." + type + ".remove_value_listener(cb)")
         
        for tr in self.rlisten["sends"]:
            if tr != None:
                for send in self.rlisten["sends"][tr]:
                    if send != None:
                        cb = self.rlisten["sends"][tr][send]
                
                        if send.value_has_listener(cb) == 1:
                            send.remove_value_listener(cb)

        for tr in self.rlisten["name"]:
            if tr != None:
                cb = self.rlisten["name"][tr]

                if tr.name_has_listener(cb) == 1:
                    tr.remove_name_listener(cb)
                    
        self.mlisten = { "solo": {}, "mute": {}, "arm": {}, "panning": {}, "volume": {}, "sends": {}, "name": {}, "oml": {}, "omr": {} }
        self.rlisten = { "solo": {}, "mute": {}, "panning": {}, "volume": {}, "sends": {}, "name": {} }
        self.masterlisten = { "panning": {}, "volume": {}, "crossfader": {} }
    
    
    def add_mixer_listeners(self):
        self.rem_mixer_listeners()
        
        # Master Track
        tr = self.song().master_track
        for type in ("volume", "panning", "crossfader"):
            self.add_master_listener(0, type, tr)
        
        self.add_meter_listener(0, tr, 2)
        
        # Normal Tracks
        tracks = self.song().visible_tracks
        for track in range(len(tracks)):
            tr = tracks[track]

            self.add_trname_listener(track, tr, 0)
            
            if tr.has_audio_output:
                self.add_meter_listener(track, tr)
            
            for type in ("arm", "solo", "mute"):
                if type == "arm":
                    if tr.can_be_armed == 1:
                        self.add_mixert_listener(track, type, tr)
                else:
                    self.add_mixert_listener(track, type, tr)
                
            for type in ("volume", "panning"):
                self.add_mixerv_listener(track, type, tr)
                
            for sid in range(len(tr.mixer_device.sends)):
                self.add_send_listener(track, tr, sid, tr.mixer_device.sends[sid])
        
        # Return Tracks
        tracks = self.song().return_tracks
        for track in range(len(tracks)):
            tr = tracks[track]

            self.add_trname_listener(track, tr, 1)
            self.add_meter_listener(track, tr, 1)
            
            for type in ("solo", "mute"):
                self.add_retmixert_listener(track, type, tr)
                
            for type in ("volume", "panning"):
                self.add_retmixerv_listener(track, type, tr)
            
            for sid in range(len(tr.mixer_device.sends)):
                self.add_retsend_listener(track, tr, sid, tr.mixer_device.sends[sid])
        
    
    # Add track listeners
    def add_send_listener(self, tid, track, sid, send):
        if self.mlisten["sends"].has_key(track) != 1:
            self.mlisten["sends"][track] = {}
                    
        if self.mlisten["sends"][track].has_key(send) != 1:
            cb = lambda :self.send_changestate(tid, track, sid, send)
            
            self.mlisten["sends"][track][send] = cb
            send.add_value_listener(cb)
    
    def add_mixert_listener(self, tid, type, track):
        if self.mlisten[type].has_key(track) != 1:
            cb = lambda :self.mixert_changestate(type, tid, track)
            
            self.mlisten[type][track] = cb
            eval("track.add_" + type + "_listener(cb)")
            
    def add_mixerv_listener(self, tid, type, track):
        if self.mlisten[type].has_key(track) != 1:
            cb = lambda :self.mixerv_changestate(type, tid, track)
            
            self.mlisten[type][track] = cb
            eval("track.mixer_device." + type + ".add_value_listener(cb)")

    # Add master listeners
    def add_master_listener(self, tid, type, track):
        if self.masterlisten[type].has_key(track) != 1:
            cb = lambda :self.mixerv_changestate(type, tid, track, 2)
            
            self.masterlisten[type][track] = cb
            eval("track.mixer_device." + type + ".add_value_listener(cb)")
            
            
    # Add return listeners
    def add_retsend_listener(self, tid, track, sid, send):
        if self.rlisten["sends"].has_key(track) != 1:
            self.rlisten["sends"][track] = {}
                    
        if self.rlisten["sends"][track].has_key(send) != 1:
            cb = lambda :self.send_changestate(tid, track, sid, send, 1)
            
            self.rlisten["sends"][track][send] = cb
            send.add_value_listener(cb)
    
    def add_retmixert_listener(self, tid, type, track):
        if self.rlisten[type].has_key(track) != 1:
            cb = lambda :self.mixert_changestate(type, tid, track, 1)
            
            self.rlisten[type][track] = cb
            eval("track.add_" + type + "_listener(cb)")
            
    def add_retmixerv_listener(self, tid, type, track):
        if self.rlisten[type].has_key(track) != 1:
            cb = lambda :self.mixerv_changestate(type, tid, track, 1)
            
            self.rlisten[type][track] = cb
            eval("track.mixer_device." + type + ".add_value_listener(cb)")      


    # Track name listener
    def add_trname_listener(self, tid, track, ret = 0):
        cb = lambda :self.trname_changestate(tid, track, ret)

        if ret == 1:
            if self.rlisten["name"].has_key(track) != 1:
                self.rlisten["name"][track] = cb
        
        else:
            if self.mlisten["name"].has_key(track) != 1:
                self.mlisten["name"][track] = cb
        
        track.add_name_listener(cb)
        
    # Output Meter Listeners
    def add_meter_listener(self, tid, track, r = 0):
        cb = lambda :self.meter_changestate(tid, track, 0, r)

        if self.mlisten["oml"].has_key(track) != 1:
            self.mlisten["oml"][track] = cb

        track.add_output_meter_left_listener(cb)

        cb = lambda :self.meter_changestate(tid, track, 1, r)

        if self.mlisten["omr"].has_key(track) != 1:
            self.mlisten["omr"][track] = cb

        track.add_output_meter_right_listener(cb)

######################################################################
# Listener Callbacks
        
    # Clip Callbacks
    def clip_name(self, clip, tid, cid):
        self.oscEndpoint.send('/live/name/clip', (tid, cid, str(clip.name), clip.color))
    
    def clip_position(self, clip, tid, cid):
        if self.check_md(1):
            if clip.is_playing:
                self.oscEndpoint.send('/live/clip/position', (tid, cid, clip.playing_position, clip.length, clip.loop_start, clip.loop_end))
    
    def slot_changestate(self, slot, tid, cid):
        tmptrack = LiveUtils.getTrack(tid)
        armed = tmptrack.arm and 1 or 0
        
        # Added new clip
        if slot.clip != None:
            self.add_cliplistener(slot.clip, tid, cid)
            
            playing = 1
            if slot.clip.is_playing == 1:
                playing = 2
            
            if slot.clip.is_triggered == 1:
                playing = 3
            
            length =  slot.clip.loop_end - slot.clip.loop_start
            
            self.oscEndpoint.send('/live/track/info', (tid, armed, cid, playing, length))
            self.oscEndpoint.send('/live/name/clip', (tid, cid, str(slot.clip.name), slot.clip.color))
        else:
            if self.clisten.has_key(slot.clip) == 1:
                slot.clip.remove_playing_status_listener(self.clisten[slot.clip])
                
            if self.pplisten.has_key(slot.clip) == 1:
                slot.clip.remove_playing_position_listener(self.pplisten[slot.clip])

            if self.cnlisten.has_key(slot.clip) == 1:
                slot.clip.remove_name_listener(self.cnlisten[slot.clip])

            if self.cclisten.has_key(slot.clip) == 1:
                slot.clip.remove_color_listener(self.cclisten[slot.clip])
            
            self.oscEndpoint.send('/live/track/info', (tid, armed, cid, 0, 0.0))
            self.oscEndpoint.send('/live/clip/info', (tid, cid, 0))
                
        #log("Slot changed" + str(self.clips[tid][cid]))
    
    def clip_changestate(self, clip, x, y):
        log("Listener: x: " + str(x) + " y: " + str(y));

        playing = 1
        
        if clip.is_playing == 1:
            playing = 2
            
        if clip.is_triggered == 1:
            playing = 3
            
        self.oscEndpoint.send('/live/clip/info', (x, y, playing))
        
        #log("Clip changed x:" + str(x) + " y:" + str(y) + " status:" + str(playing)) 
        
        
    # Mixer Callbacks
    def mixerv_changestate(self, type, tid, track, r = 0):
        val = eval("track.mixer_device." + type + ".value")
        types = { "panning": "pan", "volume": "volume", "crossfader": "crossfader" }
        
        if r == 2:
            self.oscEndpoint.send('/live/master/' + types[type], (float(val)))
        elif r == 1:
            self.oscEndpoint.send('/live/return/' + types[type], (tid, float(val)))
        else:
            self.oscEndpoint.send('/live/' + types[type], (tid, float(val)))        
        
    def mixert_changestate(self, type, tid, track, r = 0):
        val = eval("track." + type)
        
        if r == 1:
            self.oscEndpoint.send('/live/return/' + type, (tid, int(val)))
        else:
            self.oscEndpoint.send('/live/' + type, (tid, int(val)))        
    
    def send_changestate(self, tid, track, sid, send, r = 0):
        val = send.value
        
        if r == 1:
            self.oscEndpoint.send('/live/return/send', (tid, sid, float(val)))   
        else:
            self.oscEndpoint.send('/live/send', (tid, sid, float(val)))   


    # Track name changestate
    def trname_changestate(self, tid, track, r = 0):
        if r == 1:
            self.oscEndpoint.send('/live/name/return', (tid, str(track.name)))
        else:
            self.oscEndpoint.send('/live/name/track', (tid, str(track.name)))
            self.trBlock(0, len(LiveUtils.getTracks()))
            
    # Meter Changestate
    def meter_changestate(self, tid, track, lr, r = 0):
        if r == 2:
            if self.check_md(2):
                if lr == 0:
                    self.oscEndpoint.send('/live/master/meter', (0, float(track.output_meter_left)))
                else:
                    self.oscEndpoint.send('/live/master/meter', (1, float(track.output_meter_right)))
        elif r == 1:
            if self.check_md(3):
                if lr == 0:
                    self.oscEndpoint.send('/live/return/meter', (tid, 0, float(track.output_meter_left)))
                else:
                    self.oscEndpoint.send('/live/return/meter', (tid, 1, float(track.output_meter_right)))        
        else:
            if self.check_md(4):
                if lr == 0:
                    self.oscEndpoint.send('/live/track/meter', (tid, 0, float(track.output_meter_left)))
                else:
                    self.oscEndpoint.send('/live/track/meter', (tid, 1, float(track.output_meter_right)))
    
    def check_md(self, param):
        devices = self.song().master_track.devices
        
        if len(devices) > 0:
            if devices[0].parameters[param].value > 0:
                return 1
            else:
                return 0
        else:
            return 0
    
    # Device Listeners
    def add_device_listeners(self):
        self.rem_device_listeners()
    
        self.do_add_device_listeners(self.song().tracks,0)
        self.do_add_device_listeners(self.song().return_tracks,1)
        self.do_add_device_listeners([self.song().master_track],2)
            
    def do_add_device_listeners(self, tracks, type):
        for i in range(len(tracks)):
            self.add_devicelistener(tracks[i], i, type)
        
            if len(tracks[i].devices) >= 1:
                for j in range(len(tracks[i].devices)):
                    self.add_devpmlistener(tracks[i].devices[j])
                
                    if len(tracks[i].devices[j].parameters) >= 1:
                        for k in range (len(tracks[i].devices[j].parameters)):
                            par = tracks[i].devices[j].parameters[k]
                            self.add_paramlistener(par, i, j, k, type)
            
    def rem_device_listeners(self):
        for pr in self.prlisten:
            ocb = self.prlisten[pr]
            if pr != None:
                if pr.value_has_listener(ocb) == 1:
                    pr.remove_value_listener(ocb)
        
        self.prlisten = {}
        
        for tr in self.dlisten:
            ocb = self.dlisten[tr]
            if tr != None:
                if tr.view.selected_device_has_listener(ocb) == 1:
                    tr.view.remove_selected_device_listener(ocb)
                    
        self.dlisten = {}
        
        for de in self.plisten:
            ocb = self.plisten[de]
            if de != None:
                if de.parameters_has_listener(ocb) == 1:
                    de.remove_parameters_listener(ocb)
                    
        self.plisten = {}

    def add_devpmlistener(self, device):
        cb = lambda :self.devpm_change()
        
        if self.plisten.has_key(device) != 1:
            device.add_parameters_listener(cb)
            self.plisten[device] = cb
    
    def devpm_change(self):
        self.refresh_state()
        
    def add_paramlistener(self, param, tid, did, pid, type):
        cb = lambda :self.param_changestate(param, tid, did, pid, type)
        
        if self.prlisten.has_key(param) != 1:
            param.add_value_listener(cb)
            self.prlisten[param] = cb
            
    def param_changestate(self, param, tid, did, pid, type):
        if type == 2:
            self.oscEndpoint.send('/live/master/device/param', (did, pid, param.value, str(param.name)))
        elif type == 1:
            self.oscEndpoint.send('/live/return/device/param', (tid, did, pid, param.value, str(param.name)))
        else:
            self.oscEndpoint.send('/live/device/param', (tid, did, pid, param.value, str(param.name)))
        
    def add_devicelistener(self, track, tid, type):
        cb = lambda :self.device_changestate(track, tid, type)
        
        if self.dlisten.has_key(track) != 1:
            track.view.add_selected_device_listener(cb)
            self.dlisten[track] = cb
        
    def device_changestate(self, track, tid, type):
        did = self.tuple_idx(track.devices, track.view.selected_device)
        
        if type == 2:
            self.oscEndpoint.send('/live/master/devices/selected', (did))
        elif type == 1:
            self.oscEndpoint.send('/live/return/device/selected', (tid, did))
        else:
            self.oscEndpoint.send('/live/device/selected', (tid, did))        
        
    def tuple_idx(self, tuple, obj):
        for i in xrange(0,len(tuple)):
            if (tuple[i] == obj):
                return i 
