from __future__ import unicode_literals

import logging
import os

from mopidy import config, ext

__version__ = '0.0.9'

logger = logging.getLogger(__name__)


class Extension(ext.Extension):
    dist_name = u'Mopidy-BeetsLocal'
    ext_name = u'beetslocal'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), u'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        schema[u'beetslibrary'] = config.Path()
        schema[u'use_original_release_date'] = config.Boolean(optional=True)
        return schema

    def setup(self, registry):
        from actor import BeetsLocalBackend
        registry.add(u'backend', BeetsLocalBackend)
