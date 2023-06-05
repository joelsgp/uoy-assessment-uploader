"""Tool for automating submitting assessments to the University of York Computer Science department.

Files:
    ``teaching-cs-york-ac-uk-chain.pem`` is used as :attr:`requests.Session.verify`,
    due to CA issues.
    See the comments on :const:`PEM_FILE`
"""

import hashlib
import importlib.resources
import urllib.parse
from http.cookiejar import LWPCookieJar
from pathlib import Path

import requests.utils
from bs4 import BeautifulSoup
from requests import Response, Session

from .argument_parser import Namespace, get_parser
from .credentials import (
    delete_from_keyring,
    ensure_exam_number,
    ensure_password,
    ensure_username,
)

__version__ = "0.6.0"


# see here:
# https://stackoverflow.com/questions/27068163/python-requests-not-handling-missing-intermediate-certificate-only-from-one-mach
# https://pypi.org/project/aia/
PEM_FILE = "teaching-cs-york-ac-uk-chain.pem"

URL_EXAM_NUMBER = "https://teaching.cs.york.ac.uk/student/confirm-exam-number"
URL_SUBMIT_BASE = "https://teaching.cs.york.ac.uk/student"

URL_LOGIN = "https://shib.york.ac.uk/idp/profile/SAML2/Redirect/SSO"
URL_LOGIN_PARSED = urllib.parse.urlparse(URL_LOGIN)

# should be like "python-requests/x.y.z"
USER_AGENT_DEFAULT = requests.utils.default_user_agent()
USER_AGENT = f"{USER_AGENT_DEFAULT} {__name__}/{__version__}"


def get_token(response: Response, login_page: bool = False) -> str:
    """Get the CS Portal token from the HTTP response.

    The token is taken from the value of form input element csrf_token, on the login page,
    or from the content of the meta tag csrf-token, for all other webpages.

    :param response: HTTP response from a URL at teaching.cs.york.ac.uk
    :param login_page: If False, parse token from meta tag. If True, parse token from form element.
    :return: the token, an arbitrary string of letters and numbers used for verification
    """
    # could switch to Requests-HTML?
    # https://requests-html.kennethreitz.org/
    soup = BeautifulSoup(response.text, features="html.parser")
    if login_page:
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

    :param session: the HTTP session
        to make requests with and persist cookies onto
    :param csrf_token: the CS department token to send with the login request,
        from :func:`get_token`
    :param username: username from :option:`--username` or :func:`credentials.ensure_username`,
        e.g. ``ab1234``
    :param password: password from :option:`--password`, or,
        more securely, :func:`credentials.ensure_password`
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
    response = session.post(URL_LOGIN, data=payload)
    response.raise_for_status()

    response = login_saml_continue(session, response)
    return response


def login_saml_continue(session: Session, response: Response) -> Response:
    """Perform the second step of the SAML SSO login.

    :param session: the HTTP session
        to make requests with and persist cookies onto
    :param response: HTTP response from the first login step
    :return: the HTTP response object from the login request
    """
    # parse saml response
    soup = BeautifulSoup(response.text, features="html.parser")
    form = soup.find("form")
    action_url = form.attrs["action"]
    form_inputs = form.find_all("input", attrs={"type": "hidden"})
    payload = {}
    for element in form_inputs:
        payload[element["name"]] = element["value"]

    # send saml response back to teaching portal
    response = session.post(action_url, data=payload)
    response.raise_for_status()
    return response


def login_exam_number(session: Session, csrf_token: str, exam_number: str) -> Response:
    """Secondary login to the Teaching Portal, sending the exam number credential using POST.

    :param session: the HTTP session
        to make requests with and persist cookies onto
    :param csrf_token: the CS department token to send with the login request,
        from :func:`get_token`
    :param exam_number: exam number
        from :option:`--exam-number` or :func:`credentials.ensure_exam_number`,
        e.g. Y1234567
    :return: the HTTP response object from the login request, although this is not important,
        as the key part is the cookies which are attached to the session
        (same as :func:`login_saml`).
    """
    params = {
        "_token": csrf_token,
        "examNumber": exam_number,
    }
    response = session.post(URL_EXAM_NUMBER, params=params)
    response.raise_for_status()
    return response


