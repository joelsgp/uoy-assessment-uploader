"""Tool for automating submitting assessments to the University of York Computer Science department."""

import getpass
import json
from argparse import ArgumentParser
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec


# todo: re-implement with saml auth and requests, as alternative to selenium


__version__ = "0.1.0"

# timeout for selenium waits, in seconds
TIMEOUT = 10
URL_SUBMIT_BASE = "https://teaching.cs.york.ac.uk/student"
URL_LOGIN = "https://shib.york.ac.uk/idp/profile/SAML2/Redirect/SSO?execution=e1s1"
URL_EXAM_NUMBER = "https://teaching.cs.york.ac.uk/student/confirm-exam-number"


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)

    parser.add_argument("-u", "--username", required=True)
    parser.add_argument(
        "--password",
        help="Not recommended to pass this as an argument, for security reasons."
        " Leave it out and you will be securely prompted to enter it at startup.",
    )
    parser.add_argument("-e", "--exam-number", required=True)
    parser.add_argument("-f", "--file", type=Path, default="exam.zip")
    parser.add_argument(
        "-n",
        "--submit-url",
        required=True,
        help="The specific exam to upload to, e.g. /2021-2/submit/COM00012C/901/A",
    )
    parser.add_argument("--cookie-file", type=Path, default=".cookies.json")
    parser.add_argument(
        "--no-save-cookies", dest="do_save_cookies", action="store_false"
    )
    parser.add_argument("-q", "--headless", action="store_true")

    return parser


def save_cookies(driver: WebDriver, fp: Path):
    cookies = driver.get_cookies()
    with open(fp, "w") as f:
        json.dump(cookies, f)


def load_cookies(driver: webdriver.Chrome, fp: Path):
    try:
        with open(fp) as f:
            cookies = json.load(f)
    except FileNotFoundError:
        print("Not loading cookies, file doesn't exist")
    else:
        print("Loading cookies")
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


def upload(driver: WebDriver, fp: Path):
    input_file = driver.find_element(By.ID, "file")
    input_file.send_keys(str(fp.resolve()))
    input_checkbox = driver.find_element(By.ID, "ownwork")
    input_checkbox.click()
    input_checkbox.submit()


def do(
    driver: WebDriver,
    submit_url: str,
    username: str,
    password: str,
    exam_number: str,
    fp: Path,
):
    wait = WebDriverWait(driver, TIMEOUT)

    while True:
        driver.get(submit_url)
        if driver.current_url == URL_LOGIN:
            print("Logging in..")
            login(driver, username, password)
            wait.until(
                ec.any_of(ec.url_to_be(URL_EXAM_NUMBER), ec.url_to_be(submit_url))
            )
        elif driver.current_url == URL_EXAM_NUMBER:
            print("Entering exam number..")
            enter_exam_number(driver, exam_number)
            wait.until(ec.url_to_be(submit_url))
        elif driver.current_url == submit_url:
            print("Uploading file...")
            upload(driver, fp)
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
    args = parser.parse_args()

    username: str = args.username
    password: str = args.password or getpass.getpass()
    exam_number: str = args.exam_number
    submit_url: str = resolve_submit_url(args.submit_url)
    fp: Path = args.file
    cookie_path: Path = args.cookie_file
    do_save_cookies: bool = args.do_save_cookies
    headless: bool = args.headless

    # todo check fp exists

    # start webdriver
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(TIMEOUT)

    # load cookies
    if do_save_cookies:
        load_cookies(driver, cookie_path)

    # run
    try:
        do(
            driver=driver,
            submit_url=submit_url,
            username=username,
            password=password,
            exam_number=exam_number,
            fp=fp,
        )
    except Exception:
        raise
    else:
        # save cookies
        if do_save_cookies:
            print("Saving cookies")
            save_cookies(driver, cookie_path)

    # exit
    # todo context manager
    input("Press ENTER to close driver:\n")
    driver.close()


if __name__ == "__main__":
    main()
