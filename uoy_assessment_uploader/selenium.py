import json
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from uoy_assessment_uploader import TIMEOUT, URL_EXAM_NUMBER, URL_LOGIN, ensure_password, ensure_username


def save_cookies(driver: WebDriver, fp: Path):
    cookies = driver.get_cookies()
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=4)


def load_cookies(driver: webdriver.Chrome, fp: Path):
    try:
        with open(fp, encoding="utf-8") as f:
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


def run_selenium(
    driver: WebDriver,
    submit_url: str,
    username: Optional[str],
    password: Optional[str],
    exam_number: Optional[str],
    file_name: str,
    dry_run: bool,
    use_keyring: bool,
):
    wait = WebDriverWait(driver, TIMEOUT)

    # breaks loop on submit
    while True:
        driver.get(submit_url)
        # username/password login page
        if driver.current_url == URL_LOGIN:
            print("Logging in..")
            username = ensure_username(username)
            password = ensure_password(
                password, username, which="Password", use_keyring=use_keyring
            )
            login(driver, username, password)
            wait.until(
                ec.any_of(ec.url_to_be(URL_EXAM_NUMBER), ec.url_to_be(submit_url))
            )
        # exam number login page
        elif driver.current_url == URL_EXAM_NUMBER:
            print("Entering exam number..")
            username = ensure_username(username)
            exam_number = ensure_password(
                exam_number, username, which="Exam number", use_keyring=use_keyring
            )
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
