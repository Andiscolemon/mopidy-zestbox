import os, shutil, json

import tornado.web,pykka

from mopidy import config, ext

from mopidy_zestbox import frontend

__version__ = '0.1.0'


class VoteRequestHandler(tornado.web.RequestHandler):

    def initialize(self, core, frontend):
        self.core = core
        self.frontend = frontend
        self.requiredVotes = frontend.zestbox.votes_to_skip.get()

    def _getip(self):
        return self.request.headers.get("X-Forwarded-For", self.request.remote_ip)

    def get(self):
        if not self.frontend.zestbox.session_started.get():
            self.write("Session is not started!")
            self.set_status(409)
            return

        current_track = self.frontend.zestbox.currently_playing.get()
        if not current_track or not self.frontend.zestbox.is_user_tracklist.get(): return

        if self._getip() in self.frontend.zestbox.votes.get(): # User has already voted
            self.write("You have already voted to skip this song =)")
        else: # Valid vote
            if self.frontend.add_vote(self._getip()).get():            
                self.write("Skipping...")
            else:
                self.write("You have voted to skip this song. ("+str(self.requiredVotes-len(self.frontend.zestbox.votes.get()))+" more votes needed)")


class AddRequestHandler(tornado.web.RequestHandler):
    def initialize(self, core, frontend):
        self.core = core
        self.frontend = frontend
        self.maxQueueLength = frontend.zestbox.max_queue_length.get()

    def _getip(self):
        return self.request.headers.get("X-Forwarded-For", self.request.remote_ip)

    def post(self):
        if not self.frontend.zestbox.session_started.get():
            self.write("Session is not started!")
            self.set_status(403)
            return
        # when the last n tracks were added by the same user, abort.
        current_queue = self.frontend.zestbox.queue.get()
        if current_queue and all([e == self._getip() for e in current_queue]):
            self.write("You have requested too many songs")
            self.set_status(409)
            return

        request = json.loads(self.request.body)
        track_uri = request["uri"]
        user = request["user"]
        if not track_uri:
            self.set_status(400)
            return

        n_queued = self.core.tracklist.get_length().get()
        if (self.maxQueueLength > 0) and (n_queued > self.maxQueueLength):
            self.write("Queue at max length, try again later.")
            self.set_status(409)
            return

        try:
            self.frontend.add(new_uris=[track_uri], requester=user)
            self.frontend.append_ip_to_queue(self._getip())
        except Exception as e:
            self.write("Unable to add track. Internal Server Error: "+repr(e))
            self.set_status(500)
            return



class IndexHandler(tornado.web.RequestHandler):    
    def initialize(self, config):
        self.__dict = {}
        # Make zestbox configuration from mopidy.conf available as variables in index.html
        for conf_key, value in config.items():
            if conf_key != "enabled":
                self.__dict[conf_key] = value

    def get(self):
        return self.render("static/index.html", **self.__dict)
    
class VisualizerHandler(tornado.web.RequestHandler):

    def initialize(self, core, data, config):
        self.core = core
        self.data = data
        self.__dict = {}
        # Same as IndexHandler, but making variables available for the visualizer.
        for conf_key, value in config["zestbox"].items():
            if conf_key != "enabled":
                self.__dict[conf_key] = value

    def get(self):
        if shutil.which("icecast2") is not None:
            self.__dict["has_icecast"] = True
        else:
            self.set_status(
                503, "Icecast is required to view audio visualization."
            ) 
            self.__dict["no_icecast"] = False
        return self.render("static/visualizer.html", **self.__dict)
                

class ConfigHandler(tornado.web.RequestHandler):

    def initialize(self, config):
        self.zest_cfg = config

    def get(self):
        conf_key = self.get_argument("key")
        if conf_key == []:
            self.set_status(400)
            self.write("Query parameter 'key' not present")
            return
        try:
            value = self.zest_cfg[conf_key]
            self.write(repr(value))
        except KeyError:
            self.set_status(404)
            self.write("Zestbox configuration '" + conf_key + "' not found")
            return
        except Exception as e:
            self.set_status(500)
            self.write("Internal server error: "+repr(e))
            return

class ControlHandler(tornado.web.RequestHandler):
    def initialize(self, frontend):
        self.frontend = frontend

    def post(self):
        try:
            command = json.loads(self.request.body.decode())
        except ValueError as e:
            self.write("Malformed JSON data provided.")
            self.set_status(400)
            return
            
        match command["command"]:
            case "pause":
                self.frontend.set_pause(True)
                return
            case "resume":
                self.frontend.set_pause(False)
                return
            case "start":
                try:
                    self.frontend.start_session(command)
                except Exception as e:
                    self.write(e)
                    self.set_status(409)
                    return
                self.write("Session started!")
                self.set_status(200)

    
    def get(self):
        reply = self.frontend.get_state().get()
        reply["imgUri"] = self.frontend.get_img_uri(reply["currentTrack"]).get()
        reply = json.dumps(reply)
        self.write(reply)

def lemon_factory(config, core):
    from tornado.web import RedirectHandler
    from .frontend import ZestboxFrontend
    
    #TODO: Move data dict to Zestbox frontend class completely.
    data = {'track':"", 'votes':[], 'queue': [None] * config["zestbox"]["max_tracks"], 'last':None}
    fe = pykka.ActorRegistry.get_by_class(ZestboxFrontend)[0].proxy()
    
    return [
    ('/', RedirectHandler, {'url': 'index.html'}), #always redirect from extension root to the html
    ('/index.html', IndexHandler, {'config': config["zestbox"]}),
    ('/vote', VoteRequestHandler, {'core': core, 'frontend': fe}),
    ('/add', AddRequestHandler, {'core': core, 'frontend': fe}),
    ('/config', ConfigHandler, {'config':config["zestbox"]}),
    ('/control', ControlHandler, {'frontend': fe}),
    ('/visualizer', RedirectHandler, {'url': 'visualizer.html'}),
    ('/visualizer.html', VisualizerHandler, {'core': core, 'data':data, 'config':config["zestbox"]})
    ]


class Extension(ext.Extension):
    dist_name = 'Mopidy-Zestbox'
    ext_name = 'zestbox'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        schema['votes_to_skip'] = config.Integer(minimum=0)
        schema['max_tracks'] = config.Integer(minimum=0)
        schema['hide_pause'] = config.Boolean(optional=True)
        schema['hide_skip'] = config.Boolean(optional=True)
        schema['style'] = config.String()
        schema['needs_admin'] = config.String()
        schema['max_results'] = config.Integer(minimum=0, optional=True)
        schema['max_queue_length'] = config.Integer(minimum=0, optional=True)
        schema['background_tracks'] = config.List(optional = True)
        return schema

    def setup(self, registry):
        from .frontend import ZestboxFrontend
        registry.add('frontend', ZestboxFrontend)
        registry.add('http:static', {
            'name': self.ext_name,
            'path': os.path.join(os.path.dirname(__file__), 'static'),
        })
        registry.add('http:app', {
            'name': self.ext_name,
            'factory': lemon_factory,
        })
        
