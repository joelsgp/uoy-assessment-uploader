from argparse import ArgumentParser
from pathlib import Path
from typing import Optional, Sequence

DEFAULT_ARG_FILE = "exam.zip"
DEFAULT_ARG_COOKIE_FILE = "cookies.txt"


class Args:
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
    parser = get_parser()
    args = Args()
    parser.parse_args(argv, namespace=args)
    return args


def get_parser() -> ArgumentParser:
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
    # selenium cookies
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
