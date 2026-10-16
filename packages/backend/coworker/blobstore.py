"""Private file storage for twin samples and consent evidence.

Production uses S3 (``TWIN_S3_BUCKET``): server-side encrypted, private,
never public. Local development uses a folder on disk (``TWIN_FOLDER``).

Stored files are referenced by an opaque ``ref`` string kept in the
database: ``s3://bucket/key`` or an absolute local path.
"""
from __future__ import annotations

import os
import shutil
from typing import Any


def _bucket() -> str:
    return os.environ.get("TWIN_S3_BUCKET", "")


def _s3() -> Any:
    import boto3

    return boto3.client("s3", region_name=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1")


def _local_root() -> str:
    return os.environ.get("TWIN_FOLDER", "/tmp/ourogen_twin")


def put(user_id: int, name: str, data: bytes, mime: str) -> str:
    key = f"twin/{int(user_id)}/{name}"
    bucket = _bucket()
    if bucket:
        _s3().put_object(Bucket=bucket, Key=key, Body=data, ContentType=mime or "application/octet-stream",
                         ServerSideEncryption=os.environ.get("TWIN_S3_SSE", "aws:kms"))
        return f"s3://{bucket}/{key}"
    path = os.path.join(_local_root(), str(int(user_id)), name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def _split(ref: str) -> tuple[str, str]:
    bucket, _, key = ref[len("s3://"):].partition("/")
    return bucket, key


def get(ref: str) -> bytes:
    if ref.startswith("s3://"):
        bucket, key = _split(ref)
        body: bytes = _s3().get_object(Bucket=bucket, Key=key)["Body"].read()
        return body
    with open(ref, "rb") as fh:
        return fh.read()


def exists(ref: str) -> bool:
    if ref.startswith("s3://"):
        bucket, key = _split(ref)
        try:
            _s3().head_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            return False
    return os.path.exists(ref)


def delete(ref: str) -> None:
    if ref.startswith("s3://"):
        bucket, key = _split(ref)
        _s3().delete_object(Bucket=bucket, Key=key)
        return
    try:
        os.remove(ref)
    except OSError:
        pass


def delete_user(user_id: int) -> int:
    """Delete every stored object for a user (including object versions on S3)."""
    bucket = _bucket()
    deleted = 0
    if bucket:
        s3 = _s3()
        prefix = f"twin/{int(user_id)}/"
        paginator = s3.get_paginator("list_object_versions")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            objects = [{"Key": v["Key"], "VersionId": v["VersionId"]}
                       for v in (page.get("Versions") or []) + (page.get("DeleteMarkers") or [])]
            if objects:
                s3.delete_objects(Bucket=bucket, Delete={"Objects": objects})
                deleted += len(objects)
    folder = os.path.join(_local_root(), str(int(user_id)))
    if os.path.isdir(folder):
        deleted += sum(len(files) for _, _, files in os.walk(folder))
        shutil.rmtree(folder, ignore_errors=True)
    return deleted
