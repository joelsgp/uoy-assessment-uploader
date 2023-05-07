# uoy_assessment_uploader

## Install
1. When you have python and pip ready, it's as easy as:
    ```shell
    python -m pip install "git+https://github.com/joelsgp/uoy-assessment-uploader"
    ```
2. You need the Chrome browser installed. Sorry!
    - I need a cookie management feature Firefox doesn't have.
    - If you have Chromium instead, pass the `--chromium` flag.

## Use
Like this:
- ```shell
  python -m uoy_assessment_uploader --help
  ```
- ```shell
  uoy-assessment-uploader --help
  ```
  
## Example
```shell
uoy-assessment-uploader --username "ab1234" --exam-number "Y1234567" --submit-url "/2021-2/submit/COM00012C/901/A"
```
```
Found file 'exam.zip'.
Password: <PASSWORD HIDDEN>
[WDM] - Downloading: 100%|██████████| 6.98M/6.98M [00:00<00:00, 8.98MB/s]
Loading cookies.
Uploading file...
Uploaded successfully.
Saving cookies.
```
