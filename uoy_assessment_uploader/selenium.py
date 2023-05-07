import json
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver


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
