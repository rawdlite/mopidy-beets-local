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

    def _extract_uri(self, uri):
        logger.debug("convert uri = %s" % uri.encode('ascii', 'ignore'))
        if not uri.startswith('beetslocal:'):
            raise ValueError('Invalid URI.')
        path = uri.split(b':', 3)[3]
        beets_id = uri.split(b':', 3)[2]
        item_type = uri.split(b':', 3)[1]
        logger.debug("extracted path = %s id = %s type = %s" % (
            path.encode('ascii', 'ignore'), beets_id, item_type))
        return {'path': path,
                'beets_id': int(beets_id),
                'item_type': item_type}


class BeetsLocalPlaybackProvider(backend.PlaybackProvider):

    def translate_uri(self, uri):
        logger.debug('translate_uri called %s', uri)
        local_uri = 'file://%s' % self.backend._extract_uri(uri)['path']
        logger.debug('local_uri: %s' % local_uri)
        return local_uri
