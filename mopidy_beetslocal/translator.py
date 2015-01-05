from __future__ import unicode_literals

import urllib


def build_uri(variant, identifier):
    return b'beetslocal:%s:%s' % (variant,
                                  urllib.quote(identifier.encode('utf8')))


def parse_uri(uri):
    res = uri.split(':', 2)
    if len(res) == 1:
        return None, None
    elif len(res) == 2:
        return res[1], None
    elif len(res) == 3:
        return res[1], urllib.unquote(res[2].decode('utf8'))
