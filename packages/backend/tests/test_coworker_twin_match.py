"""Voice match before cloning, speaking style, vendor checks."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from coworker import admin, twin, vendor_check, voiceprint
from coworker.store import Store
from tests.audio_synth import voice

pytestmark = pytest.mark.skipif(not voiceprint.available(), reason="ffmpeg not installed")

ME_1, ME_2, ME_3 = voice(115, 1.0, 1), voice(118, 1.0, 2), voice(112, 1.0, 5)
SOMEONE_ELSE = voice(210, 1.18, 3)


def test_compare_same_and_different_speakers():
    same = voiceprint.compare(ME_1, ME_2)
    assert same["verdict"] == "match" and same["backend"] == "local"
    other = voiceprint.compare(ME_1, SOMEONE_ELSE)
    assert other["verdict"] == "mismatch" and other["pitchRatio"] > 1.45


def test_compare_handles_bad_and_short_audio():
    assert voiceprint.compare(b"not audio", ME_1)["verdict"] == "inconclusive"
    short = voice(115, 1.0, 9, seconds=1.0)
    r = voiceprint.compare(short, ME_1)
    assert r["verdict"] == "inconclusive" and "seconds" in r["reason"]
    with patch("coworker.voiceprint.available", return_value=False):
        assert voiceprint.compare(ME_1, ME_2)["verdict"] == "unavailable"
    assert voiceprint.overall([]) == "inconclusive"
    assert voiceprint.overall([{"verdict": "match"}, {"verdict": "inconclusive"}]) == "inconclusive"


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setenv("TWIN_FOLDER", str(tmp_path / "twin"))
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el")
    store = Store(f"sqlite:///{tmp_path}/twin.db")
    store.create_coworker(1, "Natan Vidra", "natan@anote.ai", mode="demo")
    return store


def _consent(store: Store, audio: bytes) -> None:
    ch = twin.challenge(store, 1, "Natan Vidra")
    spoken = " ".join(ch["code"])
    assert twin.verify(store, 1, ch["id"], f"I, Natan Vidra, authorize Ourogen. My code is {spoken}.",
                       ("consent.wav", "audio/wav", audio))["verified"]


def test_cloning_requires_matching_voice(s):
    twin.save_asset(s, 1, "voice_sample", "me.wav", "audio/wav", ME_2)
    impostor = twin.save_asset(s, 1, "voice_sample", "keynote.wav", "audio/wav", SOMEONE_ELSE)
    _consent(s, ME_1)
    with patch("coworker.voice.clone", return_value="v1") as clone, pytest.raises(PermissionError, match="keynote.wav"):
        twin.create_voice(s, 1)
    clone.assert_not_called()
    assert twin.status(s, 1)["voiceMatch"]["status"] == "mismatch"
    twin.delete_asset(s, 1, impostor["id"])
    twin.save_asset(s, 1, "video_sample", "talk.wav", "audio/wav", ME_3)
    with patch("coworker.voice.clone", return_value="v1"):
        assert twin.create_voice(s, 1) == "v1"
    assert twin.voice_match(s, 1)["status"] == "match"


def test_inconclusive_blocks_until_manual_review(s):
    twin.save_asset(s, 1, "voice_sample", "me.wav", "audio/wav", ME_2)
    _consent(s, voice(115, 1.0, 7, seconds=1.0))  # too short to judge
    with pytest.raises(PermissionError, match="somewhere quiet"):
        twin.create_voice(s, 1)
    with pytest.raises(ValueError):
        twin.approve_voice_match(Store(f"sqlite:///{s._sqlite_path}2"), 1, "x")
    twin.approve_voice_match(s, 1, "reviewer@ourogen.ai")
    with patch("coworker.voice.clone", return_value="v9"):
        assert twin.create_voice(s, 1) == "v9"
    assert twin.voice_match(s, 1)["samples"][-1]["manualReview"] is True
    with patch("coworker.voice.delete", return_value=True):
        twin.revoke(s, 1)
    settings = s.get_coworker(1)["settings"]
    assert "voice_match_override" not in settings and "voice_match" not in settings


def test_voice_match_needs_consent_and_samples(s):
    assert twin.voice_match(s, 1)["status"] == "inconclusive"


def test_speaking_style(s):
    text = ("so basically we help teams um find answers in their documents and you know the citations matter "
            "so basically you can trust it and um the citations matter a lot for analysts so basically yes")
    twin.add_speech_sample(s, 1, 7, text, 12.0)
    twin.add_speech_sample(s, 1, 8, "", 3.0)  # ignored
    style = twin.speaking_style(s, 1)
    assert style["wpm"] > 100 and "citations matter" in style["phrases"] and style["fillersPer100Words"]
    prompt = twin.style_prompt(s, 1)
    assert "words per minute" in prompt and "citations matter" in prompt
    twin.add_speech_sample(s, 1, 7, "short", 1.0)  # replaces asset 7
    assert twin.speaking_style(s, 1) is None
    assert twin.style_prompt(s, 1) == ""


def test_upload_route_keeps_transcript(client, auth_headers, tmp_path, monkeypatch):
    import io

    monkeypatch.setenv("TWIN_FOLDER", str(tmp_path / "t"))
    with patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@anote.ai")):
        assert client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers).status_code == 201
        words = " ".join(["we help analysts find answers fast"] * 6)
        r = client.post("/api/coworker/twin/assets", headers=auth_headers, content_type="multipart/form-data",
                        data={"kind": "voice_sample", "transcript": words, "seconds": "15",
                              "file": (io.BytesIO(ME_1), "s.wav", "audio/wav")})
        assert r.status_code == 201
        client.post("/api/coworker/twin/assets", headers=auth_headers, content_type="multipart/form-data",
                    data={"kind": "voice_sample", "seconds": "abc", "file": (io.BytesIO(ME_2), "s2.wav", "audio/wav")})
        st = client.get("/api/coworker/twin", headers=auth_headers).get_json()
        assert st["speakingStyle"]["wpm"] == round(36 / 0.25)
        assert client.post("/api/coworker/twin/voice-match", headers=auth_headers).get_json()["status"] == "inconclusive"


# -- vendor checks -------------------------------------------------------------

def _resp(status: int, body: dict | None = None) -> MagicMock:
    r = MagicMock(status_code=status, content=b"{}" if body is not None else b"", text="err")
    r.json.return_value = body or {}
    return r


def test_vendor_checks(monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY", "RECALL_API_KEY", "TAVUS_API_KEY", "TAVUS_REPLICA_ID",
              "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET", "SMTP_URL",
              "TWIN_S3_BUCKET", "REDIS_URL", "RATE_LIMIT_REDIS_URL", "APP_ENV", "MICROSOFT_CLIENT_ID",
              "MICROSOFT_CLIENT_SECRET", "SLACK_SIGNING_SECRET", "BACKEND_URL"):
        monkeypatch.delenv(k, raising=False)
    assert {r["status"] for r in vendor_check.run_all() if r["name"] != "Voice match"} == {"skipped"}

    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.setenv("RECALL_API_KEY", "k")
    monkeypatch.setenv("TAVUS_API_KEY", "k")
    assert vendor_check.check_tavus()["status"] == "fail"
    monkeypatch.setenv("TAVUS_REPLICA_ID", "r1")
    with patch("requests.get", side_effect=[
        _resp(200, {"id": "claude-opus-5-5"}),
        _resp(200, {"subscription": {"tier": "creator", "character_count": 10, "character_limit": 100,
                                     "can_use_instant_voice_cloning": True}}),
        _resp(200, {"count": 3}),
        _resp(200, {"replica_name": "Natan", "status": "completed"}),
    ]):
        a, e, r, t = (vendor_check.check_anthropic(), vendor_check.check_elevenlabs(), vendor_check.check_recall(),
                      vendor_check.check_tavus())
    assert a["status"] == e["status"] == r["status"] == t["status"] == "ok"
    assert "instant cloning allowed" in e["detail"] and "3 bots" in r["detail"] and "Natan" in t["detail"]
    with patch("requests.get", return_value=_resp(401, {})):
        assert "rejected" in vendor_check.check_elevenlabs()["detail"]
    with patch("requests.get", return_value=_resp(500, {})):
        assert vendor_check.check_recall()["status"] == "fail"
    import requests

    with patch("requests.get", side_effect=requests.ConnectionError()):
        assert "network" in vendor_check.check_anthropic()["detail"]

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "g")
    assert vendor_check.check_google()["status"] == "fail"
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "s")
    monkeypatch.setenv("APP_ENV", "production")
    assert vendor_check.check_google()["status"] == "fail"
    monkeypatch.setenv("GOOGLE_COWORKER_REDIRECT_URI", "https://x/cb")
    assert vendor_check.check_google()["status"] == "ok"
    monkeypatch.setenv("SLACK_CLIENT_ID", "x")
    assert vendor_check.check_slack()["status"] == "fail"
    monkeypatch.setenv("SLACK_CLIENT_SECRET", "y")
    assert vendor_check.check_slack()["status"] == "ok"
    assert "polling" in vendor_check.check_slack()["detail"]
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "z")
    assert "real-time" in vendor_check.check_slack()["detail"]

    monkeypatch.delenv("MICROSOFT_CLIENT_ID", raising=False)
    monkeypatch.delenv("MICROSOFT_CLIENT_SECRET", raising=False)
    assert vendor_check.check_microsoft()["status"] == "skipped"
    monkeypatch.setenv("MICROSOFT_CLIENT_ID", "m")
    assert vendor_check.check_microsoft()["status"] == "fail"
    monkeypatch.setenv("MICROSOFT_CLIENT_SECRET", "ms")
    monkeypatch.setenv("MICROSOFT_REDIRECT_URI", "http://localhost:5000/cb")
    assert vendor_check.check_microsoft()["status"] == "fail"  # production needs https
    monkeypatch.setenv("MICROSOFT_REDIRECT_URI", "https://chat.ourogen.ai/cb")
    assert vendor_check.check_microsoft()["status"] == "ok"

    monkeypatch.setenv("BACKEND_URL", "http://localhost:5000")
    assert vendor_check.check_public_url()["status"] == "fail"
    monkeypatch.setenv("BACKEND_URL", "http://chat.ourogen.ai")
    assert vendor_check.check_public_url()["status"] == "fail"
    monkeypatch.setenv("BACKEND_URL", "https://chat.ourogen.ai")
    assert vendor_check.check_public_url()["status"] == "ok"
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("BACKEND_URL", "http://localhost:5000")
    assert vendor_check.check_public_url()["status"] == "skipped"
    monkeypatch.setenv("APP_ENV", "production")

    monkeypatch.setenv("SMTP_URL", "smtp://u:p@mail.test:2525")
    with patch("smtplib.SMTP"):
        assert vendor_check.check_smtp()["status"] == "ok"
    with patch("smtplib.SMTP", side_effect=OSError("refused")):
        assert vendor_check.check_smtp()["status"] == "fail"
    monkeypatch.setenv("TWIN_S3_BUCKET", "b")
    with patch("coworker.blobstore._s3") as s3:
        assert vendor_check.check_s3()["status"] == "ok"
        s3.return_value.head_bucket.side_effect = RuntimeError("403")
        assert vendor_check.check_s3()["status"] == "fail"
    monkeypatch.setenv("REDIS_URL", "redis://x")
    with patch("redis.Redis.from_url"):
        assert vendor_check.check_redis()["status"] == "ok"
    with patch("redis.Redis.from_url", side_effect=ConnectionError("down")):
        assert vendor_check.check_redis()["status"] == "fail"
    with patch("coworker.voiceprint.available", return_value=False):
        assert vendor_check.check_voiceprint()["status"] == "fail"


def test_admin_vendor_route_and_hubspot_revoke(client, auth_headers, monkeypatch, tmp_path):
    with patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@anote.ai")):
        client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers)
        monkeypatch.setenv("PILOT_ADMIN_EMAILS", "someone@else.com")
        assert client.get("/api/coworker/admin/vendors", headers=auth_headers).status_code == 403
        from coworker import identity
        from coworker.store import get_store

        with client.application.app_context():
            identity.record(get_store(), 1, "google", "sub-natan", "natan@anote.ai")
        monkeypatch.setenv("PILOT_ADMIN_EMAILS", "natan@anote.ai")
        with patch("coworker.vendor_check.run_all", return_value=[{"name": "x", "status": "ok", "detail": ""}]):
            assert client.get("/api/coworker/admin/vendors", headers=auth_headers).get_json()["vendors"][0]["name"] == "x"
    from coworker.connectors.base import encrypt_token

    store = Store(f"sqlite:///{tmp_path}/a.db")
    store.create_coworker(1, "N", "n@x.com")
    store.upsert_connection(1, "hubspot", status="connected", token_enc=encrypt_token({"kind": "oauth", "refresh_token": "r"}))
    with patch("coworker.connectors.hubspot.revoke") as rv:
        assert admin.revoke_all(store, 1)["revoked"] == ["hubspot"]
    rv.assert_called_once()


def test_revoke_survives_vendor_outage_and_retries(s):
    s.update_coworker(1, settings={"voice_id": "v42"})
    import requests

    with patch("coworker.voice.delete", side_effect=requests.ConnectionError("down")), \
            patch("observability.alert") as alert:
        out = twin.revoke(s, 1)
    assert out["voiceDeleted"] is False and alert.called
    assert s.get_coworker(1)["settings"]["pending_voice_deletes"] == ["v42"]
    with patch("coworker.voice.delete", side_effect=requests.ConnectionError("still down")):
        assert twin.retry_voice_deletes(s, 1) == 0
    with patch("coworker.voice.delete", return_value=True):
        assert twin.retry_voice_deletes(s, 1) == 1
    assert s.get_coworker(1)["settings"]["pending_voice_deletes"] == []
    assert twin.retry_voice_deletes(s, 1) == 0
