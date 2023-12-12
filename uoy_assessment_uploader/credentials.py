"""Helper functions for getting login details from standard input and from persistent locations."""

import getpass
from typing import Optional

import keyring
import keyring.errors

from .constants import NAME

# used for service_name in keyring calls
KEYRING_NAME_PASSWORD = "password"
KEYRING_NAME_EXAM_NUMBER = "exam-number"
# used for input/getpass prompts
PROMPT_USERNAME = "Username: "
PROMPT_PASSWORD = "Password: "
PROMPT_EXAM_NUMBER = "Exam number: "


def get_service_name(credential: str) -> str:
    return f"{NAME}-{credential}"


def delete_keyring_entries(username: str):
    """Delete password and exam number from keyring based on username.

    The service name used is uoy-assessment-uploader plus
    with ``-username`` and ``-exam-number`` for username and exam number respectively.

    :param username: Username passed to :func:`keyring.delete_password`
    """
    for keyring_name in (KEYRING_NAME_PASSWORD, KEYRING_NAME_EXAM_NUMBER):
        service_name = get_service_name(keyring_name)
        print(f"{keyring_name} - deleting from keyring")
        try:
            keyring.delete_password(service_name, username)
            print(f"{keyring_name} - deleted from keyring")
        except keyring.errors.PasswordDeleteError:
            print(f"{keyring_name} - not in keyring")


def ensure_username(username: Optional[str]) -> str:
    """Ensure username is not None by getting it from input.

    The prompt for input is :const:`PROMPT_USERNAME`.

    :param username: either None, or the username, e.g. ``ab1234``
    :return: the same username, or a username requested from stdin, if the argument was None
    """
    if username is None:
        username = input(PROMPT_USERNAME)
    return username


def ensure_password(username: str, password: Optional[str], use_keyring: bool) -> str:
    """Wrap :func:`ensure_credential` to fill in ``password`` if it is None.

    The extra arguments passed to :func:`ensure_credential` are
        :const:`KEYRING_NAME_PASSWORD` for ``keyring_name``,
        and :const:`PROMPT_PASSWORD` for ``prompt``.

    :param username: passed through to :func:`ensure_credential`
    :param password: passed through to :func:`ensure_credential`
    :param use_keyring: passed through to :func:`ensure_credential`
    :return: the password returned from :func:`ensure_credential`
    """
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
    """Wrap :func:`ensure_credential` to fill in ``exam_number`` if it is None.

    The extra arguments passed to :func:`ensure_credential` are
        :const:`KEYRING_NAME_EXAM_NUMBER` for ``keyring_name``,
        and :const:`PROMPT_EXAM_NUMBER` for ``prompt``.

    :param username: passed through to :func:`ensure_credential`
    :param exam_number: passed through to :func:`ensure_credential`
    :param use_keyring: passed through to :func:`ensure_credential`
    :return: the exam number returned from :func:`ensure_credential`
    """
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
    """Ensure ``credential`` is not None by getting it from getpass or from the keyring.

    The prompt for getpass is :const:`PROMPT_USERNAME`.

    :param username: username passed through to :mod:`keyring`
    :param credential: either None,
        or the secret passphrase to be returned.
    :param use_keyring: whether to use :mod:`keyring` to save the credential.
        If this is True, this function will attempt to retrieve the credential,
        using :func:`keyring.get_password`.
        When the credential is not in the keyring, fall back to getpass.
        Finally, the credential is saved to the keyring for next time.
    :param keyring_name: passed to :func:`get_service_name`
        to get the ``service_name`` to pass to :mod:`keyring`
    :param prompt: prompt for :func:`getpass` to use
        if the credential is not retrieved from the keyring.
    :return: the new credential, or the original argument, if it was not None.
    """
    service_name = get_service_name(keyring_name)
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
