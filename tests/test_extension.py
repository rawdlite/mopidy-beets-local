from __future__ import unicode_literals

import unittest

import mock

from mopidy_beetslocal import Extension, actor as backend_lib


class ExtensionTest(unittest.TestCase):

    def test_get_default_config(self):
        ext = Extension()

        config = ext.get_default_config()

        self.assertIn('[beetslocal]', config)
        self.assertIn('enabled = true', config)
        self.assertIn('beetslibrary =', config)
        self.assertIn('use_original_release_date', config)

    def test_get_config_schema(self):
        ext = Extension()

        schema = ext.get_config_schema()
        self.assertIn('enabled', schema)
        self.assertIn('beetslibrary', schema)

    def test_setup(self):
        registry = mock.Mock()
        ext = Extension()
        ext.setup(registry)
        registry.add.assert_called_with(
            'backend',
            backend_lib.BeetsLocalBackend)
