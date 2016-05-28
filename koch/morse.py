
import audiogen
import audiogen.util

import itertools
import contextlib

HERTZ = 770
BANDWIDTH = 200
DEFAULT_WPM = 20

#
# todo: support parsing of prosigns
#

# ARRL Morse Transmission Timing Standard
# http://www.arrl.org/files/file/Technology/x9004008.pdf

# WPM determined by P-A-R-I-S, or 50 dit lengths (with spaces)
# ms/DIT = (60 / 50) / WPM
# WPM = (60 / 50) / (ms/DIT)
# or 
# s/DIT = 1.2 / WPM

def wpm(wpm=20, farnsworth_limit=18):
	'''
	Generate Morse timings for specified WPM

	For WPM values below farnsworth_limit, Farnsworth timing 
	will be used per the ARRL standard. The default farnsworth_limit
	is 18 WPM. To disable Farnsworth timing entirely, set
	farnsworth_limit=None.
	'''
	return farnsworth(
		wpm, 
		max(farnsworth_limit, wpm) if farnsworth_limit else wpm
	)

def farnsworth(wpm=20, cwpm=None):
	'''
	Generate Morse timings based on ARRL Farnsworth timing

	This permits optionally specifying a different overall words
	per minute. The character WPM determines the timings of the 
	dits, dahs, and intra-letter spaces; the overall WPM determines
	the timings of the inter-letter and inter-word spaces.
	'''
	if not cwpm:
		cwpm = wpm

	# ensure cwpm is never slower than wpm!
	cwpm = max(cwpm, wpm)

	dit = 1.2 / cwpm
	# see ARRL doc
	t_a = (60 * cwpm - 37.2 * wpm) / (cwpm * wpm)
	
	return {
		"dit": dit,
		"dah": dit * 3,
		"inter_symbol": dit,

		"inter_letter": (t_a * 3) / 19.,
		"inter_word": (t_a * 7) / 19.
	}

def set_times(timings):
	global DIT, DAH, INTER_SYMBOL, INTER_LETTER, INTER_WORD
	DIT = timings["dit"]
	DAH = timings["dah"]
	INTER_SYMBOL = timings["inter_symbol"]
	INTER_LETTER = timings["inter_letter"]
	INTER_WORD = timings["inter_word"]

def get_times():
	return {
		"dit": DIT,
		"dah": DAH,
		"inter_symbol": INTER_SYMBOL,
		"inter_letter": INTER_LETTER,
		"inter_word": INTER_WORD
	}

# set default timings
set_times(wpm(DEFAULT_WPM))

class timings(object):
	'''
	Context manager to set Morse symbol timings.
	'''
	def __init__(self, timings):
		self._new_timings = timings
	def __enter__(self, ):
		self._saved_timings = get_times()
		set_times(self._new_timings)
	def __exit__(self, *args, **kwargs):
		set_times(self._saved_timings)

class tone(object):
	'''
	Context manager to set frequency for Morse tones.
	'''
	def __init__(self, frequency):
		self._new_frequency = frequency
	def __enter__(self, ):
		global HERTZ
		self._saved_frequency = HERTZ
		HERTZ = self._new_frequency
	def __exit__(self, *args, **kwargs):
		global HERTZ
		HERTZ = self._saved_frequency

@contextlib.contextmanager
def bandwidth(bandwidth):
	global BANDWIDTH
	old = BANDWIDTH
	BANDWIDTH = bandwidth
	yield
	BANDWIDTH = old

def tone_for(seconds):
	tone = audiogen.crop(audiogen.util.volume(audiogen.tone(HERTZ), -3), seconds)
	return tone

def dit():
	for sample in tone_for(DIT):
		yield sample

def dah():
	for sample in tone_for(DAH):
		yield sample

def space():
	for sample in audiogen.silence(INTER_WORD):
		yield sample

def inter_symbol():
	for sample in audiogen.silence(INTER_SYMBOL):
		yield sample

def inter_letter():
	for sample in audiogen.silence(INTER_LETTER):
		yield sample
	
LETTERS = {
	"A": (dit, dah),
	"B": (dah, dit, dit, dit),
	"C": (dah, dit, dah, dit),
	"D": (dah, dit, dit),
	"E": (dit,),
	"F": (dit, dit, dah, dit),
	"G": (dah, dah, dit),
	"H": (dit, dit, dit, dit),
	"I": (dit, dit),
	"J": (dit, dah, dah, dah),
	"K": (dah, dit, dah),
	"L": (dit, dah, dit, dit),
	"M": (dah, dah),
	"N": (dah, dit),
	"O": (dah, dah, dah),
	"P": (dit, dah, dah, dit),
	"Q": (dah, dah, dit, dah),
	"R": (dit, dah, dit),
	"S": (dit, dit, dit),
	"T": (dah,),
	"U": (dit, dit, dah),
	"V": (dit, dit, dit, dah),
	"W": (dit, dah, dah),
	"X": (dah, dit, dit, dah),
	"Y": (dah, dit, dah, dah),
	"Z": (dah, dah, dit, dit),
	"1": (dit, dah, dah, dah, dah),
	"2": (dit, dit, dah, dah, dah),
	"3": (dit, dit, dit, dah, dah),
	"4": (dit, dit, dit, dit, dah),
	"5": (dit, dit, dit, dit, dit),
	"6": (dah, dit, dit, dit, dit),
	"7": (dah, dah, dit, dit, dit),
	"8": (dah, dah, dah, dit, dit),
	"9": (dah, dah, dah, dah, dit),
	"0": (dah, dah, dah, dah, dah),
	".": (dit, dah, dit, dah, dit, dah),
	",": (dah, dah, dit, dit, dah, dah),
	"?": (dit, dit, dah, dah, dit, dit),
	" ": (space,),
}

### Add prosigns to LETTERS dict
# todo: do we need to do this, or can the parser generate custom prosigns on the fly?
PROSIGNS = [ "BT", "SK", "AR", "BK", "KN", "CL" ]
for prosign in PROSIGNS:
	LETTERS[prosign] = reduce(lambda a, b: a + b, [LETTERS[char] for char in prosign])

@audiogen.sampler.cache_finite_samples
def letter(letter):
	'''Return a generator for the audio samples of the Morse for `letter`.'''
	# todo: decide on behavior when letter not in LETTERS
	tones = [gen() for gen in LETTERS[letter]]
	spaces = [gen() for gen in [inter_symbol] * (len(tones) - 1) + [inter_letter]]
	# todo: compensate for added space following an inter-word space char
	gens = [symbol for pair in zip(tones, spaces) for symbol in pair]

	# define bandpass filter to limit morse tone bandwidth
	bpf = audiogen.filters.band_pass(HERTZ, BANDWIDTH)

	# chain the band pass filter three times to narrow bandwidth
	return bpf(bpf(bpf(
		itertools.chain(*gens)
		)))

def code(text):
	'''Return a generator for audio samples of the Morse for `text`.'''
	# todo: parse prosigns out of text to be encoded
	# todo: string or list of strings passed?
	gens = [letter(l) for l in text]
	return itertools.chain(*gens)

if __name__ == "__main__":
	import sys
	#message = (sys.argv[1] if len(sys.argv) > 1 else "KD2CNQ").upper()
	pass
