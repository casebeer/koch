Koch method Morse code trainer
==============================

Command line `Koch method <http://www.qsl.net/n1irz/finley.morse.html>`__
Morse code audio generation and training program.

Implements:

- Morse code audio playback and file generation
- with configurable `Farnsworth timing [PDF] <http://www.arrl.org/files/file/Technology/x9004008.pdf>`_
  (defaults to a minimum of 20 WPM characters at any WPM less than 20 WPM)
- and filters to limit the code's audio bandwith
- supporting a 
  `Koch method <http://web.archive.org/web/20130208133414/http://www.codepractice.com/learning.html>`__
  CLI training program

Installation
------------

::

    $ pip install koch

Requires:

- `audiogen <https://pypi.python.org/pypi/audiogen>`_ 
- `PyAudio <http://people.csail.mit.edu/hubert/pyaudio/>`_ for audio playback (as opposed to file generation) 

Tested with Python 2.7.9 on Mac OS X.

Note that to install the PyAudio dependency on Mac OS X, you'll need to first
install ``portaudio`` with Homebrew::

    $ brew install portaudio

Examples
--------

Play back strings in Morse by passing them as command line arguments::

    $ koch hello world

Save the generated code to a WAV file::

    $ koch -f hello.wav hello world

Change the code speed from the default 20 WPM to 30 WPM::

    $ koch -c 30 hello world

And the tone frequency from the default 770 Hz to 440 Hz::

    $ koch -H 440 hello world

Try a slower speed, which will default to Farnsworth timing with each character played
at 20 WPM (default) but the inter-character spacings slowed to 10 WPM::

    $ koch -w 10 hello world

Keep the inter-character speed at 10 WPM, but increase the Farnsworth character speed to 
30 WPM::

    $ koch -w 10 --cwpm 30 hello world

Start a Koch method training sequence, which begins by teaching only the letter 'K' 
(default 20 WPM, 10 characters generated per training run, random word lengths)::

    $ koch

Move up to learning the first two characters in the Koch method (i.e. 'K' and 'M')::

    $ koch -c 2

This will randomly play 10 'K' or 'M' characters in words of random lengths, then pause
and wait for the user to hit the <Enter> key before printing the actual test sequence
played. 

You can also try a custom Koch alphabet, e.g. to learn in a different character order::

    $ koch -a ABCDE -c 3


Several options together to generate a WAV file with a 30 WPM, 440 Hz Koch training session
that's 20 characters long teaching letters 'K,', 'M,' and 'R'::

    $ koch -w 30 -H 440 -c 20 -f koch.wav 

Get help with CLI options::

    $ koch -h

See also
--------

- `audiogen`_ (`Github project <https://github.com/casebeer/audiogen>`_),
  a Python generator-based audio generation and processing library

Contributing
------------

Get the source and report any bugs on Github:

    https://github.com/casebeer/koch

Version history
---------------

- 0.0.3 - Band pass filter bug fix. Add CLI option to override default 200 Hz 
  band pass filter bandwidth. 
- 0.0.2 - Limit code audio bandwidth to 200 Hz using bandpass filters. Improved 
  file output behavior for easier scripting.
