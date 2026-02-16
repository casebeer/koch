
import logging
logger = logging.getLogger(__name__)

import audiogen
import audiogen.util

import itertools
import contextlib

from functools import reduce

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

    # see ARRL doc: Bloom. "A Standard for Morse Timing Using the Farnsworth Technique."
    dit = 1.2 / cwpm
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

@audiogen.sampler.cache_finite_samples
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

'''
Implement str.join() for generators and lists

Interleave output of `joiner_func()` between items of `joined`, without appending a joiner after the
final item of `joined`.  Equivalent to `joiner.join(joined)`

`joiner_func` must be a function which emits joiner.
'''
def gen_join(joiner_func, joined):
    items = iter(joined)

    # pull off the first item, if any
    try:
        previous_item = next(items)
    except StopIteration:
        return

    # iterate across remaining items, emmiting only the previous item
    # along with its subsequent space
    for item in items:
        yield previous_item
        yield joiner_func()
        previous_item = item

    # this is now the final item in the list, so emit it without a trailing space
    yield previous_item

'''
Produce printable visualization of sample data, with | for any sound and _ for silence
Decimate by 1:512 to shorten samples to reasonable lengths for printing in console.
n.b. We should do a moving average of all samples rather than decimating, but decimating is faster.
     There may be glitches in the output as a result (e.g. showing silence due to a near-zero-
     corssing in the middle of non-silence).
'''
def visualize_samples(samples):
    return "".join(['_' if -.01 < sample < .001 else '|' for index, sample in enumerate(samples) if index % 512 == 0])


'''Return iterable of sample generator functions for the Morse for `letter`.'''
def letter_gens(letter):
    # TODO: decide on behavior when letter not in LETTERS
    tones = LETTERS[letter]

    # interleave inter-symbol space silences between tones
    for symbol in gen_join(lambda: inter_symbol, tones):
        yield symbol

'''
Yield a sequence of sample generator functions which represents the provided text iterable.

Set suffix_space = True to append an inter-symbol space at the end of the text to allow for
effective bandpass filtering of terminal clicks.
'''
def text_gens(text, suffix_space=False):
    chars = iter(text)
    try:
        previous_char = next(chars)
    except StopIteration:
        return

    for char in chars:
        if previous_char == " ":
            # special case for inter-word space; don't suffix it with an inter-letter space
            for gen in letter_gens(previous_char):
                yield gen
        else:
            for gen in letter_gens(previous_char):
                yield gen
            # don't prefix an upcoming space with an inter-letter space
            if char != " ":
                yield inter_letter
        previous_char = char

    # never suffix the final char with an inter-letter space
    for gen in letter_gens(previous_char):
        yield gen
    if suffix_space:
        yield inter_symbol

'''
Return a generator for audio samples of the Morse for `text`.

n.b. this output is bandwidth limited to remove clicks, but the provided text must end with silence
     or the filter will not be able to remove the terminal click.
'''
def code(text, use_bpf=True):
    # todo: parse prosigns out of text to be encoded
    # todo: string or list of strings passed?

    # get an interable of generator functions, one per symbol/space
    gen_funcs = text_gens(text, suffix_space=use_bpf)

    # warning consumes generator
    #logger.debug(list(gen_funcs))

    logger.debug(f"Timings: DIT:{DIT} DAH:{DAH} INTER_SYMBOL:{INTER_SYMBOL} INTER_LETTER:{INTER_LETTER} INTER_WORD:{INTER_WORD}")
    logger.debug(f"HERTZ: {HERTZ}, BANDWIDTH:{BANDWIDTH}")

    # define bandpass filter to limit morse tone bandwidth
    bpf = audiogen.filters.band_pass(HERTZ, min(BANDWIDTH, HERTZ))

    # call each sample generator function; each will produce its own generator
    # chain together all the samples within each of these generators
    letter_samples = itertools.chain.from_iterable(gen_func() for gen_func in gen_funcs)

    # Warning: Generating this debug output puts all samples in memory at once
    #letter_samples = list(letter_samples)
    #logger.debug(f"{len(letter_samples)} samples:")
    #logger.debug(visualize_samples(letter_samples))

    # chain the band pass filter three times to increase stopband attenuation
    if use_bpf:
        samples = bpf(bpf(bpf(letter_samples)))
    else:
        samples = letter_samples
    return samples

if __name__ == "__main__":
    import sys
    #message = (sys.argv[1] if len(sys.argv) > 1 else "AC2SY").upper()
    import cProfile
    cProfile.run('audiogen.sampler.discard(code("Now is the time for all good men to come to the aid of their country ".upper() * 1, use_bpf=True))')
    pass
