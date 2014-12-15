import logging
import pykka

from mopidy import backend

from .library import BeetsLocalLibraryProvider

logger = logging.getLogger(__name__)


class BeetsLocalBackend(pykka.ThreadingActor, backend.Backend):

    def __init__(self, config, audio):
        super(BeetsLocalBackend, self).__init__()

        self.beetslibrary = config['beetslocal']['beetslibrary']
        logger.debug("Got brary %s" % (self.beetslibrary))
        self.library = BeetsLocalLibraryProvider(backend = self)
        self.playlists = None

        self.uri_schemes = ['beetslocal']

