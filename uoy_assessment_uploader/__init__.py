"""Tool for automating submitting assessments to the University of York Computer Science department.

Files:
    ``teaching-cs-york-ac-uk-chain.pem`` is used as :attr:`requests.Session.verify`,
    due to CA issues.
    See the comments on :const:`PEM_FILE`
"""

import hashlib
import urllib.parse
from http.cookiejar import LWPCookieJar

from .argparse import get_parser
from .constants import URL_SUBMIT_BASE, __version__
from .credentials import delete_from_keyring, ensure_username
from .requests import run_requests_session


def resolve_submit_url(submit_url: str, base: str = URL_SUBMIT_BASE) -> str:
    """Normalise the submit-url to ensure it's fully qualified.

    >>> resolve_submit_url("2021-2/submit/COM00012C/901/A")
    "https://teaching.cs.york.ac.uk/student/2021-2/submit/COM00012C/901/A"
    >>> resolve_submit_url("https://teaching.cs.york.ac.uk/student/2021-2/submit/COM00012C/901/A")
    https://teaching.cs.york.ac.uk/student/2021-2/submit/COM00012C/901/A
    >>> resolve_submit_url("/student/2021-2/submit/COM00012C/901/A")
    https://teaching.cs.york.ac.uk/student/2021-2/submit/COM00012C/901/A
    >>> resolve_submit_url("teaching.cs.york.ac.uk/student/2021-2/submit/COM00012C/901/A/")
    https://teaching.cs.york.ac.uk/student/2021-2/submit/COM00012C/901/A

    :param submit_url: URL to submit to,
        with or without base URL and leading/trailing forward slashes.
    :param base: base URL with protocol and base domain, e.g. the default, :const:`URL_SUBMIT_BASE`
    :return: fully qualified URL with protocol, base domain, and no trailing forward slashes
    """
    parsed_base = urllib.parse.urlparse(base)
    parsed = urllib.parse.urlparse(submit_url, scheme=parsed_base.scheme)

    stripped_path = parsed.path.removeprefix(parsed_base.path)
    parsed._replace(path=stripped_path)
    unparsed = urllib.parse.urlunparse(parsed)
    submit_url = urllib.parse.urljoin(base, unparsed)

    return submit_url


def main():
    """Run the command line script as intended.

    First, we parse the command line arguments.
    If :option:`--delete-from-keyring` or :option:`--delete-cookies` are set, do that, then return.
    If ``FileNotFoundError`` is raised,
    it will be caught and an error message will be shown, then we continue.

    Next, the arguments are preprocessed:
    :func:`resolve_submit_url` is called on :option:`--submit-url`.
    The :option:`--file` option is resolved, and its hash is printed.

    A :class:`cookielib.CookieJar` object is constructed
    with :option:`--cookie-file` as ``filename``.
    ``FileNotFoundError`` may be caught and an error message will be shown, then we continue.

    Then, the main even, call :func:`run_requests_session`.

    Finally, save cookies, and return.

    :raises FileNotFoundError: if the file from :option:`--file` does not exist.
    """
    # load arguments
    parser = get_parser()
    args = parser.parse_args()

    # alternate operations
    exit_now = False
    if args.delete_cookies:
        exit_now = True
        print(f"Deleting cookie file '{args.cookie_file}'")
        try:
            args.cookie_file.unlink()
            print("Deleted cookie file.")
        except FileNotFoundError:
            print("Cookie file doesn't exist.")
    if args.delete_from_keyring:
        print("Deleting password and exam number from keyring.")
        exit_now = True
        username = ensure_username(args.username)
        delete_from_keyring(username)
    if exit_now:
        return

    # verify arguments
    submit_url = resolve_submit_url(args.submit_url)
    # check zip to be uploaded exists
    file_path = args.file.resolve()
    print(f"Found file '{file_path}'.")
    # display hash of file
    with open(file_path, "rb") as file:
        # noinspection PyTypeChecker
        digest = hashlib.file_digest(file, hashlib.md5).hexdigest()
    print(f"MD5 hash of file: {digest}")

    # load cookies
    cookies = LWPCookieJar(args.cookie_file)
    if args.save_cookies:
        print(f"Loading cookie file '{args.cookie_file}'")
        try:
            cookies.load(ignore_discard=True)
            print("Loaded cookies.")
        except FileNotFoundError:
            print("No cookies to load!")

    run_requests_session(
        args=args, cookies=cookies, file_path=file_path, submit_url=submit_url
    )

    # save cookies
    if args.save_cookies:
        cookies.save(ignore_discard=True)
        print("Saved cookies.")

    print("Finished!")


if __name__ == "__main__":
    main()
