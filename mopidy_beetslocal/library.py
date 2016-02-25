from __future__ import unicode_literals

import datetime
import locale
import logging
import os
import sqlite3
import sys

from mopidy import backend
from mopidy.exceptions import ExtensionError
from mopidy.models import Album, Artist, Ref, SearchResult, Track

from uritools import uricompose, urisplit

logger = logging.getLogger(__name__)


class BeetsLocalLibraryProvider(backend.LibraryProvider):
    ROOT_URI = 'beetslocal:root'
    root_directory = Ref.directory(uri=ROOT_URI, name='Local (beets)')
    FIRST_LEVEL = ['Grouping','Genre','Mood','Format','Samplerate','Year','Compilations','Added At']
    ADDED_LEVEL = ['Last Month','Last Week','Last Day']

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
        albums = []
        if not (('track_name' in query) or ('composer' in query)):
            # when trackname or composer is queried dont search for albums
            albums = self._find_albums(query)
            logger.debug('Find found %s albums' % len(albums))
        #    artists=self._find_artists(query)
        #    logger.debug("Find found %s artists" % len(artists))
        try:
            tracks = self._find_tracks(query)
        except:
            logger.debug("EX = %s", sys.exc_info()[0])
            import pdb; pdb.set_trace()
        logger.debug('Find found %s tracks' % len(tracks))
        return SearchResult(
            uri=uricompose('beetslocal',
                           None,
                           'find',
                           query),
            # artists=artists,
            albums=albums,
            tracks=tracks)

    def search(self, query=None, uris=None, exact=False):
        logger.debug('Search query: %s in uris: %s' % (query, uris))
        # import pdb; pdb.set_trace()
        query = self._sanitize_query(query)
        logger.debug('Search sanitized query: %s ' % query)
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
            logger.debug('Build Query "%s":', track_query)
            tracks = self.lib.items(track_query)
            if 'track_name' not in query:
                # when trackname queried dont search for albums
                album_query = self._build_beets_album_query(query)
                logger.debug('Build Query "%s":', album_query)
                albums = self.lib.albums(album_query)
        logger.debug('Query found %s tracks and %s albums',
                     (len(tracks), len(albums)))
        return SearchResult(
            uri=uri,
            tracks=[self._convert_item(track) for track in tracks],
            albums=[self._convert_album(album) for album in albums]
        )

    def browse(self, uri):
        logger.debug('Browse being called for %s', uri)
        level = urisplit(uri).path
        query = self._sanitize_query(dict(urisplit(uri).getquerylist()))
        logger.debug('Got parsed to level: %s - query: %s',
                     level,
                     query)
        result = []
        if not level:
            logger.error('No level for uri %s', uri)
            # import pdb; pdb.set_trace()
        if level == 'root':
            return list(self._browse_root())
        elif level == "compilations":
            return list(self._browse_compilations())
        elif level == "format":
            return list(self._browse_format())
        elif level == "samplerate":
            return list(self._browse_samplerate())
        elif level == "year":
            return list(self._browse_year())
        elif level == "mood":
            return list(self._browse_mood())
        elif level == "grouping":
            return list(self._browse_grouping())
        elif level == "genre":
            all_artists = []
            if 'grouping' in query:
                url_query = {}
                for k, v in query.items():
                    url_query[k] = v[0]
                all_artists = [Ref.directory(
                    uri=uricompose('beetslocal',
                                   None,
                                   'artist',
                                   url_query),
                    name='All Artists')]
            return (all_artists +
                    list(self._browse_genre(query)))
        elif level == "artist":
            url_query = {}
            for k, v in query.items():
                url_query[k] = v[0]
            all_albums = [Ref.directory(
                uri=uricompose('beetslocal',
                               None,
                               'album',
                               url_query),
                name='All albums')]
            return (all_albums + list(self._browse_artist(query)))
        elif level == "album":
            return list(self._browse_album(query))
        elif level == "track":
            return list(self._browse_track(query))
        else:
            logger.debug('Unknown URI: %s', uri)
        # logger.debug(result)
        return result

    def lookup(self, uri):
        logger.debug("looking up uri = %s of type %s" % (
            uri.encode('ascii', 'ignore'), type(uri).__name__))
        uri_dict = self.backend._extract_uri(uri)
        item_type = uri_dict['item_type']
        beets_id = uri_dict['beets_id']
        logger.debug('item_type: "%s", beets_id: "%s"' % (item_type, beets_id))
        if item_type == 'track':
            try:
                track = self._get_track(beets_id)
                logger.debug('Beets track for id "%s": %s' %
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
            result = [ref.name for ref in self._browse_artist(query)]
        elif field == 'genre':
            result = [ref.name for ref in self._browse_genre()]
        else:
            logger.info(u'get_distinct not fully implemented yet')
            result = []
        return set(result)

    def _get_track(self, beets_id):
        track = self.lib.get_item(beets_id)
        return self._convert_item(track)

    def _get_album(self, beets_id):
        album = self.lib.get_album(beets_id)
        return [self._convert_item(item) for item in album.items()]

    def _browse_root(self):
        for row in self.FIRST_LEVEL:
            yield Ref.directory(
                uri=uricompose('beetslocal',
                               None,
                               row.lower(),
                               None),
                name=row)

    def _browse_track(self, query):
        tracks =  self.lib.items(['album_id:%s' % query['album'][0]])
        for track in tracks:
            yield Ref.track(
                uri="beetslocal:track:%s:%s" % (track.id,
                                                track.path.decode('utf8')),
                name=track.title)


    def _browse_album(self, query):
        logger.debug(u'browse_album query: %s' % query)
        # import pdb; pdb.set_trace()
        beets_query = []
        if 'mb_artistid' in query:
            beets_query.append('mb_albumartistid:%s' % query['mb_artistid'][0])
        for key in ('albumartist', 'genre', 'year'):
            if key in query:
                beets_query.append('%s:%s' % (key, query[key][0]))
        logger.debug('beets_query %s', beets_query)
        for album in self.lib.albums(beets_query):
            yield Ref.album(
                uri=uricompose('beetslocal',
                               None,
                               'track',
                               dict(album=album.id)),
                name=album.album)

    def _browse_artist(self, query=None):
        logger.debug('browse artist query: %s', str(query))
        # import pdb; pdb.set_trace()
        statement = ('select Distinct albums.albumartist, albums.mb_albumartistid from items'
                     ' join albums on items.album_id = albums.id'
                     ' where 1=1 ')
        for key in query:
            statement += self._build_statement(query, key)
        #statement += ' order by albums.albumartist'
        logger.debug('browse_artist: %s' % statement)
        old_url_query = {}
        for k, v in query.items():
            if k in ('mb_artistid', 'albumartist'):
                continue
            old_url_query[k] = v[0]
        for row in self._query_beets_db(statement):
            url_query = old_url_query.copy()
            if len(row[1]) > 0:
                url_query['mb_artistid'] = row[1]
            else:
                url_query['albumartist'] = row[0]
            yield  Ref.directory(
                uri=uricompose('beetslocal',
                               None,
                               'album',
                               url_query),
                name=row[0] if bool(row[0]) else u'No Artist')

    def _browse_genre(self, query=None):
        logger.debug(u'browse_genre query: %s' % query)
        statement = 'select Distinct genre from items'
        if query:
            statement += ' where 1=1 '
            statement += self._build_statement(query, 'grouping')
        old_url_query = {}
        for k, v in query.items():
            if k in ('genre', ):
                continue
            old_url_query[k] = v[0]
        for row in self._query_beets_db(statement):
            url_query = old_url_query.copy()
            url_query['genre'] = row[0]
            yield Ref.directory(
                uri=uricompose('beetslocal',
                               None,
                               'artist',
                               url_query),
                name=row[0] if bool(row[0]) else u'No Genre')

    def _browse_grouping(self):
        for row in self._query_beets_db('select distinct grouping '
                                        'from items'):
            yield Ref.directory(
                uri=uricompose('beetslocal',
                               None,
                               'genre',
                               dict(grouping=row[0])),
                name=row[0] if bool(row[0]) else u'No Grouping')

    def _browse_compilations(self):
        for album in self.lib.albums(['comp:1']):
            yield Ref.album(
                uri=uricompose('beetslocal',
                               None,
                               'track',
                               dict(album=album.id)),
                name=album.album)

    def _browse_mood(self):
        for row in self._query_beets_db('select distinct value from item_attributes'
                                    ' where key = "mood";'):
            yield Ref.directory(
                uri=uricompose('beetslocal',
                               None,
                               'artist',
                               dict(mood=row[0])),
                name=row[0])


    def _browse_format(self):
        for row in self._query_beets_db('select distinct format from items;'):
            yield  Ref.directory(
                uri=uricompose('beetslocal',
                               None,
                               'artist',
                               dict(format=row[0])),
                name=row[0])

    def _browse_samplerate(self):
        for row in self._query_beets_db('select distinct samplerate from items;'):
            yield  Ref.directory(
                uri=uricompose('beetslocal',
                               None,
                               'artist',
                               dict(samplerate=row[0])),
                name=str(row[0]))

    def _browse_year(self):
        for row in self._query_beets_db('select distinct original_year from albums;'):
            yield  Ref.directory(
                uri=uricompose('beetslocal',
                               None,
                               'artist',
                               dict(year=row[0])),
                name=str(row[0]))


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
        original_years = []
        for (key, values) in query.iteritems():
            if not values:
                del query[key]
            if type(values) is not list:
                query[key] = [values]
                # import pdb; pdb.set_trace()
            if not values:
                continue
            if key == 'date':
                for index, value in enumerate(values):
                    year = self._sanitize_year(str(value))
                    if year:
                        original_years.append(year)
                    # we possibly could introduce query['year'],
                    # query['month'] etc.
                    # Maybe later
        if 'date' in query:
            query['original_year'] = original_years
            del query['date']
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

    def _build_statement(self, query, query_key, table='items'):
        """
        A proper mopidy query has a Array of values
        Queries from mpd and browse requests have strings
        """
        statement = ""
        if query_key in query:
            for query_string in query[query_key]:
                if '"' in query_string:
                    statement += " and %s.%s = \'%s\' " % (table,
                                                           query_key,
                                                           query_string)
                else:
                    statement += ' and %s.%s = \"%s\" ' % (table,
                                                           query_key,
                                                           query_string)
        return statement

    def _find_tracks(self, query):
        statement = ('select id, title, original_day, original_month, original_year, artist, album, '
                     'composer, track, disc, length,  bitrate, comments, '
                     'mb_trackid, mtime, genre, tracktotal, disctotal, '
                     'mb_albumid, mb_albumartistid, albumartist, mb_artistid '
                     'from items where 1=1 ')

        for key in query:
            if key == 'track_name':
                query['title'] = query.pop('track_name')
            statement += self._build_statement(query, key)
        tracks = []
        result = self._query_beets_db(statement)
        for row in result:
            artist = Artist(name=row[5],
                            musicbrainz_id=row[21],
                            uri="beetslocal:artist:%s:" % row[21])
            albumartist = Artist(name=row[20],
                                 musicbrainz_id=row[19],
                                 uri="beetslocal:artist:%s:" % row[19])
            composer = Artist(name=row[7],
                              musicbrainz_id='',
                              uri="beetslocal:composer:%s:" % row[7])
            album = Album(name=row[6],
                          date=self._build_date_string(row[4],row[3],row[2]),
                          artists=[albumartist],
                          num_tracks=row[16],
                          num_discs=row[17],
                          musicbrainz_id=row[18],
                          uri="beetslocal:mb_album:%s:" % row[18])
            tracks.append(Track(name=row[1],
                                artists=[artist],
                                album=album,
                                composers=[composer],
                                track_no=row[8],
                                disc_no=row[9],
                                date=self._build_date_string(row[4],row[3],row[2]),
                                length=int(row[10] * 1000),
                                bitrate=row[11],
                                comment=row[12],
                                musicbrainz_id=row[13],
                                last_modified=int(row[14]),
                                genre=row[15],
                                uri="beetslocal:track:%s:" % row[0]))
        return tracks

    def _find_albums(self, query):
        statement = ('select id, album, original_day, original_month, original_year, '
                     'albumartist, disctotal, '
                     'mb_albumid, artpath, mb_albumartistid '
                     'from albums where 1=1 ')
        for key in query:
            if key == 'artist':
                key = 'albumartist'
                query[key] = query.pop('artist')
            statement += self._build_statement(query, key, 'albums')
        result = self._query_beets_db(statement)
        albums = []
        for row in result:
            artist = Artist(name=row[5],
                            musicbrainz_id=row[9],
                            uri="beetslocal:artist:%s:" % row[9])
            albums.append(Album(name=row[1],
                                date=self._build_date_string(row[4],row[3],row[2]),
                                artists=[artist],
                                num_discs=row[6],
                                musicbrainz_id=row[7],
                                # Expected images to be a collection of basestring, not [None]
                                # images=[row[8]],
                                uri="beetslocal:album:%s:" % row[0]))
        return albums

    def _find_artists(self, query):
        statement = ('select Distinct albumartist, mb_albumartistid'
                     ' from albums where 1=1 ')
        for key in query:
            statement += self._build_statement(query, key, 'albums')
        artists = []
        result = self._query_beets_db(statement)
        for row in result:
            artists.append(Artist(name=row[0],
                                  musicbrainz_id=row[1],
                                  uri="beetslocal:artist:%s:" % row[1]))
        return artists

    def _build_date_string(self,year=0,month=0,day=0):
        date = ""
        if not year == 0:
            date = str(year)
            if not month == 0:
                date += "-%s" % month
                if not day == 0:
                    date += "-%s" % day
        return date

    def _build_beets_track_query(self, query):
        """
        Transforms a mopidy query into beets
        query syntax
        """
        beets_query = []
        for key in query.keys():
            if key != 'any':
                if key == 'track_name':
                    beets_key = 'title'
                else:
                    beets_key = key
            # beets_query += "::(" + "|".join(query[key]) + ") "
            beets_query.append('%s:%s' % (beets_key, (' '.join(query[key])).strip()))
            logger.info(beets_query)
        # return json.dumps(self._decode_path(beets_query).strip())
        return beets_query

    def _build_beets_album_query(self, query):
        """
        Transforms a mopidy query into beets
        query syntax
        """
        beets_query = []
        for key in query.keys():
            if key != 'any':
                if key == 'artist':
                    beets_key = 'albumartist'
                else:
                    beets_key = key
                beets_query.append('%s:%s' % (beets_key, (' '.join(query[key])).strip()))
            logger.info(beets_query)
        return beets_query

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
            track_kwargs['last_modified'] = int(item['mtime'])

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
