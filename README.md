# uoy_assessment_uploader

**If you have an open exam, help me test the new and improved version!! See here: https://github.com/joelsgp/uoy-assessment-uploader/pull/1**


## Install
1. When you have Python and Pip ready, it's as easy as:
   ```shell
   python -m pip install "uoy-assessment-uploader"
   ```
   - or, directly from the repo:
      ```shell
      python -m pip install "git+https://github.com/joelsgp/uoy-assessment-uploader"
      ```
2. As shrimple as that

## Use
Like this:
- ```shell
  python -m uoy_assessment_uploader --help
  ```
  or
- ```shell
  uoy-assessment-uploader --help
  ```

Once it's submitted, you should receive an email to your uni address with confirmation.
The email will show you the MD5 hash, like so:

> MD5 hash of file: 97f212cda7e5200a67749cac560a06f4

If this matches the hash shown by the program, you can be certain you successfully uploaded the right file.

## Example
```shell
uoy-assessment-uploader --username "ab1234" --exam-number "Y1234567" --submit-url "/2021-2/submit/COM00012C/901/A"
```
```
Found file 'exam.zip'.
MD5 hash of file: 05086595c7c7c1a962d6eff6872e18c0
Loading cookie file 'cookies.txt'
No cookies to load!
Logging in..
Password: <PASSWORD HIDDEN>
Logged in.
Entering exam number..
Entered exam number.
Uploading file...
Uploaded fine.
Saved cookies.
Finished!
```
