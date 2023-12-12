# uoy_assessment_uploader

PyPI page: https://pypi.org/project/uoy-assessment-uploader/

## Install
1. When you have Python and Pip ready, it's as easy as:
   ```shell
   python -m pip install "uoy-assessment-uploader"
   ```
2. As shrimple as that

### Alternative install
- You can also install it directly from the repo with pip:
    ```shell
    python -m pip install "git+https://github.com/joelsgp/uoy-assessment-uploader.git"
    ```

- Or on an alpm (Arch) Linux system you can get it from the AUR at https://aur.archlinux.org/packages/uoy-assessment-uploader.
    ```shell
    paru uoy-assessment-uploader
    ```

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
uoy-assessment-uploader --dry-run \
    --username "ab1234" --exam-number "Y1234567" \
    --submit-url "https://teaching.cs.york.ac.uk/student/2021-2/submit/COM00012C/901/A"
```

```
Found file '/home/joelm/src/uoy-assessment-uploader/exam.zip'.
MD5 hash of file: 8bbd39fa6a215eb1ea43c34b0da764b9
Loading cookie file 'cookies.txt'
Loaded cookies.
Logging in..
Logging in from scratch.
Password: <PASSWORD HIDDEN>
Logged in.
Entering exam number..
Entered exam number.
Uploading file...
Skipped actual upload.
Saving cookie file 'cookies.txt'
Saved cookies.
Finished!
```
