import argparse
import itertools
import logging
import random
import sys
from collections.abc import Iterable, Iterator

import audiogen

from koch import morse

logger = logging.getLogger(__name__)


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

KOCH_ALPHABET = [*list("KMRSUAPTLOWI.NJEF0Y,VG5/Q9ZH38B?427C1D6X"), *["BT", "SK", "AR"]]


def koch(length: int = 20, alphabet: list[str] = KOCH_ALPHABET[:2]) -> str:
    def insert_spaces(letters: Iterator[str]) -> Iterator[str]:
        # first char can't be a space
        # TODO: better word length distribution
        yield next(letters)
        for letter in letters:
            if random.random() < 1.0 / 4:
                yield " "
            yield letter

    letters = (random.choice(alphabet) for i in range(length))
    return "".join(insert_spaces(letters))


def read_stdin() -> Iterator[str]:
    for line in sys.stdin:
        for char in line.strip("\n"):
            yield char.upper()


def main() -> int:

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-l",
        "--length",
        type=int,
        default=DEFAULT_LENGTH,
        help="Length of practise message in characters.",
    )
    parser.add_argument(
        "-c",
        "--characters",
        type=int,
        default=DEFAULT_TRAINING_CHARACTERS,
        help="Number of distinct characters to practise.",
    )
    parser.add_argument(
        "-i",
        "--intro",
        action="store_true",
        default=False,
        help="Play just the Nth Koch character to introduce it. "
        "Set `N` with the -c flag.",
    )
    parser.add_argument(
        "-a",
        "--custom-alphabet",
        type=str,
        default=None,
        help="Custom alphabet to use in place of default Koch ordering.",
    )
    # TODO: make saving in lieu of playing?
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        default=None,
        help="Save audio to a WAV file.",
    )
    parser.add_argument(
        "-H",
        "--hertz",
        type=float,
        default=DEFAULT_HERTZ,
        help="Frequency in Hertz to use for practise tones.",
    )
    parser.add_argument(
        "-B",
        "--bandwidth",
        type=float,
        default=DEFAULT_BANDWIDTH,
        help="Audio bandwidth in Hertz, centered on the tone frequency.",
    )
    parser.add_argument(
        "-w",
        "--wpm",
        type=float,
        default=DEFAULT_WPM,
        help="Morse words per minute.",
    )
    parser.add_argument(
        "--cwpm",
        type=float,
        default=None,
        help=f"""Morse *character* words per minute.
        If unset, defaults to max({DEFAULT_FARNSWORTH_CUTOFF}, WPM).
        """,
    )
    parser.add_argument(
        "--forever",
        action="store_true",
        default=False,
        help="""Loop the message forever (cannot be combined with --file).""",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-s",
        "--stdin",
        action="store_true",
        default=False,
        help="""Read message from stdin.""",
    )
    parser.add_argument("message", nargs="*", default=None)
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    if args.forever and args.file:
        print("Cannot write an infinitely looping audio stream to a file.")
        sys.exit(1)

    if args.custom_alphabet:
        alphabet = args.custom_alphabet[: args.characters]
    else:
        alphabet = KOCH_ALPHABET[: args.characters]

    if args.message:
        # play manually specified message
        message: Iterable[str] = " ".join(args.message).upper()
    elif args.stdin:
        # read message from stdin
        message = read_stdin()
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
    elif args.stdin:
        print("Reading from stdin...")
    else:
        if int(args.wpm) == cwpm:
            wpm_message = f"({int(args.wpm)} WPM)"
        else:
            wpm_message = f"({int(args.wpm)} WPM/{cwpm} CWPM)"
        print(f"Testing characters {wpm_message}:\n{'·'.join(alphabet)}")

    if args.forever:
        print("Hit ctrl-c to exit")

    with audiogen.sampler.frame_rate(48000), morse.timings(
        morse.farnsworth(args.wpm, cwpm)
    ), morse.tone(args.hertz), morse.bandwidth(args.bandwidth):

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
                audiogen.sampler.play(
                    itertools.chain(audio, morse.code(" "), audiogen.beep()),
                    blocking=True,
                )
            except KeyboardInterrupt:
                # So further messages don't start with "^C"
                print()

    if not args.intro and not args.message and not args.file and not args.stdin:
        input("\nHit <enter> to see correct transcription...")
        print(f"\n{str.lower(str(message))}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
