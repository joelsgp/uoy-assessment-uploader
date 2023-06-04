"""Helper functions for parsing command line arguments."""

from argparse import ArgumentParser
from pathlib import Path
from typing import Optional, Sequence

DEFAULT_ARG_FILE = "exam.zip"
DEFAULT_ARG_COOKIE_FILE = "cookies.txt"


# todo subclass ArgumentParser instead of using helper functions?


class Args:
    """Type-hinted namespace to use with :meth:`ArgumentParser.parse_args`."""

    username: Optional[str]
    password: Optional[str]
    exam_number: Optional[str]
    submit_url: str
    file: Path
    dry_run: bool
    use_keyring: bool
    delete_from_keyring: bool
    cookie_file: Path
    save_cookies: bool
    delete_cookies: bool


def parse_args(argv: Sequence[str] = None) -> Args:
    """Construct an argument parser return a type-hinted namespace.

    Wrapper to return a type-hinted :class:`Args` namespace,
    rather than the default untyped :class:`argparse.Namespace`.

    :param argv: list of command line arguments to parser, or None to use :var:`sys.argv` by default.
    :return: namespace with attributes parsed by :meth:`ArgumentParser.parse_args` from the argument sequence
    """
    parser = get_parser()
    args = Args()
    parser.parse_args(argv, namespace=args)
    return args


def get_parser() -> ArgumentParser:
    """Construct argument parser, add arguments for this script, and return it.

    Constants:
        :var:`__doc__` the module docstring is used for the parser's description.
        :const:`DEFAULT_ARG_FILE` Path object to use by default for :option:`--file`.
        :const:`DEFAULT_ARG_COOKIE_FILE` Path object to use by default for :option:`--cookie-file`.

    :return: the instance of :class:`ArgumentParser`
    """
    parser = ArgumentParser(description=__doc__)

    # core functionality arguments
    parser.add_argument(
        "-n",
        "--submit-url",
        required=True,
        help="The specific exam to upload to, e.g. /2021-2/submit/COM00012C/901/A",
    )
    parser.add_argument(
        "-u", "--username", help="Username for login, not email address, e.g. ab1234"
    )
    parser.add_argument(
        "--password",
        help="Not recommended to pass this as an argument, for security reasons."
        " Leave it out and you will be securely prompted to enter it if needed.",
    )
    parser.add_argument("-e", "--exam-number", help="e.g. Y1234567")
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        default=DEFAULT_ARG_FILE,
        help="default: '%(default)s'",
    )

    # options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log in but don't actually upload the file.",
    )

    # keyring store
    parser.add_argument(
        "--no-use-keyring",
        action="store_false",
        dest="use_keyring",
        help="DON'T use the keyring service for storing and retrieving the password and exam number.",
    )
    parser.add_argument(
        "--delete-from-keyring",
        action="store_true",
        help="Delete saved password and exam number from the keyring, then exit.",
    )

    # requests cookie jar file
    parser.add_argument(
        "--cookie-file",
        type=Path,
        default=DEFAULT_ARG_COOKIE_FILE,
        help="default: '%(default)s'",
    )
    parser.add_argument(
        "--no-save-cookies",
        dest="save_cookies",
        action="store_false",
        help="Do not save or load session cookies.",
    )
    parser.add_argument(
        "--delete-cookies",
        action="store_true",
        help="Delete cookie file, then exit.",
    )

    return parser
