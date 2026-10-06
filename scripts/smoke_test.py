#!/usr/bin/env python3
"""End-to-end check of the deployed backend with no browser or copy/paste involved.

Asks the Lambda for links, uploads a small file to S3, then downloads it via the
download link and compares the bytes. Prints S3's error body if anything fails.

    python3 scripts/smoke_test.py [FUNCTION_URL]

FUNCTION_URL defaults to the value in frontend/config.js. Uses only the standard library.
"""
import json
import re
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "frontend" / "config.js"
CONTENT = b"hello from the smoke test\n"
FILENAME = "smoke-test.txt"


def function_url():
    if len(sys.argv) > 1:
        return sys.argv[1]
    match = re.search(r'FUNCTION_URL:\s*"([^"]+)"', CONFIG.read_text())
    if not match or "REPLACE-ME" in match.group(1):
        sys.exit("Pass the Function URL as an argument or set it in frontend/config.js.")
    return match.group(1)


def call(request):
    """Return (status, body bytes) without raising on HTTP errors."""
    try:
        with urllib.request.urlopen(request) as res:
            return res.status, res.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def multipart(fields, filename, content_type, data):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode()
        + data
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def main():
    url = function_url()

    print("1. Asking the Lambda for links...")
    request = urllib.request.Request(
        url,
        data=json.dumps(
            {"filename": FILENAME, "size": len(CONTENT), "contentType": "text/plain"}
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    status, body = call(request)
    if status != 200:
        sys.exit(f"   FAILED ({status}): {body.decode(errors='replace')}")
    links = json.loads(body)
    kind = "short share link" if "?k=" in links["downloadUrl"] else "raw presigned URL"
    print(f"   ok. download link is a {kind}: {links['downloadUrl'][:90]}")

    print("2. Uploading to S3...")
    payload, content_type = multipart(links["fields"], FILENAME, "text/plain", CONTENT)
    request = urllib.request.Request(
        links["uploadUrl"], data=payload, headers={"Content-Type": content_type}, method="POST"
    )
    status, body = call(request)
    if status not in (200, 201, 204):
        sys.exit(f"   FAILED ({status}): {body.decode(errors='replace')}")
    print(f"   ok ({status})")

    print("3. Downloading via the download link (following the redirect to S3)...")
    status, body = call(urllib.request.Request(links["downloadUrl"]))
    if status != 200:
        sys.exit(f"   FAILED ({status}): {body.decode(errors='replace')[:600]}")
    if body != CONTENT:
        sys.exit("   FAILED: downloaded bytes differ from what was uploaded.")
    print("   ok. Downloaded bytes match.")
    print("\nAll good: the backend works end to end.")


if __name__ == "__main__":
    main()
