"""Helpers for app.py: request parsing, validation and config. Nothing AWS-specific lives here."""
import base64
import json
import os
import re
from urllib.parse import quote

MAX_EXPIRES_IN = 3600
DEFAULT_MAX_BYTES = 100 * 1024 * 1024
REDIRECT_EXPIRES_IN = 60  # the signed S3 link behind a share link only needs to live this long

# Keys are always "<32 hex chars>/<safe filename>", see create_key in app.py.
KEY_PATTERN = re.compile(r"^[0-9a-f]{32}/[A-Za-z0-9._-]{1,100}$")


class BadRequest(Exception):
    pass


def response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def redirect(url):
    return {
        "statusCode": 302,
        "headers": {"Location": url, "Cache-Control": "no-store"},
        "body": "",
    }


def share_link(event, key):
    """Short link to this same Lambda, e.g. https://<id>.lambda-url...on.aws/?k=<key>.

    It uses only URL-safe characters, so it survives copy/paste and chat apps.
    Returns None when there is no domain (e.g. the console Test tab).
    """
    domain = event.get("requestContext", {}).get("domainName")
    return f"https://{domain}/?k={quote(key, safe='/')}" if domain else None


def get_download_key(event):
    """Read and validate the ?k= parameter. Raises BadRequest."""
    key = (event.get("queryStringParameters") or {}).get("k", "")
    if not KEY_PATTERN.match(key):
        raise BadRequest("This link is not valid.")
    return key


def int_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def get_expires_in():
    """Link lifetime in seconds: EXPIRES_IN, capped at one hour."""
    return max(1, min(int_env("EXPIRES_IN", MAX_EXPIRES_IN), MAX_EXPIRES_IN))


def get_max_bytes():
    return int_env("MAX_BYTES", DEFAULT_MAX_BYTES)


def get_method(event):
    # Console "Test" events have no HTTP context, so default to POST.
    return event.get("requestContext", {}).get("http", {}).get("method", "POST")


def safe_filename(name):
    """Keep only characters that are safe in an S3 key and a header value."""
    name = os.path.basename(str(name))
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name[:100] or "file"


def _parse_body(event):
    raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise BadRequest("Request body must be JSON.")
    if not isinstance(data, dict):
        raise BadRequest("Request body must be a JSON object.")
    return data


def parse_request(event, max_bytes):
    """Validate the request and return (filename, size, content_type). Raises BadRequest."""
    data = _parse_body(event)

    filename = data.get("filename")
    if not isinstance(filename, str) or not filename.strip():
        raise BadRequest("filename is required.")

    size = data.get("size")
    # bool is an int subclass in Python, so exclude it explicitly.
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise BadRequest("size must be a positive integer (bytes).")
    if size > max_bytes:
        raise BadRequest(f"File too large. Limit is {max_bytes // (1024 * 1024)} MB.")

    content_type = data.get("contentType")
    if not isinstance(content_type, str) or not content_type:
        content_type = "application/octet-stream"

    return filename, size, content_type
