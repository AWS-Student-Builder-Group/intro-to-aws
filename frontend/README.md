# AWS Demo Frontend

Created using Claude Code

A static page (plain HTML/CSS/JS, no build step) for the Quick Drop demo. You pick a file, it uploads straight to S3, and it shows a share link that expires after a short time.

## Files

| File | Purpose |
|---|---|
| `index.html` | Page markup: drop zone, progress bar, status line, result box |
| `aws.js` | Everything that talks to AWS: asks the Lambda for presigned URLs, uploads to S3. No DOM code |
| `app.js` | UI only: file picking, drag and drop, progress bar, status, share link and countdown. Imports `aws.js` |
| `style.css` | Styling, using the AWS SBG palette |
| `config.js` | The one setting you must edit: the Lambda Function URL |

## Configuration

`config.js` is the only setting:

```js
window.APP_CONFIG = {
  FUNCTION_URL: "https://<id>.lambda-url.<region>.on.aws/",
};
```

The page makes cross-origin requests to the Function URL and to S3, so both CORS configs must list the exact origin the page is served from (for example `http://localhost:8000`).

## How it works

```
Browser                    Lambda (Function URL)              S3
  | POST {filename,size,type} |                                |
  |-------------------------->| create key + presigned URLs    |
  |<--------------------------| {uploadUrl, downloadUrl, ...}  |
  | upload file directly (PUT or POST) ----------------------->|
  | show downloadUrl + countdown                               |
```

The file never passes through the Lambda. The Lambda only signs URLs, and the signature carries the expiry.

## Lambda contract

**Request:** `POST` to `FUNCTION_URL` with a JSON body:

```json
{ "filename": "photo.png", "size": 12345, "contentType": "image/png" }
```

**Success response (200):**

```json
{
  "uploadUrl": "https://bucket.s3.amazonaws.com/...",
  "downloadUrl": "https://<id>.lambda-url.<region>.on.aws/?k=<key>",
  "expiresIn": 3600,
  "fields": { "key": "...", "policy": "...", "x-amz-signature": "..." }
}
```

- `downloadUrl` is the link to share. It is a short link back to the Lambda that redirects to S3, so it contains only URL-safe characters and survives copy and paste. (A raw presigned S3 URL is long and contains `+`, `/` and `=`, which some browsers and extensions rewrite on copy, breaking the link.)
- `expiresIn` is in seconds and drives the countdown in the page.
- `fields` is optional. If present, `uploadUrl` is a **presigned POST**: the page sends a multipart form with these fields first and the file last, and S3 can enforce a size limit. If absent, `uploadUrl` is a **presigned PUT** and the page sends the file as the request body with its `Content-Type`.

**Error response (non-2xx):** `{ "error": "message" }`. The message is shown in the page.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| "Set FUNCTION_URL in frontend/config.js first." | `config.js` still has the `REPLACE-ME` placeholder |
| Browser console shows a CORS error on the first request | The Function URL CORS config doesn't allow `http://localhost:8000` (or doesn't allow the `Content-Type` header and `POST`) |
| "Upload failed. Check bucket CORS..." | The S3 bucket CORS config doesn't allow `PUT`/`POST` from your origin |
| "S3 rejected the upload (403)" | Presigned URL expired, the Lambda role lacks `s3:PutObject`, or (PUT) the `Content-Type` sent differs from the one that was signed |
| Link works, then stops | Expected. The presigned URL has expired |
| Edited `config.js` but nothing changed | Hard refresh. `serve.py` disables caching, but another server might not |

## Customising

- **Colours:** the palette is defined as CSS variables at the top of `style.css`.
- **Lambda behaviour** (expiry, size limit, key naming) lives in the backend, not here. The page just follows what the Lambda returns.