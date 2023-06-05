"""Helper functions for parsing command line arguments."""

import argparse
from pathlib import Path
from typing import Optional, Sequence

DEFAULT_ARG_FILE = "exam.zip"
DEFAULT_ARG_COOKIE_FILE = "cookies.txt"


class Namespace(argparse.Namespace):
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


class ArgumentParser(argparse.ArgumentParser):
    """Argument parser subclass that returns a type-hinted namespace from :meth:`parse_args`."""

    def parse_args(
        self, args: Optional[Sequence[str]] = None, namespace=None
    ) -> Namespace:
        if namespace is None:
            namespace = Namespace()
        return super().parse_args(args, namespace)


def get_parser() -> ArgumentParser:
    """Construct argument parser, add arguments for this script, and return it.

    Constants:
        :data:`__doc__` the module docstring is used for the parser's description.
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
        help=(
            "DON'T use the keyring service"
            "for storing and retrieving the password and exam number."
        ),
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
