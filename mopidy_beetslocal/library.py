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
        logger.debug("Search query: %s in uris: %s" % (query, uris))
        if not query:
            logger.debug("No query => browse library")
            # Fetch all data(browse library)
            tracks = self.lib.items()
            return SearchResult(
                uri='beetslocal:search-all',
                tracks=self._parse_query(tracks))
        self._validate_query(query)
        query = self._build_beets_query(query)
        logger.debug('Build Query "%s":' % query)
        tracks = self.lib.items(query)
        logger.debug("Query found %s tracks" % len(tracks))
        albums = self.lib.albums(query)
        logger.debug("Query found %s albums" % len(albums))
        return SearchResult(
            uri='beetslocal:search:' + query.replace(' ', '_'),
            tracks=self._parse_tracks(tracks),
            albums=self._parse_albums(albums))

    def get_track(self, beets_id):
        track = self.lib.get_item(beets_id)
        return self._convert_item(track)

    def get_album(self, beets_id):
        album = self.lib.get_album(beets_id)
        return [self._convert_item(item) for item in album.items()]

    def lookup(self, uri):
        logger.debug("looking up uri = %s of type %s" % (
            uri, type(uri).__name__))
        uri_dict = self.backend._extract_uri(uri)
        item_type = uri_dict['item_type']
        beets_id = uri_dict['beets_id']
        if item_type == 'track':
            try:
                track = self.get_track(beets_id)
                logger.debug('Beets track for id "%s": %s' % (beets_id, uri))
                return [track]
            except Exception as error:
                logger.debug('Failed to lookup "%s": %s' % (uri, error))
                return []
        elif item_type == 'album':
            try:
                tracks = self.get_album(beets_id)
                return tracks
            except Exception as error:
                logger.debug('Failed to lookup "%s": %s' % (uri, error))
                return []
        else:
            logger.debug("Dont know what to do with item_type: %s" % item_type)

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
                elif key == 'artist':
                    beets_query += 'albumartist'
                else:
                    # beets_query += "::(" + "|".join(query[key]) + ") "
                    beets_query += key
            # beets_query += "::(" + "|".join(query[key]) + ") "
            beets_query += ":" + " ".join(query[key]) + " "
        return json.dumps(beets_query.strip())

    def _parse_tracks(self, res):
        tracks = []
        for track in res:
            tracks.append(self._convert_item(track))
        return tracks

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

        if 'bitrate' in item:
            track_kwargs['bitrate'] = item['bitrate']

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
            track_kwargs['uri'] = "beetslocal:track:%s:%s" % (
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

    def _parse_albums(self, res):
        albums = []
        for album in res:
            albums.append(self._convert_album(album))
        return albums

    def _convert_album(self, album):
        if not album:
            return
        album_kwargs = {}
        artist_kwargs = {}

        if 'album' in album:
            album_kwargs['name'] = album['album']

        if 'disctotal' in album:
            album_kwargs['num_discs'] = album['disctotal']

        if 'tracktotal' in album:
            album_kwargs['num_tracks'] = album['tracktotal']

        if 'mb_albumid' in album:
            album_kwargs['musicbrainz_id'] = album['mb_albumid']

        album_kwargs['date'] = None
        if self.backend.use_original_release_date:
            if 'original_year' in album:
                try:
                    d = datetime.datetime(
                        album['original_year'],
                        album['original_month'],
                        album['original_day'])
                    album_kwargs['date'] = '{:%Y-%m-%d}'.format(d)
                except:
                    pass
        else:
            if 'year' in album:
                try:
                    d = datetime.datetime(
                        album['year'],
                        album['month'],
                        album['day'])
                    album_kwargs['date'] = '{:%Y-%m-%d}'.format(d)
                except:
                    pass

        # if 'added' in item:
        #    album_kwargs['last_modified'] = album['added']

        if 'artpath' in album:
            album_kwargs['images'] = [album['artpath']]

        if 'albumartist' in album:
            artist_kwargs['name'] = album['albumartist']

        if 'mb_albumartistid' in album:
            artist_kwargs['musicbrainz_id'] = album['mb_albumartistid']

        if artist_kwargs:
            artist = Artist(**artist_kwargs)
            album_kwargs['artists'] = [artist]

        if 'id' in album:
            album_kwargs['uri'] = "beetslocal:album:%s:" % album['id']

        album = Album(**album_kwargs)
        return album
