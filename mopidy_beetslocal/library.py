from __future__ import unicode_literals

import datetime
import json
import locale
import logging

from mopidy import backend
from mopidy.models import Album, Artist, SearchResult, Track
logger = logging.getLogger(__name__)


class BeetsLocalLibraryProvider(backend.LibraryProvider):

    def __init__(self, *args, **kwargs):
        super(BeetsLocalLibraryProvider, self).__init__(*args, **kwargs)
        import beets.library
        self.lib = beets.library.Library(self.backend.beetslibrary)

    def find_exact(self, query=None, uris=None):
            return self.search(query=query, uris=uris)

    def search(self, query=None, uris=None):
        logger.debug('Query "%s":' % query)
        if not query:
            logger.debug("browse library")
            # Fetch all data(browse library)
            tracks = self.lib.items()
            return SearchResult(
                uri='beetslocal:search-all',
                tracks=self._parse_query(tracks))
        self._validate_query(query)
        query = self._build_beets_query(query)
        logger.debug('Query "%s":' % query)
        tracks = self.lib.items(query)
        return SearchResult(
            uri='beetslocal:search-' + query.replace(' ', '_'),
            tracks=self._parse_query(tracks) or [])

    def get_track(self, id):
        track = self.lib.get_item(id)
        return self._convert_item(track)

    def lookup(self, uri):
        logger.debug("uri = %s of type %s" % (uri, type(uri).__name__))
        id = self.backend._extract_id(uri)
        try:
            track = self.get_track(id)
            logger.debug('Beets track for id "%s": %s' % (id, uri))
            return [track]
        except Exception as error:
            logger.debug('Failed to lookup "%s": %s' % (uri, error))
            return []

    def _validate_query(self, query):
        for (_, values) in query.iteritems():
            if not values:
                raise LookupError('Missing query')
            for value in values:
                if not value:
                    raise LookupError('Missing query')

    def _build_beets_query(self, query):
        beets_query = ""
        for key in query.keys():
            if key != 'any':
                if key == 'track_name':
                    beets_query += 'title'
                else:
                    # beets_query += "::(" + "|".join(query[key]) + ") "
                    beets_query += key
            # beets_query += "::(" + "|".join(query[key]) + ") "
            beets_query += ":" + " ".join(query[key]) + " "
        return json.dumps(beets_query.strip())

    def _parse_query(self, res):
        if len(res) > 0:
            tracks = []
            for track in res:
                tracks.append(self._convert_item(track))
            return tracks
        return None

    def _decode_path(self, path):
        default_encoding = locale.getpreferredencoding()
        decoded_path = None
        try:
            decoded_path = path.decode(default_encoding)
        except:
            pass
        if not decoded_path:
            try:
                decoded_path = path.decode('utf-8')
            except:
                pass
        if not decoded_path:
            try:
                decoded_path = path.decode('ISO-8859-1')
            except:
                pass
        return decoded_path

    def _convert_item(self, item):
        if not item:
            return
        track_kwargs = {}
        album_kwargs = {}
        artist_kwargs = {}
        albumartist_kwargs = {}

        if 'track' in item:
            track_kwargs['track_no'] = int(item['track'])

        if 'tracktotal' in item:
            album_kwargs['num_tracks'] = int(item['tracktotal'])

        if 'artist' in item:
            artist_kwargs['name'] = item['artist']
            albumartist_kwargs['name'] = item['artist']

        if 'albumartist' in item:
            albumartist_kwargs['name'] = item['albumartist']

        if 'album' in item:
            album_kwargs['name'] = item['album']

        if 'title' in item:
            track_kwargs['name'] = item['title']

        if 'disc' in item:
            track_kwargs['disc_no'] = item['disc']

        if 'mtime' in item:
            track_kwargs['last_modified'] = item['mtime']

        track_kwargs['date'] = None
        if self.backend.use_original_release_date:
            if 'original_year' in item:
                try:
                    d = datetime.datetime(
                        item['original_year'],
                        item['original_month'],
                        item['original_day'])
                    track_kwargs['date'] = '{:%Y-%m-%d}'.format(d)
                except:
                    pass
        else:
            if 'year' in item:
                try:
                    d = datetime.datetime(
                        item['year'],
                        item['month'],
                        item['day'])
                    track_kwargs['date'] = '{:%Y-%m-%d}'.format(d)
                except:
                    pass

        if 'mb_trackid' in item:
            track_kwargs['musicbrainz_id'] = item['mb_trackid']

        if 'mb_albumid' in item:
            album_kwargs['musicbrainz_id'] = item['mb_albumid']

        if 'mb_artistid' in item:
            artist_kwargs['musicbrainz_id'] = item['mb_artistid']

        if 'mb_albumartistid' in item:
            albumartist_kwargs['musicbrainz_id'] = (
                item['mb_albumartistid'])

        if 'path' in item:
            track_kwargs['uri'] = "beetslocal:%s:%s" % (
                item['id'],
                self._decode_path(item['path']))

        if 'length' in item:
            track_kwargs['length'] = int(item['length']) * 1000

        if artist_kwargs:
            artist = Artist(**artist_kwargs)
            track_kwargs['artists'] = [artist]

        if albumartist_kwargs:
            albumartist = Artist(**albumartist_kwargs)
            album_kwargs['artists'] = [albumartist]

        if album_kwargs:
            album = Album(**album_kwargs)
            track_kwargs['album'] = album

        track = Track(**track_kwargs)

        return track
