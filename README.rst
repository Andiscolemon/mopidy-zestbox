****************************
Mopidy-Zestbox
****************************

UNDER CONSTRUCTION!
=============

Fork of `Mopidy-Party <https://github.com/Lesterpig/mopidy-party>`_, see their work first!
ALL CREDIT FOR THE ORIGINAL MOPIDY-PARTY EXTENSION GOES TO 
`Lesterpig <https://github.com/Lesterpig/>`_, `grasdk <https://github.com/grasdk>`_, `girst <https://github.com/girst>`_ AND ALL OTHER CONTRIBUTORS OF MOPIDY-PARTY 
Extension of a Mopidy web extension aiming to enhance the feature set of Mopidy-Party!

=====

To use the interface, simply use your browser to visit your Mopidy instance's IP at port 6680 to see all available web interfaces.
For example, http://192.168.0.2:6680/

Web UI for Mopidy-Zestbox is located at: http://192.168.0.2:6680/zestbox/

Configuration
=============

::

    [zestbox]
    enabled = true
    votes_to_skip = 3     # Votes needed from different users to allow skipping a song.
    max_tracks = 0        # Maximum number of tracks that can be added by a single user in a row, 0 for unlimited
    max_results = 50      # Maximum number of tracks to show when searching / browsing on a single page
    max_queue_length = 0  # Maximum number of tracks queued at the same time, 0 for unlimited
    hide_pause = false    # Change to true to hide the pause button
    hide_skip = false     # Change to true to hide the skip button
    style = zestbox.css   # Stylesheet to use.
    needs_admin = false   # Not yet implemented. Will be used to enable admin override functionality 
    background_tracks =   # List of track URIs to play automatically in the background when nothing else is queued
::
