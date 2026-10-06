"""Base backend project"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from utils import (
    REDIRECT_EXPIRES_IN,
    BadRequest,
    get_download_key,
    get_expires_in,
    get_max_bytes,
    get_method,
    parse_request,
    redirect,
    response,
    safe_filename,
    share_link,
)

# SigV4 + regional endpoint avoids redirects that would break browser uploads.
s3 = boto3.client(
    "s3",
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)


def lambda_handler(event, context):
    bucket = os.environ.get("BUCKET_NAME")
    if not bucket:
        return response(500, {"error": "Server misconfigured: BUCKET_NAME is not set."})

    method = get_method(event)
    if method == "POST":
        return create_links(event, bucket)  # the web app: "I want to upload a file"
    if method == "GET":
        return open_share_link(event, bucket)  # a friend: "I opened the link I was sent"
    return response(405, {"error": "Use GET or POST."})


def presigned_download(bucket, key, expires_in):
    filename = key.split("/", 1)[1]
    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": bucket,
            "Key": key,
            "ResponseContentDisposition": f'attachment; filename="{filename}"',
        },
        ExpiresIn=expires_in,
    )


def create_links(event, bucket):
    expires_in = get_expires_in()
    max_bytes = get_max_bytes()

    try:
        filename, size, content_type = parse_request(event, max_bytes)
    except BadRequest as err:
        return response(400, {"error": str(err)})

    # Unguessable prefix, readable name.
    key = f"{uuid.uuid4().hex}/{safe_filename(filename)}"

    # Upload link: a presigned POST, so S3 itself enforces the size limit.
    post = s3.generate_presigned_post(
        Bucket=bucket,
        Key=key,
        Fields={"Content-Type": content_type},
        Conditions=[
            {"Content-Type": content_type},
            ["content-length-range", 1, max_bytes],
        ],
        ExpiresIn=expires_in,
    )

    # Download link to share. Normally a short link back to this Lambda (see open_share_link).
    # A raw presigned URL is long and full of characters that copy/paste can corrupt, so we
    # only fall back to it when there is no domain to link to (e.g. the console Test tab).
    download_url = share_link(event, key) or presigned_download(bucket, key, expires_in)

    return response(
        200,
        {
            "uploadUrl": post["url"],
            "fields": post["fields"],
            "downloadUrl": download_url,
            "expiresIn": expires_in,
        },
    )


def open_share_link(event, bucket):
    expires_in = get_expires_in()

    try:
        key = get_download_key(event)
    except BadRequest as err:
        return response(400, {"error": str(err)})

    try:
        obj = s3.head_object(Bucket=bucket, Key=key)
    except ClientError:
        # S3 answers 404 or 403 for a missing key, depending on bucket permissions.
        return response(404, {"error": "File not found."})

    # The link is good for EXPIRES_IN seconds after the upload finished.
    if datetime.now(timezone.utc) - obj["LastModified"] > timedelta(seconds=expires_in):
        return response(410, {"error": "This link has expired."})

    # Hand the visitor a freshly signed S3 link that only lives for a minute.
    return redirect(presigned_download(bucket, key, REDIRECT_EXPIRES_IN))
