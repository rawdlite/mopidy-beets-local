****************************
Mopidy-BeetsLocal
****************************

.. image:: https://img.shields.io/pypi/v/Mopidy-BeetsLocal.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-BeetsLocal/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/dm/Mopidy-BeetsLocal.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-BeetsLocal/
    :alt: Number of PyPI downloads

.. image:: https://img.shields.io/travis/rawdlite/mopidy-beets-local/master.png?style=flat
    :target: https://travis-ci.org/rawdlite/mopidy-beets-local
    :alt: Travis CI build status

.. image:: https://img.shields.io/coveralls/rawdlite/mopidy-beets-local/master.svg?style=flat
   :target: https://coveralls.io/r/rawdlite/mopidy-beets-local?branch=master
   :alt: Test coverage

Access local beets library via beets native api.
No running beets web process required.
Search by genre etc. supported.


Installation
============

Install by running::

    pip install Mopidy-BeetsLocal



Configuration
=============

Before starting Mopidy, you must add configuration for
Mopidy-BeetsLocal to your Mopidy configuration file::

    [beetslocal]
    enabled = true
    beetslibrary = /<your path>/beetslibrary.blb
    use_original_release_date = false

Project resources
=================

- `Source code <https://github.com/rawdlite/mopidy-beetslocal>`_
- `Issue tracker <https://github.com/rawdlite/mopidy-beetslocal/issues>`_
- `Development branch tarball <https://github.com/rawdlite/mopidy-beetslocal/archive/master.tar.gz#egg=Mopidy-BeetsLocal-dev>`_


Changelog
=========

v0.0.4
----------------------------------------
cleanup

v0.0.3 (UNRELEASED)
----------------------------------------
Switched to URI schema 'beetslocal'

v0.0.2 (UNRELEASED)
----------------------------------------

Introducing new optional config option 'use_original_release_date'.
Path decoding now hopefully working for different locale.
Returns release date and Disc Number.


v0.0.1 (UNRELEASED)
----------------------------------------

- Initial release.
