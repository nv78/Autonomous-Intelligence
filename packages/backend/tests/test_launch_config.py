"""Production launch: S3 twin storage, config enforcement, key rotation."""
from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from coworker import blobstore, config, twin
from coworker.store import Store

BUCKET = "test-twin-bucket"


@pytest.fixture
def s3(monkeypatch):
    for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.setenv(key, "testing")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("TWIN_S3_BUCKET", BUCKET)
    monkeypatch.setenv("TWIN_S3_SSE", "AES256")
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        client.put_bucket_versioning(Bucket=BUCKET, VersioningConfiguration={"Status": "Enabled"})
        yield client


def test_blobstore_local_roundtrip(tmp_path, monkeypatch):
    monkeypatch.delenv("TWIN_S3_BUCKET", raising=False)
    monkeypatch.setenv("TWIN_FOLDER", str(tmp_path))
    ref = blobstore.put(7, "a.webm", b"hello", "video/webm")
    assert ref.startswith(str(tmp_path)) and blobstore.exists(ref)
    assert blobstore.get(ref) == b"hello"
    blobstore.delete(ref)
    blobstore.delete(ref)  # deleting twice is harmless
    assert not blobstore.exists(ref)
    blobstore.put(7, "b.webm", b"x", "video/webm")
    assert blobstore.delete_user(7) == 1
    assert not (tmp_path / "7").exists()


def test_blobstore_s3_encrypted_and_versions_purged(s3):
    ref = blobstore.put(3, "sample.webm", b"voice", "audio/webm")
    assert ref == f"s3://{BUCKET}/twin/3/sample.webm"
    head = s3.head_object(Bucket=BUCKET, Key="twin/3/sample.webm")
    assert head["ServerSideEncryption"] == "AES256" and head["ContentType"] == "audio/webm"
    assert blobstore.exists(ref) and blobstore.get(ref) == b"voice"
    blobstore.put(3, "sample.webm", b"voice v2", "audio/webm")  # second version
    blobstore.delete(ref)  # leaves a delete marker plus old versions
    assert not blobstore.exists(ref)
    blobstore.put(4, "other.webm", b"keep", "audio/webm")
    assert blobstore.delete_user(3) == 3
    left = s3.list_object_versions(Bucket=BUCKET)
    keys = {v["Key"] for v in left.get("Versions", []) + left.get("DeleteMarkers", [])}
    assert keys == {"twin/4/other.webm"}


def test_twin_lifecycle_on_s3(s3, tmp_path):
    store = Store(f"sqlite:///{tmp_path}/twin.db")
    store.create_coworker(1, "Natan Vidra", "natan@example.com", mode="demo")
    asset = twin.save_asset(store, 1, "voice_sample", "me.webm", "audio/webm", b"audio")
    assert asset["path"].startswith(f"s3://{BUCKET}/twin/1/")
    ch = twin.challenge(store, 1, "Natan Vidra")
    spoken = " ".join(ch["code"])
    result = twin.verify(store, 1, ch["id"], f"I, Natan Vidra, authorize Ourogen. My code is {spoken}.",
                         ("consent.webm", "video/webm", b"consent"))
    assert result["verified"]
    assert twin.delete_asset(store, 1, asset["id"]) and not blobstore.exists(asset["path"])
    assert not twin.delete_asset(store, 1, asset["id"])
    twin.save_asset(store, 1, "photo", "me.png", "image/png", b"png")
    revoked = twin.revoke(store, 1)
    assert revoked["deletedFiles"] == 2
    assert "Versions" not in s3.list_object_versions(Bucket=BUCKET, Prefix="twin/1/")


def test_asset_route_serves_from_blobstore(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.delenv("TWIN_S3_BUCKET", raising=False)
    monkeypatch.setenv("TWIN_FOLDER", str(tmp_path / "twin"))
    from unittest.mock import patch
    with patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@example.com")):
        assert client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers).status_code == 201
        up = client.post("/api/coworker/twin/assets", headers=auth_headers, content_type="multipart/form-data",
                         data={"kind": "photo", "file": (__import__("io").BytesIO(b"PNG"), "me.png", "image/png")})
        assert up.status_code in (200, 201), up.get_json()
        aid = up.get_json()["asset"]["id"]
        resp = client.get(f"/api/coworker/twin/assets/{aid}/file", headers=auth_headers)
        assert resp.status_code == 200 and resp.data == b"PNG"
        assert resp.headers["Cache-Control"] == "private, no-store"
        assert client.get("/api/coworker/twin/assets/9999/file", headers=auth_headers).status_code == 404


