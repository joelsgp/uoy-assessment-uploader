"""Tool for automating submitting assessments to the University of York Computer Science department."""

import getpass
import hashlib
import re
import sys
from http.cookiejar import LWPCookieJar
from pathlib import Path
from typing import Optional

import keyring
import requests
import requests.utils
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from .parser import parse_args

# todo: re-implement with saml auth and requests, as alternative to selenium
# todo figure out what it do on fails
# todo make flowchart ot figure this confusion out
# todo pyinstaller


__version__ = "0.5.0"

# used for service_name in keyring
NAME = "uoy-assessment-uploader"
RE_SHIBSESSION = re.compile(r'_shibsession_[0-9a-z]{96}')
# timeout for selenium waits, in seconds
TIMEOUT = 10
# should be like "python-requests/x.y.z"
USER_AGENT_DEFAULT = requests.utils.default_user_agent()
USER_AGENT = f"{USER_AGENT_DEFAULT} {NAME}/{__version__}"

URL_SUBMIT_BASE = "https://teaching.cs.york.ac.uk/student"
URL_LOGIN = "https://shib.york.ac.uk/idp/profile/SAML2/Redirect/SSO?execution=e1s1"
URL_EXAM_NUMBER = "https://teaching.cs.york.ac.uk/student/confirm-exam-number"


def login_exam_number(session: requests.Session, token: str, exam_number: str) -> requests.Response:
    params = {
        "_token": token,
        "examNumber": exam_number,
    }
    r = session.post(URL_EXAM_NUMBER, params=params)
    return r


def get_token(session: requests.Session, submit_url: str) -> str:
    r = session.get(submit_url)
    # todo handle fail here
    soup = BeautifulSoup(r.text, features="html.parser")
    tag = soup.find("meta", name="csrf-token")
    token = tag.attrs["content"]
    return token


def upload_assignment(
    session: requests.Session, csrf_token: str, submit_url: str, fp: Path
) -> requests.Response:
    with open(fp, "rb") as file:
        file_dict = {"file": (fp.name, file)}
        form_data = {"_token": csrf_token}
        r = session.post(url=submit_url, data=form_data, files=file_dict)
    return r


def ensure_username(username: Optional[str]) -> str:
    if username is None:
        username = input("Username: ")
    return username


def ensure_password(
    password: Optional[str], username: str, which: str, use_keyring: bool
) -> str:
    service_name = f"{NAME}-{which}"
    # get password
    if password is None and use_keyring:
        password = keyring.get_password(service_name, username)
    if password is None:
        prompt = f"{which}: "
        password = getpass.getpass(prompt)
    # save password to keyring
    if use_keyring:
        keyring.set_password(service_name, username, password)

    return password


def run_requests(
    session: requests.Session,
    submit_url: str,
    username: Optional[str],
    password: Optional[str],
    exam_number: Optional[str],
    file_path: Path,
    dry_run: bool,
    use_keyring: bool,
):
    token = get_token(session, submit_url)
    print("Uploading file...")
    if dry_run:
        print("Skipped actual upload.")
    else:
        upload_assignment(session, token, submit_url, file_path)


def selenium_get_shibsession(submit_url: str, username: str, password: str) -> dict[str, str]:
    # webdriver setup
    # options
    driver_options = webdriver.ChromeOptions()
    # auto installer
    driver_path = ChromeDriverManager().install()
    driver_service = ChromeService(driver_path)
    with webdriver.Chrome(options=driver_options, service=driver_service) as driver:
        driver.implicitly_wait(TIMEOUT)
        wait = WebDriverWait(driver, TIMEOUT)

        driver.get(submit_url)
        login(driver, username, password)
        wait.until(
            ec.any_of(ec.url_to_be(URL_EXAM_NUMBER), ec.url_to_be(submit_url))
        )
        cookies = driver.get_cookies()

    for c in cookies:
        key = next(iter(c.keys()))
        if RE_SHIBSESSION.fullmatch(key):
            return c


def resolve_submit_url(submit_url: str) -> str:
    base = URL_SUBMIT_BASE
    submit_url = submit_url.removeprefix(base).strip("/")
    submit_url = f"{base}/{submit_url}"
    return submit_url


def main():
    # load arguments
    args = parse_args()
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
    if args.delete_cookies:
        args.cookie_file.unlink(missing_ok=True)
    elif args.save_cookies:
        try:
            cookies.load(ignore_discard=True)
        except FileNotFoundError:
            pass

    with requests.Session() as session:
        # session setup
        # todo fix workaround
        session.cookies = cookies
        session.headers.update({"User-Agent": USER_AGENT})
        # session.verify = "teaching-cs-york-ac-uk.pem"
        # session.verify = "GEANTOVRSACA4.crt"
        session.verify = False
        # run
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
        print("Saving cookies.")
        cookies.save(ignore_discard=True)

    print("Finished!")


if __name__ == "__main__":
    main()


def login(driver: WebDriver, username: str, password: str):
    input_username = driver.find_element(By.ID, "username")
    input_username.send_keys(username)
    input_password = driver.find_element(By.ID, "password")
    input_password.send_keys(password)
    input_button = driver.find_element(By.NAME, "_eventId_proceed")
    input_button.click()
