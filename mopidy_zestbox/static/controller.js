'use strict';

// TODO : add a mopidy service designed for angular, to avoid ugly $scope.$apply()...
angular.module('zestboxApp', [])
  .controller('MainController', function ($scope, $http, $timeout, $interval) {

    // Scope variables
    $scope.trackSelected = {};

    $scope.trackRequester = {name: "An Anonymous Lemon"};


    $scope.query = {} // Why the hell did this break?
    $scope.message = [];
    $scope.tracks = [];
    $scope.tracksToLookup = [];
    $scope.maxTracksToLookup = 50; // Will be overwritten later by module config
    $scope.initialized = false;
    $scope.admin = "";
    $scope.loading = true;
    $scope.ready = false;
    $scope.coverImages = [];
    $scope.currentState = {
      reqName: "",
      currentVotes: 0,
      votesNeeded: 0,
      playingUserTrack: false,
      paused: false,
      length: 0,
      coverImage: "./src/thumbnail-fb.png",
      track: {
        length: 0,
        name: 'Nothing playing right now! Add default background tracks to config or queue a song!'
      }
    };
    $scope.trackProgress = 0;

    // Get the max tracks to lookup and background tracks at once from the config values in mopidy.conf
    $http.get('/zestbox/config?key=max_results').then(function success(response) {
      if (response.status == 200) {
        $scope.maxTracksToLookup = +response.data;
      }
    }, null);

    var mopidy = new Mopidy({
      'callingConvention': 'by-position-or-by-name'
    });

    mopidy.on('state:online', function () {
      $http.get("/zestbox/control").then(function success(response) {
        var data = response.data;
        $scope.initialized = data.sessionStarted;
        $scope.currentState.currentVotes = data.votesAdded;
        $scope.currentState.votesNeeded = data.votesNeeded;
        $scope.currentState.playingUserTrack = data.userTrack;
        $scope.currentState.paused = data.paused;
        $scope.currentState.length = data.playlistLength;
        $scope.currentState.reqName = data.requestedBy;
        $scope.currentState.coverImage = data.imgUri
        if(data.currentTrack){
          $scope.currentState.track = data.currentTrack;
          mopidy.playback.getTimePosition().done(function(time) {
            $scope.trackProgress = time;
          });
        }
        else {
          $scope.trackProgress = 0
        }
        return data
      }, null).then(function (data) {
        $timeout(function () {
          $scope.ready = true;
          $scope.loading = false;
          $scope.search();
          $scope.$apply()
        }, 10)
      });
    });

    mopidy.on('event:playbackStateChanged', function (event) {
      $scope.refreshData();
      $scope.$apply();
    });
    mopidy.on('event:trackPlaybackStarted', function (event) {
      $scope.refreshData();
      $scope.$apply();
    });
    mopidy.on('event:tracklistChanged', function (event) {
      $scope.refreshData();
      $scope.$apply();
    });

    $scope.refreshData = function () {
      if (!$scope.ready)
        return
      $http.get("/zestbox/control").then(function success(response) {
        $timeout(function () {
          var data = response.data;
          $scope.initialized = data.sessionStarted;
          $scope.currentState.currentVotes = data.votesAdded;
          $scope.currentState.votesNeeded = data.votesNeeded;
          $scope.currentState.playingUserTrack = data.userTrack;
          $scope.currentState.paused = data.paused;
          $scope.currentState.length = data.playlistLength;
          $scope.currentState.reqName = data.requestedBy;
          $scope.currentState.coverImage = data.imgUri
          $scope.ready = true;
          $scope.loading = false;
          if(data.currentTrack) {
            $scope.currentState.track = data.currentTrack;
            mopidy.playback.getTimePosition().done(function(time) {
              $scope.trackProgress = time;
            });
          }
        }, 10);
      }, null)
    };
      
    $scope.printDuration = function (length) {
      if (length < 1)
        return '';

      var _sum = length / 1000;
      var _min = _sum / 60;
      var _sec = _sum % 60;

      return '(' + Math.trunc(_min) + ':' + (_sec < 10 ? '0' + Math.trunc(_sec) : Math.trunc(_sec)) + ')';
    };

    $scope.search = function () {
      $scope.message = [];
      $scope.loading = true;

      console.log($scope.query.text)
      if (!$scope.query.text) {
        mopidy.library.browse({
          'uri': 'local:directory'
        }).done($scope.handleBrowseResult);
        return;
      }
      
      mopidy.library.search({
        'query': {
          'any': [$scope.query.text]
        }
      }).done($scope.handleSearchResult);
    };

    $scope.handleBrowseResult = function (res) {
      $scope.loading = false;
      $scope.tracks = [];
      $scope.tracksToLookup = [];

      for (var i = 0; i < res.length; i++) {
        if (res[i].type == 'directory' && res[i].uri == 'local:directory?type=track') {
          mopidy.library.browse({
            'uri': res[i].uri
          }).done($scope.handleBrowseResult);
        } else if (res[i].type == 'track') {
          $scope.tracksToLookup.push(res[i].uri);
        }
      }

      if ($scope.tracksToLookup) {
        $scope.lookupOnePageOfTracks();
      }
    };

    $scope.lookupOnePageOfTracks = function () {
      mopidy.library.lookup({ 'uris': $scope.tracksToLookup.splice(0, $scope.maxTracksToLookup) }).done(function (tracklistResult) {
        Object.values(tracklistResult).map(function(singleTrackResult) { return singleTrackResult[0]; }).forEach($scope.addTrackResult);
      });
    };


    $scope.handleSearchResult = function (res) {
      $scope.loading = false;
      $scope.tracks = [];
      $scope.tracksToLookup = [];

      var _index = 0;
      var _found = true;
      while (_found && _index < $scope.maxTracksToLookup) {
        _found = false;
        for (var i = 0; i < res.length; i++) {
          if (res[i].tracks && res[i].tracks[_index]) {
            $scope.addTrackResult(res[i].tracks[_index]);
            _found = true;
          }
        }
        _index++;
      }

      $scope.$apply();
    };

    $scope.addTrackResult = function (track) {
      $scope.tracks.push(track);
      mopidy.tracklist.filter([{ 'uri': [track.uri] }]).done(
        function (matches) {
          if (matches.length) {
            for (var i = 0; i < $scope.tracks.length; i++) {
              if ($scope.tracks[i].uri == matches[0].track.uri)
                $scope.tracks[i].disabled = true;
            }
          }
          $scope.$apply();
        });
    };

    $scope.addTrackDialog = function(track) {
      $scope.trackSelected = track;
    }

    $scope.addTrack = function (track) {
      track.disabled = true;

      $http.post('/zestbox/add', {"uri": track.uri, "user": $scope.trackRequester.name}).then(
        function success(response) {
          $scope.message = ['success', 'Queued: ' + track.name];
        },
        function error(response) {
          if (response.status === 409) {
            $scope.message = ['error', '' + response.data];
          } else {
            $scope.message = ['error', 'Code ' + response.status + ' - ' + response.data];
          }
        }
      );
    };

    $scope.nextTrack = function () {
      $http.get('/zestbox/vote').then(
        function success(response) {
          $scope.message = ['success', '' + response.data];
        },
        function error(response) {
          $scope.message = ['error', '' + response.data];
        }
      );
    };

    $scope.getTrackSource = function (track) {
      var sourceAsText = 'unknown';
      if (track.uri) {
        sourceAsText = track.uri.split(':', '1')[0];
      }

      return sourceAsText;
    };

    $scope.getTrackCoverImage = function (track) {
      if (!track) return;
      if (track.uri) {  
          mopidy.library.getImages({"uris": [track.uri]})
          .then(function (results) {
          $scope.currentState.coverImage = Object.values(results)[0][0].uri; }, 
          function () { 
            $scope.currentState.coverImage = "./src/thumbnail-fb.png"; 
            $scope.$apply();
          });
      }};

    $scope.getFontAwesomeIcon = function (source) {
      var sources_with_fa_icon = ['bandcamp', 'mixcloud', 'soundcloud', 'spotify', 'youtube'];
      var css_class = 'fa fa-music';

      if (source == 'local') {
        css_class = 'fa fa-folder';
      } else if (sources_with_fa_icon.includes(source)) {
        css_class = 'fa-brands fa-' + source;
      }

      return css_class;
    };

    $scope.togglePause = function () {
      $http.post('/zestbox/control', {command: $scope.currentState.paused ? 'resume' : 'paused'});
    };

    $scope.init_session = function () {
      $http.post('/zestbox/control', {command: "start", backgroundPlaylist: [], adminPassphrase: ""})
      .then(function () {
        $scope.initialized = true;
      }); // TODO: Add actual session customization through web UI. 
    };

    $interval(function () {
      if($scope.currentState.track && $scope.currentState.track.length > 0 && $scope.trackProgress < $scope.currentState.track.length) {
        $scope.trackProgress += 1000; 
      }
    }, 1000);
  });
