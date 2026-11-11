deflacue
========
http://github.com/idlesign/deflacue

|release| |lic| |ci| |coverage|

.. |release| image:: https://img.shields.io/pypi/v/deflacue.svg
    :target: https://pypi.python.org/pypi/deflacue

.. |lic| image:: https://img.shields.io/pypi/l/deflacue.svg
    :target: https://pypi.python.org/pypi/deflacue

.. |ci| image:: https://img.shields.io/travis/idlesign/deflacue/master.svg
    :target: https://travis-ci.org/idlesign/deflacue

.. |coverage| image:: https://img.shields.io/coveralls/idlesign/deflacue/master.svg
    :target: https://coveralls.io/r/idlesign/deflacue


What's that
-----------

*deflacue is a SoX based audio splitter appropriate to split audio CD images incorporated with .cue files.*

It is able to function both as a Python module and in command line mode.


Features
--------

- Large variety of supported lossless input audio formats FLAC, WAV, etc. (due to SoX).
- Batch audio files processing (including recursive path traversing).
- Automatic audio collection hierarchy building (Artist/Year-Album/Tracknum-Title).
- Automatic track metadata copying from .cue.


Requirements
------------

* Python 3.6+
* SoX command line utility - http://sox.sourceforge.net.

  Ubuntu users may install the following SoX packages: ``sox``, ``libsox-fmt-all``.


Usage
-----

From Python
~~~~~~~~~~~

``from deflacue import deflacue`` - if you want to use it as module.

Use ``Deflacue`` class for SoX interaction.

Use ``CueParser`` class for .cue parsing.

From Command Line
~~~~~~~~~~~~~~~~~

``deflacue --help`` in command line - to get help on utility usage.

In the following example we create audio collection in ``/home/idle/audio_collection/`` from audio CD images
stored under ``/home/idle/audio_raw/`` processing Cue Sheet files created using ``windows-1251`` encoding:

.. code-block::

    $ deflacue -e windows-1251 /home/idle/audio_raw/ -d /home/idle/audio_collection/

