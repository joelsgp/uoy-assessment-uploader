"""Constants including version and URLs."""

__version__ = "0.6.0"

# see here:
# https://stackoverflow.com/questions/27068163/python-requests-not-handling-missing-intermediate-certificate-only-from-one-mach
# https://pypi.org/project/aia/
PEM_FILE = "teaching-cs-york-ac-uk-chain.pem"
# urls
URL_EXAM_NUMBER = "https://teaching.cs.york.ac.uk/student/confirm-exam-number"
URL_LOGIN = "https://shib.york.ac.uk/idp/profile/SAML2/Redirect/SSO?execution=e1s1"
URL_SUBMIT_BASE = "https://teaching.cs.york.ac.uk/student"
