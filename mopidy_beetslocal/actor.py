import logging

from mopidy import backend

import pykka

from .library import BeetsLocalLibraryProvider

logger = logging.getLogger(__name__)


class BeetsLocalBackend(pykka.ThreadingActor, backend.Backend):

    def __init__(self, config, audio):
        super(BeetsLocalBackend, self).__init__()
        self.beetslibrary = config['beetslocal']['beetslibrary']
        self.use_original_release_date = config['beetslocal'][
            'use_original_release_date']
        logger.debug("Got library %s" % (self.beetslibrary))
        self.playback = BeetsLocalPlaybackProvider(audio=audio, backend=self)
        self.library = BeetsLocalLibraryProvider(backend=self)
        self.playlists = None
        self.uri_schemes = ['beetslocal']

    def _extract_path(self, path):
        logger.debug("convert path = %s" % path)
        if not path.startswith('beetslocal:'):
            raise ValueError('Invalid URI.')
        path = path.split(b':', 2)[2]
        logger.debug("extracted path = %s" % path)
        return path

    def _extract_id(self, path):
        logger.debug("convert path = %s" % path)
        if not path.startswith('beetslocal:'):
            raise ValueError('Invalid URI.')
        id = path.split(b':', 2)[1]
        logger.debug("extracted id = %s" % id)
        return id


class BeetsLocalPlaybackProvider(backend.PlaybackProvider):

    def play(self, track):
        local_track = track.copy(uri="file://%s" %
                                 self.backend._extract_path(track.uri))
        return super(BeetsLocalPlaybackProvider, self).play(local_track)
