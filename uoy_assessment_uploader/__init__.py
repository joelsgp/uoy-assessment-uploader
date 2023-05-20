"""Tool for automating submitting assessments to the University of York Computer Science department."""

import getpass
import hashlib
import importlib.resources
import re
import sys
from http.cookiejar import LWPCookieJar
from pathlib import Path
from typing import Optional

import keyring
import keyring.errors
import requests.utils
from bs4 import BeautifulSoup
from requests import Response, Session

from .argument_parser import parse_args

__version__ = "0.5.0"


# used for service_name in keyring calls
KEYRING_NAME_PASSWORD = "password"
KEYRING_NAME_EXAM_NUMBER = "exam-number"
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
    soup = BeautifulSoup(response.text, features="html.parser")
    tag = soup.find("meta", attrs={"name": "csrf-token"})
    token = tag["content"]
    return token


def login_saml(session: Session, username: str, password: str, token: str) -> Response:
    # get saml response from SSO
    params = {
        "csrf_token_": token,
        "j_username": username,
        "j_password": password,
        "_eventId_proceed": "",
    }
    r = session.post(URL_LOGIN, params=params)
    r.raise_for_status()

    # parse saml response
    soup = BeautifulSoup(r.text, features="html.parser")
    form = soup.find("form")
    action_url = form.attrs["action"]
    form_inputs = form.find_all("input", attrs={"type": "hidden"})
    params = {}
    for fi in form_inputs:
        params[fi["name"]] = fi["value"]

    # send saml response back to teaching portal
    r = session.post(action_url, params=params)
    r.raise_for_status()
    return r


def login_exam_number(session: Session, token: str, exam_number: str) -> Response:
    params = {
        "_token": token,
        "examNumber": exam_number,
    }
    r = session.post(URL_EXAM_NUMBER, params=params)
    r.raise_for_status()
    return r


def upload_assignment(
    session: Session, csrf_token: str, submit_url: str, fp: Path
) -> Response:
    with open(fp, "rb") as file:
        file_dict = {"file": (fp.name, file)}
        form_data = {"_token": csrf_token}
        r = session.post(url=submit_url, data=form_data, files=file_dict)
    return r


def ensure_username(username: Optional[str]) -> str:
    if username is None:
        username = input("Username: ")
    return username


def ensure_credential(
    username: str,
    credential: Optional[str],
    use_keyring: bool,
    keyring_name: str,
    prompt: str,
) -> str:
    service_name = f"{__name__}-{keyring_name}"
    # try keyring
    if credential is None and use_keyring:
        credential = keyring.get_password(service_name, username)
        if credential is None:
            print(f"{keyring_name} - not in keyring")
        else:
            print(f"{keyring_name} - got from keyring")
    # fall back to getpass
    if credential is None:
        credential = getpass.getpass(prompt)
    # save password to keyring
    if use_keyring:
        keyring.set_password(service_name, username, credential)
        print(f"{keyring_name} - saved to keyring")

    return credential


def ensure_password(username: str, password: Optional[str], use_keyring: bool) -> str:
    return ensure_credential(
        username,
        password,
        use_keyring=use_keyring,
        keyring_name=KEYRING_NAME_PASSWORD,
        prompt="Password: ",
    )


def ensure_exam_number(
    username: str, exam_number: Optional[str], use_keyring: bool
) -> str:
    return ensure_credential(
        username,
        exam_number,
        use_keyring=use_keyring,
        keyring_name=KEYRING_NAME_EXAM_NUMBER,
        prompt="Exam number: ",
    )


def keyring_wipe(username: str):
    for which in (KEYRING_NAME_PASSWORD, KEYRING_NAME_EXAM_NUMBER):
        service_name = f"{__name__}-{which}"
        print(f"{which} - deleting from keyring")
        try:
            keyring.delete_password(service_name, username)
            print(f"{which} - deleted from keyring")
        except keyring.errors.PasswordDeleteError:
            print(f"{which} - not in keyring")


def run_requests(
    session: Session,
    submit_url: str,
    username: Optional[str],
    password: Optional[str],
    exam_number: Optional[str],
    file_path: Path,
    dry_run: bool,
    use_keyring: bool,
):
    """Run the actual upload process, using direct http requests.

    Login process:
    1. Request the submit page.
    2. If login is requested, enter username and password with selenium. Get the shibsession cookie.
    3. Retrieve the csrf-token needed alongside the shibsession token for the next steps.
    3. If exam number is requested, submit exam number.
    4. Upload the actual file.
    """
    r = session.get(submit_url)
    r.raise_for_status()
    token = get_token(r)

    if r.url == URL_LOGIN:
        username = ensure_username(username)
        password = ensure_password(password, username, use_keyring=use_keyring)
        exam_number = ensure_exam_number(exam_number, username, use_keyring=use_keyring)

        login_saml(session, username, password, token)
        login_exam_number(session, token, exam_number)
    elif r.url == URL_EXAM_NUMBER:
        exam_number = ensure_exam_number(exam_number, username, use_keyring=use_keyring)

        login_exam_number(session, token, exam_number)
    elif r.url == submit_url:
        pass
    else:
        raise RuntimeError(f"Unexpected redirect '{r.url}'")

    print("Uploading file...")
    if dry_run:
        print("Skipped actual upload.")
    else:
        r = upload_assignment(session, token, submit_url, file_path)
        r.raise_for_status()


def resolve_submit_url(submit_url: str) -> str:
    base = URL_SUBMIT_BASE
    submit_url = submit_url.removeprefix(base).strip("/")
    submit_url = f"{base}/{submit_url}"
    return submit_url


def main():
    # load arguments
    args = parse_args()

    # alternate operations
    exit_now = False
    if args.delete_cookies:
        exit_now = True
        print(f"Deleting cookie file '{args.cookie_file}'")
        args.cookie_file.unlink(missing_ok=True)
    if args.delete_from_keyring:
        exit_now = True
        args.username = ensure_username(args.username)
        keyring_wipe(args.username)
    if exit_now:
        sys.exit()

    # verify arguments
    submit_url = resolve_submit_url(args.submit_url)
    # check zip to be uploaded exists
    try:
        file_path = args.file.resolve()
    except FileNotFoundError:
        print(f"File doesn't exist '{args.file}'.")
        sys.exit(1)
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
            print("Loaded cookies")
        except FileNotFoundError:
            print("No cookies to load!")

    with Session() as session:
        # session setup
        session.cookies = cookies
        session.headers.update({"User-Agent": USER_AGENT})

        with importlib.resources.path(__name__, PEM_FILE) as pem_path:
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
