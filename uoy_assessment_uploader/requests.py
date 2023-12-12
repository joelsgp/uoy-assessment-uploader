"""Functions to carry out the actual login and submission process, using :mod:`requests`."""

import urllib.parse
from http.cookiejar import LWPCookieJar
from pathlib import Path

import requests.utils
from bs4 import BeautifulSoup
from requests import Response, Session

from .argparse import Namespace
from .constants import NAME, URL_EXAM_NUMBER, URL_LOGIN, __version__
from .credentials import ensure_exam_number, ensure_password, ensure_username

# user agent
# should be like "python-requests/x.y.z"
USER_AGENT_DEFAULT = requests.utils.default_user_agent()
USER_AGENT = f"{USER_AGENT_DEFAULT} {NAME}/{__version__}"


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
        form_data = {"ownwork": 1, "_token": csrf_token}
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

    parsed_base = urllib.parse.urlparse(URL_LOGIN)
    parsed = urllib.parse.urlparse(response.url)

    if (parsed.hostname, parsed.path) == (parsed_base.hostname, parsed_base.path):
        print("Logging in..")

        if parsed.query == parsed_base.query:
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


def run_requests_session(args: Namespace, file_path: Path, submit_url: str):
    """Create a session, attach cookies and CA cert file, then run.

    :param args: command line arguments object
    :param file_path: passed through to :func:`run_requests`
    :param submit_url: passed through to :func:`run_requests`
    """
    # load cookies
    cookies = LWPCookieJar(args.cookie_file)
    # create cookie file's folder if it doesn't exist
    args.cookie_file.parent.mkdir(parents=True, exist_ok=True)
    if args.save_cookies:
        load_cookies(cookies)

    with Session() as session:
        # session setup
        session.cookies = cookies
        session.headers.update({"User-Agent": USER_AGENT})

        run_requests(
            session=session,
            args=args,
            submit_url=submit_url,
            file_path=file_path,
        )

        # save cookies
        if args.save_cookies:
            print(f"Saving cookie file '{cookies.filename}'")
            cookies.save(ignore_discard=True)
            print("Saved cookies.")


def load_cookies(cookies: LWPCookieJar):
    """Try to call the cookie jar's :meth:`cookies.load` method.

    ignore_discard is used.
    If the file :attr:`cookies.filename` doesn't exist, this function will
    catch FileNotFoundError and print an error message.

    :param cookies: cookie jar to load
    """
    print(f"Loading cookie file '{cookies.filename}'")
    try:
        cookies.load(ignore_discard=True)
        print("Loaded cookies.")
    except FileNotFoundError:
        print("No cookies to load!")
