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
        
    ### Mopidy event listeners
    def tracklist_changed(self):
        if self.core.tracklist.get_length().get() < 1:
            self.change_to_background_tracks()
    
    def track_playback_ended(self, time_position, tl_track):
        track = tl_track.track
        if self.zestbox.currently_playing == track:
            self.zestbox.currently_playing = []
        if self.zestbox.is_user_tracklist:
            try:
                self.zestbox.current_tracks.pop(track)
                self.zestbox.votes = []
            except KeyError as e:
                self.logger.error("Could not synchronize Zestbox frontend with core tracklist!")
            

    def track_playback_started(self, tl_track):
        self.zestbox.currently_playing = tl_track.track

    def playback_state_changed(self, old_state, new_state):
        self.zestbox.playback_paused = new_state == 'paused'

    ### Frontend function definitions
    def change_to_background_tracks(self):
        if not self.zestbox.background_playlist:
            return

        self.core.tracklist.add(uris=self.zestbox.background_playlist)
        self.core.tracklist.set_consume(False)
        self.core.tracklist.set_random(True)
        self.core.tracklist.set_repeat(True)
        self.zestbox.is_user_tracklist = False
        if self.core.playback.get_state().get() == "stopped":
            self.core.playback.play()

    def add(self, new_uris = [], requester = ""):
        try:
            if not self.zestbox.is_user_tracklist:
                self.core.tracklist.clear()
                self.change_to_user_mode()
            self.core.tracklist.add(uris=new_uris).get()
            track = self.core.tracklist.filter({"uri": new_uris})
            if self.core.playback.get_state().get() == "stopped":
                self.core.playback.play()
                self.logger.info("I PLAY MUSIC NOW.") 
        except Exception as e:
            self.logger.error(e)
            return e
        
        self.zestbox.currentTracks[track] = requester
        self.logger.info("I ADDEDDED TRACK!") 

    def change_to_user_mode(self):
        self.core.tracklist.set_consume(True)
        self.core.tracklist.set_random(False)
        self.core.tracklist.set_repeat(False)
        self.zestbox.is_user_tracklist = True

    def start_session(self, settings):
        self.logger.info("Starting a Zestbox session!")
        if self.zestbox.session_started:
            self.logger.info("Exception!!")
            raise Exception("Session is already started!")
        self.logger.info("No session conflict found!")
        self.zestbox.initialize()
        self.logger.info("Initialized!")
        self.zestbox.needs_admin = self.config["needs_admin"]
        self.zestbox.background_playlist = self.config["background_tracks"] #settings["backgroundPlaylist"]
        self.zestbox.admin_passphrase = settings["adminPassphrase"]
        self.zestbox.max_queue_length = self.config["max_queue_length"]
        self.zestbox.queue = [None] * self.config["max_queue_length"]
        self.zestbox.votes_to_skip = self.config["votes_to_skip"] #settings["votesToSkip"]
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

      

    def get_state(self):
        return self.zestbox.state_json()

class Zestbox:
    def __init__(self):
        super().__init__()
        self.initialize()

    def initialize(self):
        self.needs_admin = False
        self.session_started = False
        self.playing_user_track = False
        self.is_user_tracklist = False
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
                  else "A LEMON!" if self.currently_playing is None\
                      else self.current_tracks[self.currently_playing],
            "paused": self.playback_paused
        }

    