# Backend

A single Python Lambda that creates presigned S3 URLs. It has no dependencies beyond `boto3`, which is already in the Lambda Python runtime, so there is nothing to package.

| File | Contents |
|---|---|
| `app.py` | The part worth walking through: the S3 client, the handler, and the two presigned URLs |
| `utils.py` | Plumbing: request parsing and validation, filename cleanup, env var config, response helper |

In the console, create both files in the editor (`app.py` and `utils.py`, same folder) and deploy.

## What it does

The Lambda handles two kinds of request on its Function URL.

**`POST` (from the web app): create the links**
1. Validates the request (`filename`, `size`, optional `contentType`).
2. Picks a key: `<random uuid>/<sanitised filename>`.
3. Returns a **presigned POST** for upload (S3 enforces the size limit) and a **share link** for download.

**`GET /?k=<key>` (a friend opening the share link): serve the file**
1. Checks the key looks right and the file exists.
2. Checks the file is no older than `EXPIRES_IN` (otherwise `410 This link has expired.`).
3. Redirects (`302`) to a freshly presigned S3 download link that lives for 60 seconds.

**Why a short share link instead of sharing the presigned URL directly?** A presigned URL signed with role credentials carries a very long session token full of `+`, `/` and `=`. Some browsers, extensions and chat apps rewrite those characters when a link is copied, which silently breaks it (S3 answers `InvalidToken`). The share link uses only safe characters, and the long signed URL is only ever followed by the browser's redirect, never copied by a person.

The request and response format is documented in `../frontend/README.md`.

## Configuration

Set these as Lambda environment variables:

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `BUCKET_NAME` | yes | | Bucket that receives uploads |
| `EXPIRES_IN` | no | `3600` | Link lifetime in seconds, capped at 3600. Use `60` to demo expiry. |
| `MAX_BYTES` | no | `104857600` | Maximum upload size (100 MB) |

## IAM

The execution role needs only these actions, on `arn:aws:s3:::<bucket>/*`:

- `s3:PutObject` (for the upload URL)
- `s3:GetObject` (for the download URL, and for checking the file exists before redirecting)

A presigned URL carries the signer's permissions. If the role lacks them, the URLs are generated but S3 returns 403 when used.

## Notes

- **CORS** is configured on the Function URL, not in code. Adding headers here as well would duplicate them and the browser would reject the response.
- **Expiry limit:** a URL signed with Lambda role credentials stops working when those temporary credentials expire. That is why expiry is capped at one hour.
- **Console test event:**
  ```json
  { "body": "{\"filename\":\"hello.txt\",\"size\":11,\"contentType\":\"text/plain\"}" }
  ```
  The Test tab has no web address, so there the `downloadUrl` is a raw presigned URL instead of a share link.
- **Expiry is measured from the upload**, using the file's last-modified time in S3, so the 1 hour starts when the upload finishes.
- **Smoke test:** `python3 scripts/smoke_test.py` runs the whole flow against the deployed Lambda with no browser.
