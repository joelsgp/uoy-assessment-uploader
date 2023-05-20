import getpass
from typing import Optional

import keyring
import keyring.errors


KEYRING_NAME_PASSWORD = "password"
KEYRING_NAME_EXAM_NUMBER = "exam-number"
PROMPT_USERNAME = "Username: "
PROMPT_PASSWORD = "Password: "
PROMPT_EXAM_NUMBER = "Exam number: "


def delete_from_keyring(username: str):
    for keyring_name in (KEYRING_NAME_PASSWORD, KEYRING_NAME_EXAM_NUMBER):
        service_name = f"{__name__}-{keyring_name}"
        print(f"{keyring_name} - deleting from keyring")
        try:
            keyring.delete_password(service_name, username)
            print(f"{keyring_name} - deleted from keyring")
        except keyring.errors.PasswordDeleteError:
            print(f"{keyring_name} - not in keyring")


def ensure_username(username: Optional[str]) -> str:
    if username is None:
        username = input(PROMPT_USERNAME)
    return username


def ensure_password(username: str, password: Optional[str], use_keyring: bool) -> str:
    return ensure_credential(
        username,
        password,
        use_keyring=use_keyring,
        keyring_name=KEYRING_NAME_PASSWORD,
        prompt=PROMPT_PASSWORD,
    )


def ensure_exam_number(
    username: str, exam_number: Optional[str], use_keyring: bool
) -> str:
    return ensure_credential(
        username,
        exam_number,
        use_keyring=use_keyring,
        keyring_name=KEYRING_NAME_EXAM_NUMBER,
        prompt=PROMPT_EXAM_NUMBER,
    )


def ensure_credential(
    username: str,
    credential: Optional[str],
    use_keyring: bool,
    keyring_name: str,
    prompt: str,
) -> str:
    service_name = f"{__name__}-{keyring_name}"
    # try keyring
    got_from_keyring = False
    if use_keyring and credential is None:
        credential = keyring.get_password(service_name, username)
        if credential is None:
            print(f"{keyring_name} - not in keyring")
            got_from_keyring = False
        else:
            print(f"{keyring_name} - got from keyring")
            got_from_keyring = True
    # fall back to getpass
    if credential is None:
        credential = getpass.getpass(prompt)
    # save password to keyring
    if use_keyring and not got_from_keyring:
        keyring.set_password(service_name, username, credential)
        print(f"{keyring_name} - saved to keyring")

    return credential
