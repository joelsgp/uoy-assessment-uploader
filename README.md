# uoy_assessment_uploader

## Install
1. When you have Python and Pip ready, it's as easy as:
   ```shell
   python -m pip install "uoy-assessment-uploader"
   ```
   - or, directly from the repo:
      ```shell
      python -m pip install "git+https://github.com/joelsgp/uoy-assessment-uploader"
      ```
2. You need the Chrome browser installed. Sorry!
    - I need a cookie management feature Firefox doesn't have.
    - Chromium and Ungoogled Chrome should work too.

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
[WDM] - Downloading: 100%|██████████| 6.98M/6.98M [00:00<00:00, 8.98MB/s]
Loading cookies.
Logging in..
Password: <PASSWORD HIDDEN>
Entering exam number..
Uploading file...
Uploaded successfully.
Saving cookies.
Finished!
```