SAFE = {
    "APP_ENV": "production",
    "JWT_SECRET_KEY": "x" * 40,
    "PROVIDER_KEY_ENCRYPTION_KEY": "k",
    "BACKEND_URL": "https://chat.ourogen.ai",
    "FRONTEND_URL": "https://chat.ourogen.ai",
    "TWIN_S3_BUCKET": "b",
    "ANTHROPIC_API_KEY": "sk",
}


def test_config_check_safe_and_unsafe():
    assert config.check(SAFE) == ([], [])
    errors, warnings = config.check({"APP_ENV": "production", "JWT_SECRET_KEY": "dev-secret-change-me",
                                     "COWORKER_DB_URL": "sqlite:///x.db", "GOOGLE_CLIENT_ID": "g",
                                     "BACKEND_URL": "http://x"})
    assert len(errors) == 3
    assert any("GOOGLE_COWORKER_REDIRECT_URI" in w for w in warnings)
    assert any("TWIN_S3_BUCKET" in w for w in warnings)
    assert any("offline planner" in w for w in warnings)
    _, warnings = config.check({**SAFE, "MICROSOFT_CLIENT_ID": "m", "SLACK_CLIENT_ID": "s"})
    assert any("MICROSOFT_REDIRECT_URI" in w for w in warnings) and any("SLACK_SIGNING_SECRET" in w for w in warnings)
    assert config.check({**SAFE, "MICROSOFT_CLIENT_ID": "m", "MICROSOFT_REDIRECT_URI": "https://x/cb",
                         "SLACK_CLIENT_ID": "s", "SLACK_SIGNING_SECRET": "z"}) == ([], [])


def test_config_enforce(caplog):
    config.enforce({"APP_ENV": "local"})  # only production is checked
    config.enforce(SAFE)
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        config.enforce({**SAFE, "JWT_SECRET_KEY": "short"})
    config.enforce({**SAFE, "JWT_SECRET_KEY": "short", "ALLOW_UNSAFE_CONFIG": "1"})
    assert "starting anyway" in caplog.text


def test_create_app_refuses_unsafe_production(monkeypatch):
    from app import create_app
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "dev-secret-change-me")
    monkeypatch.delenv("ALLOW_UNSAFE_CONFIG", raising=False)
    with pytest.raises(RuntimeError, match="Unsafe production configuration"):
        create_app({"DB_HOST": "localhost"})


def test_provider_keys_decrypt_after_setting_dedicated_key(monkeypatch):
    from cryptography.fernet import Fernet

    from services import provider_keys
    monkeypatch.setenv("JWT_SECRET_KEY", "jwt-secret-for-test")
    monkeypatch.delenv("PROVIDER_KEY_ENCRYPTION_KEY", raising=False)
    old_token = provider_keys._fernet().encrypt(b"sk-old")
    monkeypatch.setenv("PROVIDER_KEY_ENCRYPTION_KEY", Fernet.generate_key().decode())
    f = provider_keys._fernet()
    assert f.decrypt(old_token) == b"sk-old"
    new_token = f.encrypt(b"sk-new")
    monkeypatch.delenv("PROVIDER_KEY_ENCRYPTION_KEY")
    with pytest.raises(Exception):
        provider_keys._fernet().decrypt(new_token)  # new values use the dedicated key


def test_config_gmail_push_needs_pinned_service_account():
    errors, _ = config.check({**SAFE, "GMAIL_PUSH_AUDIENCE": "https://x/push"})
    assert any("GMAIL_PUSH_SERVICE_ACCOUNT" in e for e in errors)
    assert config.check({**SAFE, "GMAIL_PUSH_AUDIENCE": "https://x/push", "GMAIL_PUSH_SERVICE_ACCOUNT": "p@x.iam"}) == ([], [])
