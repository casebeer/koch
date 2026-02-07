
# coding=utf8

import logging
logger = logging.getLogger(__name__)

import audiogen
import koch.morse as morse

import itertools
import random

import sys

# http://www.qsl.net/n1irz/finley.morse.html
# http://www.codepractice.com/learning.html
# K  M  R  S  U  A  P   T  L  O  W  I  .  N  J  E  F  0   Y  ,  V  G  5  /
# Q  9  Z  H  3  8  B   ?  4  2  7  C  1  D  6  X  <BT>   <SK>  <AR>

DEFAULT_LENGTH = 10
# i.e. start with only the letter 'K'
DEFAULT_TRAINING_CHARACTERS = 1
DEFAULT_HERTZ = 770
DEFAULT_BANDWIDTH = 200
DEFAULT_WPM = 20
# Farnsworth timings below 20 WPM  (n.b. ARRL cutoff is 18 WPM)
DEFAULT_FARNSWORTH_CUTOFF = 20

def koch_alphabet(characters=2):
	# todo: parse alphabet from string, handling prosigns properly
	# todo: accept and parse custom alphabet string
	alphabet = [char for char in "KMRSUAPTLOWI.NJEF0Y,VG5/Q9ZH38B?427C1D6X"] +\
		["BT", "SK", "AR"]
	return alphabet[:characters]

def koch(length=20, alphabet=koch_alphabet(2)):
	def insert_spaces(letters):
		# first char can't be a space
		# todo: better word length distribution
		yield next(letters)
		for letter in letters:
			if random.random() < 1. / 4:
				yield u" "
			yield letter

	letters = (random.choice(alphabet) for i in range(length))
	return u"".join(insert_spaces(letters))

def main():
	import argparse

	parser = argparse.ArgumentParser(
		formatter_class=argparse.ArgumentDefaultsHelpFormatter
	)
	parser.add_argument("-l", "--length",
		type=int,
		default=DEFAULT_LENGTH,
		help="Length of practise message in characters."
	)
	parser.add_argument("-c", "--characters",
		type=int,
		default=DEFAULT_TRAINING_CHARACTERS,
		help="Number of distinct characters to practise."
	)
	parser.add_argument("-i", "--intro",
		action="store_true",
		default=False,
		help="Play just the Nth Koch character to introduce it. Set `N` with the -c flag."
	)
	parser.add_argument("-a", "--custom-alphabet",
		type=str,
		default=None,
		help="Custom alphabet to use in place of default Koch ordering."
	)
	# todo: make saving in lieu of playing?
	parser.add_argument("-f", "--file",
		type=str,
		default=None,
		help="Save audio to a WAV file."
	)
	parser.add_argument("-H", "--hertz",
		type=float,
		default=DEFAULT_HERTZ,
		help="Frequency in Hertz to use for practise tones."
	)
	parser.add_argument("-B", "--bandwidth",
		type=float,
		default=DEFAULT_BANDWIDTH,
		help="Audio bandwidth in Hertz, centered on the tone frequency."
	)
	parser.add_argument("-w", "--wpm",
		type=float,
		default=DEFAULT_WPM,
		help="Morse words per minute."
	)
	parser.add_argument("--cwpm",
		type=float,
		default=None,
		help=f"""Morse *character* words per minute.
		If unset, defaults to max({DEFAULT_FARNSWORTH_CUTOFF}, WPM).
		"""
	)
	parser.add_argument("--forever",
		action="store_true",
		default=False,
		help="""Loop the message forever (cannot be combined with --file)."""
	)
	parser.add_argument("-d", "--debug",
		action="store_true",
		default=False
	)
	parser.add_argument("message", nargs="*", default=None)
	args = parser.parse_args()

	if args.debug:
		logging.basicConfig(level=logging.DEBUG)
	else:
		logging.basicConfig(level=logging.WARN)

	if args.forever and args.file:
		print("Cannot write an infinitely looping audio stream to a file.")
		sys.exit(1)

	if args.custom_alphabet:
		# todo: parse with koch_alphabet function (TBD)
		alphabet = args.custom_alphabet[:args.characters]
	else:
		alphabet = koch_alphabet(args.characters)

	if args.message:
		# play manually specified message
		message = u" ".join(args.message).upper()
	elif args.intro:
		# play the Nth char length times to teach the char
		message = alphabet[-1] * args.length
	else:
		# play random message of chosen chars and length
		message = koch(args.length, alphabet)

	if args.cwpm:
		cwpm = args.cwpm
	else:
		# Farnsworth timings below 20 WPM  (n.b. ARRL cutoff is 18 WPM)
		cwpm = max(DEFAULT_FARNSWORTH_CUTOFF, args.wpm)

	if args.intro or args.message:
		print(message)
	else:
		if int(args.wpm) == cwpm:
			wpm_message = f"({int(args.wpm)} WPM)"
		else:
			wpm_message = f"({int(args.wpm)} WPM/{cwpm} CWPM)"
		print(f"Testing characters {wpm_message}:\n{u'·'.join(alphabet)}")


	if args.forever:
		print("Hit ctrl-c to exit")

	with audiogen.sampler.frame_rate(48000):
		with morse.timings(morse.farnsworth(args.wpm, cwpm)):
			with morse.tone(args.hertz):
				with morse.bandwidth(args.bandwidth):
					# todo: determine nesting behavior of context managers

					if args.debug:
						# generate audio samples just for visualization, since visualizing consumes
						# them and they will not be available for audio output
						logger.debug(morse.visualize_samples(morse.code(message)))

					audio = morse.code(message)
					if args.file:
						with open(args.file, "wb") as f:
							audiogen.write_wav(f, audio)
					else:
						try:
							if args.forever:
								audio = itertools.cycle(itertools.chain(audio, morse.code(" ")))
							stream = audiogen.sampler.play(
								itertools.chain(audio, morse.code(" "), audiogen.beep()),
								blocking=True
							)
						except KeyboardInterrupt:
							# So further messages don't start with "^C"
							print(u"")

	if not args.intro and not args.message and not args.file:
		input(u"\nHit <enter> to see correct transcription...")
		print(u"\n{}".format(message.lower()))

	return 0

if __name__ == "__main__":
	sys.exit(main())
