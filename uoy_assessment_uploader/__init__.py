"""Tool for automating submitting assessments to the University of York Computer Science department.

Files:
    ``teaching-cs-york-ac-uk-chain.pem`` is used as :attr:`requests.Session.verify` due to CA issues.
    See the comments on :const:`PEM_FILE`
"""

import hashlib
import importlib.resources
import re
from http.cookiejar import LWPCookieJar
from pathlib import Path
from typing import Optional

import requests.utils
from bs4 import BeautifulSoup
from requests import Response, Session

from .argument_parser import parse_args
from .credentials import (
    delete_from_keyring,
    ensure_exam_number,
    ensure_password,
    ensure_username,
)


__version__ = "0.5.2"


# see here:
# https://stackoverflow.com/questions/27068163/python-requests-not-handling-missing-intermediate-certificate-only-from-one-mach
# https://pypi.org/project/aia/
PEM_FILE = "teaching-cs-york-ac-uk-chain.pem"
RE_SHIBSESSION_COOKIE_NAME = re.compile(r"_shibsession_[0-9a-z]{96}")
URL_SUBMIT_BASE = "https://teaching.cs.york.ac.uk/student"
URL_LOGIN = "https://shib.york.ac.uk/idp/profile/SAML2/Redirect/SSO?execution=e1s1"
URL_EXAM_NUMBER = "https://teaching.cs.york.ac.uk/student/confirm-exam-number"
# should be like "python-requests/x.y.z"
USER_AGENT_DEFAULT = requests.utils.default_user_agent()
USER_AGENT = f"{USER_AGENT_DEFAULT} {__name__}/{__version__}"


def get_token(response: Response) -> str:
    """Get the CS Portal token from the HTTP response.

    The token is taken from the value of form input element csrf_token, on the login page,
    or from the content of the meta tag csrf-token, for all other webpages.

    :param response: HTTP response from a URL at teaching.cs.york.ac.uk
    :return: the token, an arbitrary string of letters and numbers used for verification
    """
    # todo switch to Requests-HTML?
    soup = BeautifulSoup(response.text, features="html.parser")
    if response.url == URL_LOGIN:
        tag = soup.find("input", attrs={"type": "hidden", "name": "csrf_token"})
        token = tag["value"]
    else:
        tag = soup.find("meta", attrs={"name": "csrf-token"})
        token = tag["content"]

    return token


def login_saml(
    session: Session, csrf_token: str, username: str, password: str
) -> Response:
    """Login to the Teaching Portal using SSO (SAML Single Sign-On) using POST.

    :param session: the HTTP session to make requests with and persist cookies onto
    :param csrf_token: the CS department token to send with the login request, from :func:`get_token`
    :param username: username from :option:`--username` or :func:`credentials.ensure_username`,
        e.g. ``ab1234``
    :param password: password from :option:`--password`, or, more securely, :func:`credentials.ensure_password`
    :return: the HTTP response object from the login request, although this is not important,
        as the key part is the cookies which are attached to the session.
    """
    # get saml response from SSO
    payload = {
        "csrf_token": csrf_token,
        "j_username": username,
        "j_password": password,
        "_eventId_proceed": "",
    }
    r = session.post(URL_LOGIN, data=payload)
    r.raise_for_status()

    # parse saml response
    soup = BeautifulSoup(r.text, features="html.parser")
    form = soup.find("form")
    action_url = form.attrs["action"]
    form_inputs = form.find_all("input", attrs={"type": "hidden"})
    payload = {}
    for fi in form_inputs:
        payload[fi["name"]] = fi["value"]

    # send saml response back to teaching portal
    r = session.post(action_url, data=payload)
    r.raise_for_status()
    return r


def login_exam_number(session: Session, csrf_token: str, exam_number: str) -> Response:
    """Secondary login to the Teaching Portal, sending the exam number credential using POST.

    :param session: the HTTP session to make requests with and persist cookies onto
    :param csrf_token: the CS department token to send with the login request, from :func:`get_token`
    :param exam_number: exam number from :option:`--exam-number` or :func:`credentials.ensure_exam_number`,
        e.g. Y1234567
    :return: the HTTP response object from the login request, although this is not important,
        as the key part is the cookies which are attached to the session (same as :func:`login_saml`).
    """
    params = {
        "_token": csrf_token,
        "examNumber": exam_number,
    }
    r = session.post(URL_EXAM_NUMBER, params=params)
    r.raise_for_status()
    return r


def upload_assignment(
    session: Session, csrf_token: str, submit_url: str, file_path: Path
) -> Response:
    """Upload the completed exam file to the Teaching Portal using POST.

    :param session: the HTTP session to make requests with and persist cookies onto
    :param csrf_token: the CS department token to send with the login request, from :func:`get_token`
    :param submit_url: the url to submit to, passed verbatim to :meth:`session.post`
        e.g. https://teaching.cs.york.ac.uk/student/2021-2/submit/COM00012C/901/A
    :param file_path: file path to pass to the ``files`` parameter of :meth:`session.post`,
        opened in mode ``rb`` (read bytes).
    :return: the HTTP response object from the submit request
    """
    with open(file_path, "rb") as file:
        file_dict = {"file": (file_path.name, file)}
        form_data = {"_token": csrf_token}
        r = session.post(url=submit_url, data=form_data, files=file_dict)
    return r


