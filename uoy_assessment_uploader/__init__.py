"""Tool for automating submitting assessments to the University of York Computer Science department."""

import getpass
import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType


# todo: re-implement with saml auth and requests, as alternative to selenium


__version__ = "0.2.1"

# timeout for selenium waits, in seconds
TIMEOUT = 10

DEFAULT_ARG_FILE = "exam.zip"
DEFAULT_ARG_COOKIE_FILE = ".cookies.json"

URL_SUBMIT_BASE = "https://teaching.cs.york.ac.uk/student"
URL_LOGIN = "https://shib.york.ac.uk/idp/profile/SAML2/Redirect/SSO?execution=e1s1"
URL_EXAM_NUMBER = "https://teaching.cs.york.ac.uk/student/confirm-exam-number"


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)

    # core functionality arguments
    parser.add_argument(
        "-n",
        "--submit-url",
        required=True,
        help="The specific exam to upload to, e.g. /2021-2/submit/COM00012C/901/A",
    )
    parser.add_argument("-u", "--username")
    parser.add_argument(
        "--password",
        help="Not recommended to pass this as an argument, for security reasons."
        " Leave it out and you will be securely prompted to enter it at startup.",
    )
    parser.add_argument("-e", "--exam-number")
    parser.add_argument("-f", "--file", type=Path, default=DEFAULT_ARG_FILE)
    # options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log in but don't actually upload the file.",
    )
    # selenium cookies
    parser.add_argument("--cookie-file", type=Path, default=DEFAULT_ARG_COOKIE_FILE)
    parser.add_argument(
        "--no-save-cookies", dest="save_cookies", action="store_false"
    )
    parser.add_argument(
        "--delete-cookies",
        action="store_true",
        help="Before starting, delete previous login cookies (if they exist).",
    )
    # other selenium options
    parser.add_argument(
        "-q",
        "--headless",
        action="store_true",
        help="Hide the browser window. Full auto.",
    )
    parser.add_argument(
        "--chromium", action="store_true", help="Use Chromium instead of Google Chrome."
    )

    return parser


class Args:
    username: str
    password: str
    exam_number: str
    submit_url: str
    file: Path
    dry_run: bool
    cookie_file: Path
    save_cookies: bool
    delete_cookies: bool
    headless: bool
    chromium: bool


def save_cookies(driver: WebDriver, fp: Path):
    cookies = driver.get_cookies()
    with open(fp, "w") as f:
        json.dump(cookies, f)


def load_cookies(driver: webdriver.Chrome, fp: Path):
    try:
        with open(fp) as f:
            cookies = json.load(f)
    except FileNotFoundError:
        print("Not loading cookies, file doesn't exist.")
    else:
        print("Loading cookies.")
        for c in cookies:
            driver.execute_cdp_cmd("Network.setCookie", c)


def login(driver: WebDriver, username: str, password: str):
    input_username = driver.find_element(By.ID, "username")
    input_username.send_keys(username)
    input_password = driver.find_element(By.ID, "password")
    input_password.send_keys(password)
    input_button = driver.find_element(By.NAME, "_eventId_proceed")
    input_button.click()


def enter_exam_number(driver: WebDriver, exam_number: str):
    input_exam_number = driver.find_element(By.ID, "examNumber")
    input_exam_number.send_keys(exam_number)
    input_exam_number.submit()


def upload(driver: WebDriver, file_name: str, dry_run: bool):
    input_file = driver.find_element(By.ID, "file")
    input_file.send_keys(file_name)
    input_checkbox = driver.find_element(By.ID, "ownwork")
    input_checkbox.click()
    if not dry_run:
        input_checkbox.submit()


def ensure_details(
    current: str, prompt: Optional[str] = None, hide: bool = False
) -> str:
    if current is not None:
        return current

    if hide:
        current = getpass.getpass()
    else:
        current = input(prompt)
    return current


def do(
    driver: WebDriver,
    submit_url: str,
    username: Optional[str],
    password: Optional[str],
    exam_number: Optional[str],
    file_name: str,
    dry_run: bool,
):
    wait = WebDriverWait(driver, TIMEOUT)

    # breaks loop on submit
    while True:
        driver.get(submit_url)
        # username/password login page
        if driver.current_url == URL_LOGIN:
            print("Logging in..")
            username = ensure_details(username, "Enter username: ")
            password = ensure_details(password, hide=True)
            login(driver, username, password)
            wait.until(
                ec.any_of(ec.url_to_be(URL_EXAM_NUMBER), ec.url_to_be(submit_url))
            )
        # exam number login page
        elif driver.current_url == URL_EXAM_NUMBER:
            print("Entering exam number..")
            exam_number = ensure_details(exam_number, "Enter exam number: ")
            enter_exam_number(driver, exam_number)
            wait.until(ec.url_to_be(submit_url))
        # logged in, upload page
        elif driver.current_url == submit_url:
            print("Uploading file...")
            upload(driver, file_name, dry_run)
            if dry_run:
                print("Skipped actual upload.")
            else:
                wait.until(
                    ec.text_to_be_present_in_element(
                        [By.CLASS_NAME, "alert-success"], "File submitted successfully."
                    )
                )
                print("Uploaded successfully.")
            break
        else:
            raise Exception("bruh")


def resolve_submit_url(submit_url: str) -> str:
    base = URL_SUBMIT_BASE
    submit_url = submit_url.removeprefix(base).strip("/")
    submit_url = f"{base}/{submit_url}"
    return submit_url


def main():
    # load arguments
    parser = get_parser()
    args = Args()
    parser.parse_args(namespace=args)

    # check zip to be uploaded exists
    if not args.file.is_file():
        print(f"File doesn't exist '{args.file}'.")
        sys.exit(1)
    print(f"Found file '{args.file}'.")
    file_name = str(args.file.resolve())

    # verify arguments
    submit_url = resolve_submit_url(args.submit_url)

    # webdriver setup
    # options
    driver_options = webdriver.ChromeOptions()
    if args.headless:
        driver_options.add_argument("--headless")

    # auto installer
    if args.chromium:
        chrome_type = ChromeType.CHROMIUM
    else:
        chrome_type = ChromeType.GOOGLE
    driver_path = ChromeDriverManager(chrome_type=chrome_type).install()
    driver_service = ChromeService(driver_path)

    with webdriver.Chrome(options=driver_options, service=driver_service) as driver:
        driver.implicitly_wait(TIMEOUT)

        # load cookies
        if args.delete_cookies:
            args.cookie_file.unlink(missing_ok=True)
        elif args.save_cookies:
            load_cookies(driver, args.cookie_file)

        # run
        do(
            driver=driver,
            submit_url=submit_url,
            username=args.username,
            password=args.password,
            exam_number=args.exam_number,
            file_name=file_name,
            dry_run=args.dry_run,
        )

        # save cookies
        if args.save_cookies:
            print("Saving cookies.")
            save_cookies(driver, args.cookie_file)


if __name__ == "__main__":
    main()
