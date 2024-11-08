import logging
import pykka
from mopidy.core import CoreListener

class ZestboxFrontend(pykka.ThreadingActor, CoreListener):
    def __init__(self, config, core):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config = config["zestbox"]
        self.core = core
        self.zestbox = pykka.traversable(Zestbox())
        self.needs_admin = self.config["needs_admin"]
        self.background_tracks = self.config["background_tracks"]
        self.max_queue_length = self.config["max_queue_length"]
        self.change_to_user_mode_next_track = False
        
    ### Mopidy event listeners
    def tracklist_changed(self):
        if self.core.tracklist.get_length().get() < 1 and not self.change_to_user_mode_next_track:
            self.change_to_background_tracks()
        if self.core.playback.get_state().get() == "stopped" and self.core.tracklist.get_length().get() > 0:
           self.core.playback.play()
    
    def track_playback_ended(self, time_position, tl_track):
        track = tl_track.track
        if self.zestbox.currently_playing == track:
            self.zestbox.currently_playing = []
        if self.zestbox.playing_user_track and not self.change_to_user_mode_next_track:
            try:
                self.zestbox.current_tracks.pop(track.uri)
                self.zestbox.votes = []
            except KeyError as e:
                self.logger.error("Could not synchronize Zestbox frontend with core tracklist!")
        self.logger.info(f"Track ended, changing track to {self.core.tracklist.next_track(tl_track).get()}.")
            

    def track_playback_started(self, tl_track):
        self.zestbox.currently_playing = tl_track.track
        if self.change_to_user_mode_next_track:
            self.change_to_user_mode()
            self.change_to_user_mode_next_track = False
        self.logger.info(f"Changed track to {tl_track.track}.")
        

    def playback_state_changed(self, old_state, new_state):
        self.zestbox.playback_paused = new_state == 'paused'

    ### Frontend function definitions
    def change_to_background_tracks(self):
        self.zestbox.playing_user_track = False
        if not self.zestbox.background_playlist:
            return

        self.core.tracklist.add(uris=self.zestbox.background_playlist)
        self.core.tracklist.set_consume(False)
        self.core.tracklist.set_random(True)
        self.core.tracklist.set_repeat(True)
        if self.core.playback.get_state().get() == "stopped":
            self.core.playback.play()
        self.logger.info(f"Added background tracks.\nAdded tracks: {self.core.library.lookup(self.zestbox.background_playlist).get()}")


    def add(self, new_uris = [], requester = ""):
        try:
            if not self.zestbox.playing_user_track:
                self.change_to_user_mode_next_track = True                
                self.core.tracklist.clear()
            tracks = self.core.library.lookup(new_uris).get()
            track = tracks[new_uris[0]][0]
            self.zestbox.current_tracks[track.uri] = requester
            self.core.tracklist.add(uris=new_uris).get()
            if self.core.playback.get_state().get() == "stopped":
                self.core.playback.play()
                self.logger.info("I PLAY MUSIC NOW.") 
        except Exception as e:
            self.logger.error(e)
            return e
        
        
        self.logger.info("I ADDEDDED TRACK!") 

    def change_to_user_mode(self):
        self.core.tracklist.set_consume(True)
        self.core.tracklist.set_random(False)
        self.core.tracklist.set_repeat(False)
        self.zestbox.playing_user_track = True
        self.change_to_user_mode_next_track = False

    def start_session(self, settings = None):
        self.logger.info("Starting a Zestbox session!")
        if self.zestbox.session_started:
            self.logger.info("Exception!!")
            raise Exception("Session is already started!")
        self.logger.info("No session conflict found!")
        self.zestbox.initialize()
        self.logger.info("Initialized!")
        self.zestbox.needs_admin = self.config["needs_admin"]
        self.zestbox.background_playlist = self.config["background_tracks"] #settings["backgroundPlaylist"]

        self.zestbox.max_queue_length = self.config["max_queue_length"]
        self.zestbox.queue = [None] * self.config["max_queue_length"]
        self.zestbox.votes_to_skip = self.config["votes_to_skip"] #settings["votesToSkip"]
        if settings:
            self.zestbox.admin_passphrase = settings["adminPassphrase"]            

        self.logger.info("Configured!")
        if self.zestbox.background_playlist:
            self.logger.info("Background tracks found!")
            self.zestbox.has_background_playlist = True
            self.change_to_background_tracks()
            self.logger.info("Background tracks added!")
        self.zestbox.session_started = True
        self.logger.info("Zestbox session started!")

    def stop_session(self):
        self.zestbox.__init()
        self.core.tracklist.clear()
        self.core.playback.stop()
    
    def append_ip_to_queue(self, ip):
        self.zestbox.queue.append(ip)
        self.zestbox.queue.pop(0)

    def add_vote(self, ip):
        self.zestbox.votes.append(self._getip())
        if (len(self.frontend.zestbox.votes) >= self.requiredVotes):
            self.core.playback.next()
            self.zestbox.votes = []
            return True
        return False

    def set_pause(self, pause):
        if pause: self.core.playback.pause()
        else: self.core.playback.resume()

    # Would just use get_images() from the UI side, but I'd rather just get one URI and get all info at once on track change.
    def get_img_uri(self, track):
        img = ""
        if track:
            img = self.core.library.get_images([track.uri]).get()
        if img:
            img = img[track.uri][0].uri # The first one'll do.
            return img
        else:
            return "./src/thumbnail-fb.png"

    def get_state(self):
        data = self.zestbox.state_json()
        data["imgUri"] = self.get_img_uri(self.zestbox.currently_playing)
        return data

class Zestbox:
    def __init__(self):
        super().__init__()
        self.initialize()

    def initialize(self):
        self.needs_admin = False
        self.session_started = False
        self.playing_user_track = False
        self.playback_paused = False
        self.votes = []
        self.queue = []
        self.admin_passphrase = "" # Plaintext string. Sue me.
        self.votes_to_skip = 1
        self.background_playlist = []
        self.has_background_playlist = False
        self.current_tracks = {}
        self.currently_playing = None
        self.max_queue_length = 50
        return True
    

    def state_json(self):
        return {
            "userTrack": self.playing_user_track,
            "sessionStarted": self.session_started,
            "votesNeeded": self.votes_to_skip,
            "votesAdded": len(self.votes),
            "currentTrack": self.currently_playing.serialize() if self.currently_playing else None,
            "playlistLength": len(self.current_tracks),
            "requestedBy": "Zestbox" if not self.playing_user_track\
                  else "A LEMON!" if not self.currently_playing\
                      else self.current_tracks[self.currently_playing.uri],
            "paused": self.playback_paused
        }

    