def run_requests(
    session: Session,
    username: Optional[str],
    password: Optional[str],
    exam_number: Optional[str],
    use_keyring: bool,
    submit_url: str,
    file_path: Path,
    dry_run: bool,
):
    """Run the actual upload process, using direct HTTP requests.

    Login process:
    0. A :class:`requests.Session` is used for all steps, to save the cookies between http calls.
    1. Request the submit page. The redirect in the response is used to figure out which parts of 3. are needed.
    2. Get the csrf-token from the response using :func:`get_token`
    3.
        1. If login is needed, follow the SAML auth process with requests, then proceed to 3.2.
            First we make sure we have both username and password,
            using :func:`ensure_username` and :func:`ensure_password`. Making these optional means
            we don't have to retrieve them if the saved cookies allow us to go right ahead.
            Then we do the login process using :func:`login_saml`.
        2. If the exam number is needed, submit the exam number.
            First we make sure we have the exam number using :func:`ensure_exam_number`.
            Then we send it using :func:`login_exam_number`.
    4. Upload the actual file using :func:`upload_assignment`.

    :param session: the HTTP session to make requests with and persist cookies onto
    :param username: username which may or may not be used, and may be None to enable lazy loading (:mod:`credentials`)
    :param password: password, also optional
    :param exam_number: exam number, also optional
    :param use_keyring: passed through to :mod:`credentials` functions
        to enable or disable saving details in the keyring
    :param submit_url: url passed through to :func:`upload_assignment`
    :param file_path: file path also passed through to :func:`upload_assignment`
    :param dry_run: set this to True in order to skip the actual upload, only doing the login process.
        Useful for testing. The only argument to this function that isn't passed through to another function
    :raises requests.HTTPError: from :meth:`Response.raise_for_status`, if any response during the process is not OK.
    """
    r = session.get(submit_url)
    r.raise_for_status()
    csrf_token = get_token(r)

    if r.url == URL_LOGIN:
        print("Logging in..")
        username = ensure_username(username)
        password = ensure_password(username, password, use_keyring=use_keyring)
        exam_number = ensure_exam_number(username, exam_number, use_keyring=use_keyring)

        r = login_saml(
            session,
            csrf_token,
            username,
            password,
        )
        print("Logged in.")

        print("Entering exam number..")
        # the token changes after login
        csrf_token = get_token(r)
        login_exam_number(session, csrf_token, exam_number)
        print("Entered exam number.")
    elif r.url == URL_EXAM_NUMBER:
        print("Entering exam number..")
        exam_number = ensure_exam_number(username, exam_number, use_keyring=use_keyring)
        login_exam_number(session, csrf_token, exam_number)
        print("Entered exam number.")
    elif r.url == submit_url:
        pass
    else:
        raise RuntimeError(f"Unexpected redirect '{r.url}'")

    print("Uploading file...")
    if dry_run:
        print("Skipped actual upload.")
    else:
        r = upload_assignment(session, csrf_token, submit_url, file_path)
        r.raise_for_status()
        print("Uploaded fine.")


def resolve_submit_url(submit_url: str, base: str = URL_SUBMIT_BASE) -> str:
    """Normalise the submit-url to ensure it's fully qualified.

    :param submit_url: URL to submit to, with or without base URL and leading plus trailing forward slashes.
    :param base: base URL with protocol and base domain, e.g. the default, :const:`URL_SUBMIT_BASE`
    :return: fully qualified URL with protocol, base domain, and no trailing forward slashes
    """
    submit_url = submit_url.removeprefix(base).strip("/")
    submit_url = f"{base}/{submit_url}"
    return submit_url


def main():
    """Run the command line script as intended.

    First, we parse the command line arguments.
    If :option:`--delete-from-keyring` or :option:`--delete-cookies` are set, do that, then return.
        If ``FileNotFoundError`` is raised, it will be caught and an error message will be shown, then we continue.

    Next, the arguments are preprocessed: :func:`resolve_submit_url` is called on :option:`--submit-url`.
        The :option:`--file` option is resolved, and its hash is printed.

    A :class:`cookielib.CookieJar` object is constructed with :option:`--cookie-file` as ``filename``.
        ``FileNotFoundError`` may be caught and an error message will be shown, then we continue.

    The main event, create a requests :class:`Session`, then call :func:`run_requests`.

    Finally, save cookies, and finish.

    :raises FileNotFoundError: if the file from :option:`--file` does not exist.
    """
    # load arguments
    args = parse_args()

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
        args.username = ensure_username(args.username)
        delete_from_keyring(args.username)
    if exit_now:
        return

    # verify arguments
    submit_url = resolve_submit_url(args.submit_url)
    # check zip to be uploaded exists
    file_path = args.file.resolve()
    print(f"Found file '{file_path}'.")
    # display hash of file
    with open(file_path, "rb") as f:
        # noinspection PyTypeChecker
        digest = hashlib.file_digest(f, hashlib.md5).hexdigest()
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

    with Session() as session:
        # session setup
        session.cookies = cookies
        session.headers.update({"User-Agent": USER_AGENT})

        files = importlib.resources.files(__package__)
        pem_traversable = files.joinpath(PEM_FILE)
        with importlib.resources.as_file(pem_traversable) as pem_path:
            session.verify = pem_path
            run_requests(
                session=session,
                submit_url=submit_url,
                username=args.username,
                password=args.password,
                exam_number=args.exam_number,
                file_path=file_path,
                dry_run=args.dry_run,
                use_keyring=args.use_keyring,
            )

    # save cookies
    if args.save_cookies:
        cookies.save(ignore_discard=True)
        print("Saved cookies.")

    print("Finished!")


if __name__ == "__main__":
    main()
