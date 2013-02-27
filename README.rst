deflacue
========
http://github.com/idlesign/deflacue


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

1. SoX command line utility - http://sox.sourceforge.net.

   Ubuntu users may install the following SoX packages: `sox`, `libsox-fmt-all`.

2. Python 3.2+


Usage
-----

1. `import deflacue` - if you want to use it as module. *Deflacue* and *CueParser* classes are at your service.
2. `./deflacue.py -h` in command line - to get help on utility usage.

In the following example we create audio collection in /home/idle/audio_collection/ from audio CD images
stored under /home/idle/audio_raw/ processing Cue Sheet files created using windows-1251 encoding::

    ./deflacue.py -e windows-1251 /home/idle/audio_raw/ -d /home/idle/audio_collection/


Please keep in mind that `./deflacue.py` syntax used above supposes that Python 3.2+ is set as system default
Python interpreter. Otherwise you might want to run deflacue with `python3 deflacue.py`.
