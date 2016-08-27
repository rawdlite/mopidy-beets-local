from __future__ import unicode_literals

import datetime
import logging
import os
import sqlite3
import sys

from mopidy import backend
from mopidy.exceptions import ExtensionError
from mopidy.models import Album, Artist, Ref, SearchResult, Track

from uritools import uricompose, uriencode, urisplit

logger = logging.getLogger(__name__)


class BeetsLocalLibraryProvider(backend.LibraryProvider):
    ROOT_URI = 'beetslocal:root'
    root_directory = Ref.directory(uri=ROOT_URI, name='Local (beets)')

    def __init__(self, *args, **kwargs):
        super(BeetsLocalLibraryProvider, self).__init__(*args, **kwargs)
        try:
            import beets.library
        except:
            logger.error('BeetsLocalBackend: could not import beets library')
        if not os.path.isfile(self.backend.beetslibrary):
            raise ExtensionError('Can not find %s'
                                 % (self.backend.beetslibrary))
        try:
            self.lib = beets.library.Library(self.backend.beetslibrary)
        except sqlite3.OperationalError, e:
            logger.error('BeetsLocalBackend: %s', e)
            raise ExtensionError('Mopidy-BeetsLocal can not open %s',
                                 self.backend.beetslibrary)
        except sqlite3.DatabaseError, e:
            logger.error('BeetsLocalBackend: %s', e)
            raise ExtensionError('Moidy-BeetsLocal can not open %s',
                                 self.backend.beetslibrary)
        except:
            print "Unexpected error:", sys.exc_info()[0]
            pass

    def _find_exact(self, query=None, uris=None):
        logger.debug("Find query: %s in uris: %s" % (query, uris))
        # artists = []
        # import pdb; pdb.set_trace()
        albums = []
        if not (('track_name' in query) or ('composer' in query)):
            # when trackname or composer is queried dont search for albums
            albums = self._find_albums(query)
            logger.debug("Find found %s albums" % len(albums))
        #    artists=self._find_artists(query)
        #    logger.debug("Find found %s artists" % len(artists))
        tracks = self._find_tracks(query)
        # logger.debug(u'Find found %s tracks' % len(tracks))
        return SearchResult(
            uri=uricompose('beetslocal',
                           None,
                           'find',
                           query),
            # artists=artists,
            tracks=tracks,
            albums=albums)

    def search(self, query=None, uris=None, exact=False):
        logger.debug(u'Search query: %s in uris: %s' % (query, uris))
        # import pdb; pdb.set_trace()
        query = self._sanitize_query(query)
        logger.debug(u'Search sanitized query: %s ' % query)
        if exact:
            return self._find_exact(query, uris)
        albums = []
        if not query:
            uri = 'beetslocal:search-all'
            tracks = self.lib.items()
            albums = self.lib.albums()
        else:
            uri = uricompose('beetslocal',
                             None,
                             'search',
                             query)
            track_query = self._build_beets_track_query(query)
            logger.debug(u'Build Query "%s":' % track_query)
            tracks = self.lib.items(track_query)
            if 'track_name' not in query:
                # when trackname queried dont search for albums
                album_query = self._build_beets_album_query(query)
                logger.debug('Build Query "%s":' % album_query)
                albums = self.lib.albums(album_query)
        logger.debug(u"Query found %s tracks and %s albums"
                     % (len(tracks), len(albums)))
        return SearchResult(
            uri=uri,
            tracks=[self._convert_item(track) for track in tracks],
            albums=[self._convert_album(album) for album in albums]
        )

    def browse(self, uri):
        logger.debug(u"Browse being called for %s" % uri)
        level = urisplit(uri).path
        query = self._sanitize_query(dict(urisplit(uri).getquerylist()))
        logger.debug("Got parsed to level: %s - query: %s" % (level,
                                                              query))
        result = []
        if not level:
            logger.error("No level for uri %s" % uri)
            # import pdb; pdb.set_trace()
        if level == 'root':
            for row in self._browse_genre():
                result.append(Ref.directory(
                    uri=uricompose('beetslocal',
                                   None,
                                   'genre',
                                   dict(genre=row[0])),
                    name=row[0] if bool(row[0]) else u'No Genre'))
        elif level == "genre":
            # artist refs not browsable via mpd
            for row in self._browse_artist(query):
                result.append(Ref.directory(
                    uri=uricompose('beetslocal',
                                   None,
                                   'artist',
                                   dict(genre=query['genre'][0],
                                        artist=row[1])),
                    name=row[0] if bool(row[0]) else u'No Artist'))
        elif level == "artist":
            for album in self._browse_album(query):
                result.append(Ref.album(
                    uri=uricompose('beetslocal',
                                   None,
                                   'album',
                                   dict(album=album.id)),
                    name=album.album))
        elif level == "album":
            for track in self._browse_track(query):
                result.append(Ref.track(
                    uri="beetslocal:track:%s:%s" % (
                        track.id,
                        uriencode(track.path, '/')),
                    name=track.title))
        else:
            logger.debug('Unknown URI: %s', uri)
        # logger.debug(result)
        return result

    def lookup(self, uri):
        logger.debug(u'looking up uri = %s of type %s' % (
            uri.encode('ascii', 'ignore'), type(uri).__name__))
        uri_dict = self.backend._extract_uri(uri)
        item_type = uri_dict['item_type']
        beets_id = uri_dict['beets_id']
        logger.debug('item_type: "%s", beets_id: "%s"' % (item_type, beets_id))
        if item_type == 'track':
            try:
                track = self._get_track(beets_id)
                logger.debug(u'Beets track for id "%s": %s' %
                             (beets_id, uri.encode('ascii', 'ignore')))
                return [track]
            except Exception as error:
                logger.debug(u'Failed to lookup "%s": %s' % (uri, error))
                return []
        elif item_type == 'album':
            try:
                tracks = self._get_album(beets_id)
                return tracks
            except Exception as error:
                logger.debug(u'Failed to lookup "%s": %s' % (uri, error))
                return []
        else:
            logger.debug(u"Dont know what to do with item_type: %s" %
                         item_type)
            return []

    def get_distinct(self, field, query=None):
        logger.warn(u'get_distinct called field: %s, Query: %s' % (field,
                                                                   query))
        query = self._sanitize_query(query)
        logger.debug(u'Search sanitized query: %s ' % query)
        result = []
        if field == 'artist':
            result = self._browse_artist(query)
        elif field == 'genre':
            result = self._browse_genre()
        else:
            logger.info(u'get_distinct not fully implemented yet')
            result = []
        return set([v[0] for v in result])

    def _get_track(self, beets_id):
        track = self.lib.get_item(beets_id)
        return self._convert_item(track)

    def _get_album(self, beets_id):
        album = self.lib.get_album(beets_id)
        return [self._convert_item(item) for item in album.items()]

    def _browse_track(self, query):
        return self.lib.items('album_id:\'%s\'' % query['album'][0])

    def _browse_album(self, query):
        logger.debug(u'browse_album query: %s' % query)
        return self.lib.albums('mb_albumartistid:\'%s\' genre:\'%s\''
                               % (query['artist'][0], query['genre'][0]))

    def _browse_artist(self, query=None):
        statement = 'select Distinct albumartist, mb_albumartistid from albums'
        if query:
            statement += ' where 1=1 '
            statement += self._build_statement(query, 'genre', 'genre')
            statement += self._build_statement(query, 'artist', 'albumartist')
            statement += self._build_statement(query, 'album', 'album')
            statement += self._build_statement(query, 'mb_albumid',
                                                      'mb_albumid')
            statement += self._build_statement(query, 'date', 'year')
        statement += ' order by albumartist'
        logger.debug('browse_artist: %s' % statement)
        return self._query_beets_db(statement)

    def _browse_genre(self):
        return self._query_beets_db('select Distinct genre '
                                    'from albums order by genre')

    def _query_beets_db(self, statement):
        result = []
        logger.debug(statement)
        with self.lib.transaction() as tx:
            try:
                result = tx.query(statement)
            except:
                # import pdb; pdb.set_trace()
                logger.error('Statement failed: %s' % statement)
                pass
        return result

    def _sanitize_query(self, query):
        """
        We want a consistent query structure that later code
        can rely on
        """
        # import pdb; pdb.set_trace()
        if not query:
            return query
        for (key, values) in query.iteritems():
            if not values:
                del query[key]
            if type(values) is not list:
                query[key] = [values]
            for index, value in enumerate(values):
                if key == 'date':
                    year = self._sanitize_year(str(value))
                    if year:
                        query[key][index] = year
                    else:
                        del query[key][index]
                    # we possibly could introduce query['year'],
                    # query['month'] etc.
                    # Maybe later
        return query

    def _sanitize_year(self, datestr):
        """
        Clients may send date field as Date String, Year or Zero
        """
        try:
            year = str(datetime.datetime.strptime(datestr, '%Y').date().year)
        except:
            try:
                year = str(datetime.datetime.strptime(datestr,
                                                      '%Y-%m-%d').date().year)
            except:
                year = None
        return year

    def _build_statement(self, query, query_key, beets_key):
        """
        A proper mopidy query has a Array of values
        Queries from mpd and browse requests hav strings
        """
        statement = ""
        if query_key in query:
            for query_string in query[query_key]:
                if '"' in query_string:
                    statement += " and %s = \'%s\' " % (beets_key,
                                                        query_string)
                else:
                    statement += ' and %s = \"%s\" ' % (beets_key,
                                                        query_string)
        return statement

    def _build_date(self, year, month, day):
        month = 1 if month == 0 else month
        day = 1 if day == 0 else day
        try:
            d = datetime.datetime(
                year,
                month,
                day)
            date = '{:%Y-%m-%d}'.format(d)
        except:
            date = None
        return date

    def _find_tracks(self, query):
        statement = ('select id, title, day, month, year, artist, album, '
                     'composer, track, disc, length,  bitrate, comments, '
                     'mb_trackid, mtime, genre, tracktotal, disctotal, '
                     'mb_albumid, mb_albumartistid, albumartist, mb_artistid '
                     'from items where 1=1 ')
        statement += self._build_statement(query, 'track_name', 'title')
        statement += self._build_statement(query, 'genre', 'genre')
        statement += self._build_statement(query, 'artist', 'artist')
        statement += self._build_statement(query, 'album', 'album')
        statement += self._build_statement(query, 'composer', 'composer')
        statement += self._build_statement(query, 'mb_trackid', 'mb_trackid')
        statement += self._build_statement(query, 'mb_albumid', 'mb_albumid')
        statement += self._build_statement(query,
                                           'mb_albumartistid',
                                           'mb_albumartistid')
        statement += self._build_statement(query, 'date', 'year')
        tracks = []
        result = self._query_beets_db(statement)
        for row in result:
            date = self._build_date(row[4], row[3], row[2])
            artist = Artist(name=row[5],
                            musicbrainz_id=row[21],
                            uri=uricompose('beetslocal',
                                           None,
                                           'artist:%s:' % row[21]))
            albumartist = Artist(name=row[20],
                                 musicbrainz_id=row[19],
                                 uri=uricompose('beetslocal',
                                                None,
                                                'artist:%s:' % row[19]))
            composer = Artist(name=row[7],
                              musicbrainz_id='',
                              uri=uricompose('beetslocal',
                                             None,
                                             'composer:%s:' % row[7]))
            album = Album(name=row[6],
                          date=date,
                          artists=[albumartist],
                          num_tracks=row[16],
                          num_discs=row[17],
                          musicbrainz_id=row[18],
                          uri=uricompose('beetslocal',
                                         None,
                                         'mb_album:%s:' % row[18]))
            tracks.append(Track(name=row[1],
                                artists=[artist],
                                album=album,
                                composers=[composer],
                                track_no=row[8],
                                disc_no=row[9],
                                date=date,
                                length=int(row[10] * 1000),
                                bitrate=row[11],
                                comment=row[12],
                                musicbrainz_id=row[13],
                                last_modified=int(row[14] * 1000),
                                genre=row[15],
                                uri=uricompose('beetslocal',
                                               None,
                                               'track:%s:' % row[0])))
        return tracks

    def _find_albums(self, query):
        statement = ('select id, album, day, month, year, '
                     'albumartist, disctotal, '
                     'mb_albumid, artpath, mb_albumartistid '
                     'from albums where 1=1 ')
        statement += self._build_statement(query, 'genre', 'genre')
        statement += self._build_statement(query, 'artist', 'albumartist')
        statement += self._build_statement(query, 'album', 'album')
        statement += self._build_statement(query, 'mb_albumid', 'mb_albumid')
        statement += self._build_statement(query, 'date', 'year')
        result = self._query_beets_db(statement)
        albums = []
        for row in result:
            date = self._build_date(row[4], row[3], row[2])
            artist = Artist(name=row[5],
                            musicbrainz_id=row[9],
                            uri=uricompose('beetslocal',
                                           None,
                                           'artist:%s:' % row[9]))
            albums.append(Album(name=row[1],
                                date=date,
                                artists=[artist],
                                # num_tracks=row[6],
                                num_discs=row[6],
                                musicbrainz_id=row[7],
                                # images=[row[8]],
                                uri=uricompose('beetslocal',
                                               None,
                                               'album:%s:' % row[0])))
        return albums

    def _find_artists(self, query):
        statement = ('select Distinct albumartist, mb_albumartistid'
                     ' from albums where 1=1 ')
        statement += self._build_statement(query, 'genre', 'genre')
        statement += self._build_statement(query, 'artist', 'albumartist')
        statement += self._build_statement(query, 'date', 'year')
        statement += self._build_statement(query,
                                           'mb_albumartistid',
                                           'mb_albumartistid')
        artists = []
        result = self._query_beets_db(statement)
        for row in result:
            artists.append(Artist(name=row[0],
                                  musicbrainz_id=row[1],
                                  uri=uricompose('beetslocal',
                                                 None,
                                                 'artist:%s:' % row[1])))
        return artists

    def _build_beets_track_query(self, query):
        """
        Transforms a mopidy query into beets
        query syntax
        """
        beets_query = ""
        for key in query.keys():
            if key != 'any':
                if key == 'track_name':
                    beets_query += 'title'
                else:
                    beets_query += key
            # beets_query += "::(" + "|".join(query[key]) + ") "
            beets_query += ":" + " ".join(query[key]) + " "
            logger.info(beets_query)
        return '\'%s\'' % beets_query.strip()

    def _build_beets_album_query(self, query):
        """
        Transforms a mopidy query into beets
        query syntax
        """
        beets_query = ""
        for key in query.keys():
            if key != 'any':
                if key == 'artist':
                    beets_query += 'albumartist'
                else:
                    beets_query += key
            beets_query += ":" + " ".join(query[key]) + " "
            logger.info(beets_query)
        return '\'%s\'' % beets_query.strip()

    def _convert_item(self, item):
        """
        Transforms a beets item into a mopidy Track
        """
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

        if 'genre' in item:
            track_kwargs['genre'] = item['genre']

        if 'comments' in item:
            track_kwargs['comment'] = item['comments']

        if 'bitrate' in item:
            track_kwargs['bitrate'] = item['bitrate']

        if 'mtime' in item:
            track_kwargs['last_modified'] = int(item['mtime'] * 1000)

        if self.backend.use_original_release_date:
            if 'original_year' in item:
                track_kwargs['date'] = self._build_date(
                                       item['original_year'],
                                       item['original_month'],
                                       item['original_day'])
        else:
            if 'year' in item:
                track_kwargs['date'] = self._build_date(
                                       item['year'],
                                       item['month'],
                                       item['day'])

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
                uriencode(item['path'], '/'))

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

    def _convert_album(self, album):
        """
        Transforms a beets album into a mopidy Track
        """
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
                    album_kwargs['date'] = self._build_date(
                                                album['original_year'],
                                                album['original_month'],
                                                album['original_day'])
        else:
            if 'year' in album:
                    album_kwargs['date'] = self._build_date(album['year'],
                                                            album['month'],
                                                            album['day'])

        # if 'added' in item:
        #    album_kwargs['last_modified'] = album['added']

        # if 'artpath' in album:
        #    album_kwargs['images'] = [album['artpath']]

        if 'albumartist' in album:
            artist_kwargs['name'] = album['albumartist']

        if 'mb_albumartistid' in album:
            artist_kwargs['musicbrainz_id'] = album['mb_albumartistid']

        if artist_kwargs:
            artist = Artist(**artist_kwargs)
            album_kwargs['artists'] = [artist]

        if 'id' in album:
            album_kwargs['uri'] = uricompose('beetslocal',
                                             None,
                                             'album:%s:' % album['id'])

        album = Album(**album_kwargs)
        return album
