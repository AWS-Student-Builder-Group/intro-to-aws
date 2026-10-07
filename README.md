# AWS Demo App: DIY Dropbox

### A simple demonstration for how AWS works, taking advantage of AWS Lambda and S3 to demonstrate compute and storage capabilities of AWS

Upload a file, get a link that works for an hour, and share it. The file goes straight from the browser to a private S3 bucket. A Lambda function hands out the signed, expiring links.

## Requirements & Installation

**Always:**
- An AWS account (see [`instructions.md`](instructions.md) for sign-up steps, and the Cost section below)
- Python 3 (`python3 --version`)
- This repository (clone or download it)

**Only for Part Two (maintainer):**
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), then `aws configure` (or `aws configure sso`)
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Credentials that can create CloudFormation, S3, Lambda, IAM and CloudFront resources. Don't create access keys for the root user. Use an IAM user or SSO.

No `pip install` is needed. The Lambda only uses `boto3`, which AWS provides.

## Demo Instructions

### Part One: Console + local page

1. Follow the step-by-step guide in [`instructions.md`](instructions.md). It walks through creating the bucket, CORS, lifecycle rule, Lambda, IAM policy and Function URL in the console.
2. Put your Function URL in `frontend/config.js`:
   ```js
   window.APP_CONFIG = {
     FUNCTION_URL: "https://<ID>.lambda-url.<REGION>.on.aws/",
   };
   ```
3. Run the page:
   ```bash
   python3 scripts/serve.py
   ```
   It opens `http://localhost:8000`. Options: `--port <n>`, `--no-browser`. Keep port 8000 unless you also change the allowed origin in the bucket CORS and Function URL CORS.
4. Check the backend without a browser: `python3 scripts/smoke_test.py`

### Part Two: Deploy everything from code (maintainer)

Workshop participants use Part One. This path is for keeping a fully hosted copy of the app, for example as a live backup or a finished example to show.

```bash
scripts/deploy.sh
```

This builds and deploys [`infra/template.yaml`](infra/template.yaml) with SAM, uploads the web page, and prints the address to open. The first run takes several minutes because CloudFront is slow to create.

Optional settings (environment variables): `STACK_NAME` (default `quickdrop`), `AWS_REGION` (default: your AWS CLI region), `LOCAL_ORIGIN` (default `http://localhost:8000`).

Afterwards, `python3 scripts/smoke_test.py <backend URL>` checks the backend end to end (`deploy.sh` prints the exact command).

What gets created:

| Resource | Purpose |
|---|---|
| Upload bucket (S3) | Private. Stores uploads, with CORS and a delete-after-1-day rule |
| Lambda + Function URL | Signs the links and serves the share link |
| IAM role | Created for the Lambda, limited to the upload bucket |
| Site bucket (S3) | Private. Holds the web page, readable only by CloudFront |
| CloudFront distribution | Serves the web page over HTTPS |

The deployed page gets its own generated `config.js`, so `frontend/config.js` in the repo (the one you edit by hand for Part One) is never touched.

**Remove everything:**
```bash
scripts/teardown.sh
```
It asks for confirmation, empties both buckets, and deletes the stack. Removing CloudFront takes a few minutes.

### Mixing the two
After `scripts/deploy.sh`, you can also run the page on your laptop against the deployed backend. Put the printed backend URL in `frontend/config.js` and run `python3 scripts/serve.py`. The deployed backend allows `http://localhost:8000` by default.

## Project layout

```
backend/    The Lambda (app.py is the part worth reading; utils.py is plumbing)
frontend/   The web page (aws.js talks to AWS; app.js is the UI)
infra/      template.yaml: everything in Part Two as code
scripts/    serve.py (run the page), smoke_test.py (check the backend),
            deploy.sh and teardown.sh (Part Two)
assets/     Screenshot used in this README
instructions.md  Step-by-step guide for both parts (console walkthrough, then CLI deploy)
```

More detail: [`backend/README.md`](backend/README.md) and [`frontend/README.md`](frontend/README.md).

## Cost

Designed to cost nothing at demo scale. Lambda has an always-free allowance, S3 has a free allowance, and uploads delete themselves after a day. CloudFront has a generous always-free tier too. New AWS accounts start on the Free plan, which doesn't charge but closes after 6 months or when its credits run out. Run the cleanup (the Clean up section of Part One or Part Two in `instructions.md`, or `scripts/teardown.sh`) when you're finished.
