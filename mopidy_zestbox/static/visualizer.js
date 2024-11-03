'use strict';

angular.module('visualizerApp', [])
  .controller('MainController', function ($scope, $http) {

    $scope.loading = true;
    $scope.ready = false;
    $scope.currentState = {
      paused: false,
      track: {
        length: 0,
        name: 'Nothing is playing!'
      }
    };

    var player = new IcecastMetadataPlayer(
      "http://127.0.0.1:9001/icecast", {}
    );

    import('https://cdn.skypack.dev/audiomotion-analyzer?min').then( AudioMotionAnalyzer => {
      var audiomotion = new AudioMotionAnalyzer.default(
        document.getElementById("visualizer"),
        {
          source: player.audioElement,
          height: 200,
          mode: 3,
          connectSpeakers: false
        }
      )});

    var mopidy = new Mopidy({
      'callingConvention': 'by-position-or-by-name'
    });

    mopidy.on('state:online', function () {
      mopidy.playback
        .getCurrentTrack()
        .then(function (track) {
          if (track)
            $scope.currentState.track = track;
          return mopidy.playback.getState();
        })
        .then(function (state) {
          $scope.currentState.paused = (state === 'paused');
        })
        .done(function () {
          $scope.ready = true;
          $scope.loading = false;
          $scope.$apply();
        });
    });

    mopidy.on('event:playbackStateChanged', function (event) {
      $scope.currentState.paused = (event.new_state === 'paused');
      $scope.$apply();
    });

    mopidy.on('event:trackPlaybackStarted', function (event) {
      $scope.currentState.track = event.tl_track.track;
      $scope.$apply();
    });

    mopidy.on('event:tracklistChanged', function () {
      mopidy.tracklist.getLength().done(function (length) {
        $scope.currentState.length = length;
        $scope.$apply();
      });
    });

    $scope.printDuration = function (track) {
      if (!track.length)
        return '';

      var _sum = parseInt(track.length / 1000);
      var _min = parseInt(_sum / 60);
      var _sec = _sum % 60;

      return '(' + _min + ':' + (_sec < 10 ? '0' + _sec : _sec) + ')';
    };

    $scope.getTrackSource = function (track) {
      var sourceAsText = 'unknown';
      if (track.uri) {
        sourceAsText = track.uri.split(':', '1')[0];
      }

      return sourceAsText;
    };

    $scope.getTrackCoverImage = function (track) {
      var imageUri = "./src/thumbnail-fb.png";
      if (track.uri) {
        imageUri = mopidy.library.getImages({"uris": [track.uri]})[track.uri].uri;
      }
      return imageUri;
    }

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
      var _fn = $scope.currentState.paused ? mopidy.playback.resume : mopidy.playback.pause;
      _fn().done();
    };
  });