def upload_assignment(
    session: Session, csrf_token: str, submit_url: str, file_path: Path
) -> Response:
    """Upload the completed exam file to the Teaching Portal using POST.

    :param session: the HTTP session
        to make requests with and persist cookies onto
    :param csrf_token: the CS department token to send with the login request,
        from :func:`get_token`
    :param submit_url: the url to submit to, passed verbatim to :meth:`session.post`
        e.g. https://teaching.cs.york.ac.uk/student/2021-2/submit/COM00012C/901/A
    :param file_path: file path to pass to the ``files`` parameter of :meth:`session.post`,
        opened in mode ``rb`` (read bytes).
    :return: the HTTP response object from the submit request
    """
    with open(file_path, "rb") as file:
        file_dict = {"file": (file_path.name, file)}
        form_data = {"_token": csrf_token}
        response = session.post(url=submit_url, data=form_data, files=file_dict)
    return response


def run_requests(
    session: Session,
    args: Namespace,
    submit_url: str,
    file_path: Path,
):
    """Run the actual upload process, using direct HTTP requests.

    Login process:
    A :class:`requests.Session` is used for all steps, to save the cookies between http calls.

    1. Request the submit page.
       The redirect in the response is used to figure out which parts of 3. are needed.
    2. Get the csrf-token from the response using :func:`get_token`
    3. Authentication
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
    :param args: command line arguments namespace containing credentials
    :param submit_url: url passed through to :func:`upload_assignment`
    :param file_path: file path also passed through to :func:`upload_assignment`
    :raises requests.HTTPError: from :meth:`Response.raise_for_status`,
        if any response during the process is not OK.
    """
    dry_run = args.dry_run
    use_keyring = args.use_keyring

    response = session.get(submit_url)
    response.raise_for_status()

    parsed_url = urllib.parse.urlparse(response.url)
    if (parsed_url.hostname, parsed_url.path) == (URL_LOGIN_PARSED.hostname, URL_LOGIN_PARSED.path):
        print("Logging in..")

        if parsed_url.query == URL_LOGIN_PARSED.query:
            # full login required
            print("Logging in from scratch.")
            username = ensure_username(args.username)
            password = ensure_password(username, args.password, use_keyring=use_keyring)
            exam_number = ensure_exam_number(
                username, args.exam_number, use_keyring=use_keyring
            )

            csrf_token = get_token(response, login_page=True)
            response = login_saml(
                session,
                csrf_token,
                username,
                password,
            )
        else:
            # resume login
            print("Refreshing login.")
            username = ensure_username(args.username)
            exam_number = ensure_exam_number(
                username, args.exam_number, use_keyring=use_keyring
            )
            response = login_saml_continue(session, response)

        response.raise_for_status()
        print("Logged in.")

        print("Entering exam number..")
        # the token changes after login
        csrf_token = get_token(response)
        response = login_exam_number(session, csrf_token, exam_number)
        response.raise_for_status()
        print("Entered exam number.")
    elif response.url == URL_EXAM_NUMBER:
        csrf_token = get_token(response)
        print("Entering exam number..")
        exam_number = ensure_exam_number(
            args.username, args.exam_number, use_keyring=use_keyring
        )
        login_exam_number(session, csrf_token, exam_number)
        print("Entered exam number.")
    elif response.url == submit_url:
        csrf_token = get_token(response)
    else:
        raise RuntimeError(f"Unexpected redirect '{response.url}'")

    print("Uploading file...")
    if dry_run:
        print("Skipped actual upload.")
    else:
        response = upload_assignment(session, csrf_token, submit_url, file_path)
        response.raise_for_status()
        print("Uploaded fine.")


def run_requests_session(
    args: Namespace, cookies: LWPCookieJar, file_path: Path, submit_url: str
):
    """Create a session, attach cookies and CA cert file, then run.

    :param args: command line arguments object
    :param cookies: cookie jar object to attach to session
    :param file_path: passed through to :fun:`run_requests`
    :param submit_url: passed through to :fun:`run_requests`
    """
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
                args=args,
                submit_url=submit_url,
                file_path=file_path,
            )


def resolve_submit_url(submit_url: str, base: str = URL_SUBMIT_BASE) -> str:
    """Normalise the submit-url to ensure it's fully qualified.

    :param submit_url: URL to submit to,
        with or without base URL and leading/trailing forward slashes.
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
