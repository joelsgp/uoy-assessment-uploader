"""Tool for automating submitting assessments to the University of York Computer Science department."""

import hashlib
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Optional

from .argparse import Namespace, get_parser
from .constants import URL_SUBMIT_BASE, URL_SUBMIT_EXAMPLE, __version__
from .credentials import delete_keyring_entries, ensure_username
from .requests import run_requests_session

REGEX_SUBMIT_URL = re.compile(
    r"((((((https?:)?//)?teaching\.cs\.york\.ac\.uk)?/)?student)?/)?"
    r"(?P<path>\d{4}-\d/submit/([A-Z\d]+/\d+))"
    r"(/A)?/?",
    re.VERBOSE,
)


def deletion_subcommands(args: Namespace) -> bool:
    """Delete cookie file and keyring entries.

    Takes effect if :option:`--delete-cookies`
    and :option:`--delete-from-keyring` are set, respectively.

    :param args: parsed command line arguments namespace
    :return: boolean indicating whether to exit now if we did stuff
    """
    exit_now = False
    # delete cookies?
    if args.delete_cookies:
        exit_now = True
        cookie_file = args.cookie_file
        print(f"Deleting cookie file '{cookie_file}'")
        try:
            cookie_file.unlink()
            print("Deleted cookie file.")
        except FileNotFoundError:
            print("Cookie file doesn't exist.")
    # delete keyring entries?
    if args.delete_from_keyring:
        exit_now = True
        username = ensure_username(args.username)
        print(
            f"Deleting password and exam number from keyring with username '{username}'."
        )
        delete_keyring_entries(username)
        print("Deleted from keyring")

    return exit_now


def print_file_hash(file_path: Path):
    """Resolve the file path and print its checksum.

    :param file_path: path object to resolve and hash
    :return: a fully resolved path object of the same path
    """
    file_path = file_path.resolve()
    print(f"Found file '{file_path}'.")
    # display hash of file
    with open(file_path, "rb") as file:
        # noinspection PyTypeChecker
        digest = hashlib.file_digest(file, hashlib.md5).hexdigest()
    print(f"MD5 hash of file: {digest}")
    return file_path


def resolve_submit_url(submit_url: str, base: str = URL_SUBMIT_BASE) -> Optional[str]:
    """Normalise the submit-url to ensure it's fully qualified.

    >>> result = "https://teaching.cs.york.ac.uk/student/2021-2/submit/COM00012C/901/A"
    >>> for url in (
    ...     "2021-2/submit/COM00012C/901/A",
    ...     "/2021-2/submit/COM00012C/901/A/",
    ...     "student/2021-2/submit/COM00012C/901/A",
    ...     "/student/2021-2/submit/COM00012C/901/A/",
    ...     "teaching.cs.york.ac.uk/student/2021-2/submit/COM00012C/901/A",
    ...     "//teaching.cs.york.ac.uk/student/2021-2/submit/COM00012C/901/A",
    ...     "https://teaching.cs.york.ac.uk/student/2021-2/submit/COM00012C/901/A",
    ... ):
    ...     assert resolve_submit_url(url) == result
    >>> assert resolve_submit_url("toooodle pip") is None

    :param submit_url: URL to submit to,
        with or without base URL and leading/trailing forward slashes.
    :param base: base URL with protocol and base domain, e.g. the default, :const:`URL_SUBMIT_BASE`
    :return: fully qualified URL with protocol, base domain, and no trailing forward slashes
    """
    match = REGEX_SUBMIT_URL.fullmatch(submit_url)
    if match is None:
        return None
    path = match.group("path")
    path = f"student/{path}/A"
    submit_url = urllib.parse.urljoin(base, path)

    return submit_url


def main_exit_code() -> int:
    """Run the command line script as intended.

    First, we parse the command line arguments.
    If :option:`--delete-from-keyring` or :option:`--delete-cookies` are set, do that, then return.
    If ``FileNotFoundError`` is raised,
    it will be caught and an error message will be shown, then we continue.

    Next, the arguments are preprocessed:
    * :func:`resolve_submit_url` is called on :option:`--submit-url`.
    * :func:`print_file_hash` is called on :option:`--file`.

    A :class:`cookielib.CookieJar` object is constructed
    with :option:`--cookie-file` as ``filename``.
    ``FileNotFoundError`` may be caught and an error message will be shown, then we continue.

    Then, the main even, call :func:`run_requests_session`.

    Finally, save cookies, and return.

    :raises FileNotFoundError: if the file from :option:`--file` does not exist.
    :return: an integer return code to be passed to :func:`sys.exit`
    """
    # load arguments
    parser = get_parser()
    args = parser.parse_args()

    # alternate operations
    if deletion_subcommands(args):
        return 0

    # verify submit url
    submit_url = resolve_submit_url(args.submit_url)
    if submit_url is None:
        print(f"Invalid submit url: '{args.submit_url}'")
        print("It should look something like this:")
        print(URL_SUBMIT_EXAMPLE)
        return 1

    # check zip to be uploaded exists
    file_path = print_file_hash(args.file)

    run_requests_session(args=args, file_path=file_path, submit_url=submit_url)

    print("Finished!")
    return 0


def main():
    """Call :func:`sys.exit` with code from :func:`main_exit_code`."""
    sys.exit(main_exit_code())


if __name__ == "__main__":
    main()
