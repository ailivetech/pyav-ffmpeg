pyav-ffmpeg -- Raven's LGPL fork
================================

This is `AI Live Technologies`_' fork of `pyav-ffmpeg`_ for `Raven`_, taken at the
upstream tag ``7.1-4`` -- the recipe that built the PyPI ``av==14.2.0`` wheel Raven
shipped with -- and given one new mode, ``scripts/build-ffmpeg.py --lgpl``:

- the upstream ``--community`` package set and configure line, minus ``x264`` and
  ``x265`` (GPL), minus ``gmp`` and ``opencore-amr`` (the only consumers of
  ``--enable-version3`` in this recipe), and with ``--enable-version3`` dropped, so
  ``avcodec_license()`` reads ``LGPL version 2.1 or later``;
- ``libsrt`` (MPL-2.0), MediaFoundation (Windows), VideoToolbox (macOS) and the
  NVENC/NVDEC wrappers (``--enable-cuda``) stay exactly as the community build has them;
- neither ``openh264`` nor ``fdk_aac`` (the commercial variant's codecs) is built.

The workflow builds only Raven's two platforms (macOS arm64, Windows x86_64) and, on a
``7.1-<n>-raven-lgpl-<m>`` tag, attaches the tarballs to a GitHub Release. Raven's
``ffmpeg_lgpl/fetch_drop.py`` downloads them from there; Raven's private PyAV wheel is
built against them (see Raven's ``docs/ffmpeg-gpl-lgpl-split-plan.md``).

The fork's second product is ``scripts/build-ffmpeg.py --gpl-child``: Raven's **GPL encoder
helper** -- an unmodified, static ``ffmpeg`` executable built with ``--enable-gpl
--enable-libx264 --enable-libx265`` and nothing else enabled (the NUT demuxer/muxer, the
rawvideo decoder, the pipe protocol), which Raven runs as a separate process fed over pipes so
that libx264/libx265 never enter Raven's own process. A ``7.1-<n>-raven-gpl-child-<m>`` tag
builds it on both platforms and attaches ``ffmpeg-gpl-child-<platform>.tar.gz`` (``bin/ffmpeg``,
``src/`` = the corresponding source of everything linked in, ``CONFIGURE.txt``) to a Release;
Raven's ``gpl_encoder_helper/fetch_helper.py`` downloads it. Everything below this section is
upstream's README, unchanged.

.. _AI Live Technologies: https://raven.video/
.. _pyav-ffmpeg: https://github.com/PyAV-Org/pyav-ffmpeg
.. _Raven: https://raven.video/

pyav-ffmpeg
===========

This project provides binary builds of FFmpeg and its dependencies for `PyAV`_.
These builds are used in order to provide binary wheels of PyAV, allowing
users to easily install PyAV without perform error-prone compilations.

The builds are provided for several platforms:

- Linux (x86_64, i686, aarch64)
- macOS (x86_64, arm64)
- Windows (AMD64)

Features
--------

Currently FFmpeg 7.1 is built with the following packages enabled for all platforms:

- gmp 6.3.0
- xml2 2.9.13
- xz 5.6.3
- aom 3.11.0
- dav1d 1.4.1
- lame 3.100
- ogg 1.3.5
- opencore-amr 0.1.5
- opus 1.5.2
- speex 1.2.1
- svt-av1 2.2.1
- srt 1.5.4 (encryption disabled on macOS)
- twolame 0.4.0
- vorbis 1.3.7
- vpx 1.14.0
- png 1.6.45
- webp 1.5.0
- x264 master
- x265 3.5

The following additional packages are also enabled on Linux:

- gnutls 3.8.1
- nettle 3.9.1
- unistring 1.2

.. _PyAV: https://github.com/PyAV-Org/PyAV
