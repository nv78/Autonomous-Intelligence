"""Check every configured vendor with read-only calls before going live.

    python -m coworker.vendor_check          # table; exits 1 if anything failed
    python -m coworker.vendor_check --json

Nothing here sends a message, joins a call, clones a voice, or spends
meaningful credits: each check uses a list/whoami-style endpoint. A vendor
without credentials is reported as ``skipped``, not failed. Admins can run
the same checks from ``GET /api/coworker/admin/vendors``.
"""
from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

import requests

TIMEOUT = 15


def _result(name: str, status: str, detail: str) -> dict[str, str]:
    return {"name": name, "status": status, "detail": detail}


def _http(name: str, url: str, headers: dict[str, str], describe: Callable[[dict[str, Any]], str]) -> dict[str, str]:
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return _result(name, "fail", f"network error: {exc.__class__.__name__}")
    if resp.status_code in (401, 403):
        return _result(name, "fail", f"key rejected (HTTP {resp.status_code})")
    if resp.status_code >= 400:
        return _result(name, "fail", f"HTTP {resp.status_code}: {resp.text[:120]}")
    try:
        body = resp.json() if resp.content else {}
    except ValueError:
        body = {}
    return _result(name, "ok", describe(body))


def check_anthropic() -> dict[str, str]:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _result("Anthropic", "skipped", "ANTHROPIC_API_KEY not set (offline planner)")
    model = os.environ.get("COWORKER_MODEL", "claude-opus-5-5")
    return _http("Anthropic", f"https://api.anthropic.com/v1/models/{model}",
                 {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
                 lambda b: f"model {b.get('id', model)} available")


def check_elevenlabs() -> dict[str, str]:
    if not os.environ.get("ELEVENLABS_API_KEY"):
        return _result("ElevenLabs", "skipped", "ELEVENLABS_API_KEY not set (browser voice)")

    def describe(b: dict[str, Any]) -> str:
        sub = b.get("subscription") or {}
        used, limit = sub.get("character_count"), sub.get("character_limit")
        clone = "instant cloning allowed" if sub.get("can_use_instant_voice_cloning") else "instant cloning NOT on this plan"
        return f"{sub.get('tier', 'unknown')} tier, {used}/{limit} characters used, {clone}"

    return _http("ElevenLabs", "https://api.elevenlabs.io/v1/user", {"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}, describe)


def check_recall() -> dict[str, str]:
    if not os.environ.get("RECALL_API_KEY"):
        return _result("Recall.ai", "skipped", "RECALL_API_KEY not set (no meeting bot)")
    from coworker.connectors import recall

    return _http("Recall.ai", f"{recall._base()}/bot/?page_size=1", recall._headers(),
                 lambda b: f"reachable at {urlparse(recall._base()).netloc}, {b.get('count', 'some')} bots on record")


def check_tavus() -> dict[str, str]:
    if not os.environ.get("TAVUS_API_KEY"):
        return _result("Tavus", "skipped", "TAVUS_API_KEY not set (photo avatar)")
    replica = os.environ.get("TAVUS_REPLICA_ID", "")
    if not replica:
        return _result("Tavus", "fail", "TAVUS_REPLICA_ID is required with TAVUS_API_KEY")
    return _http("Tavus", f"https://tavusapi.com/v2/replicas/{replica}", {"x-api-key": os.environ["TAVUS_API_KEY"]},
                 lambda b: f"replica {b.get('replica_name') or replica} status {b.get('status', 'unknown')}")


def check_google() -> dict[str, str]:
    cid, secret = os.environ.get("GOOGLE_CLIENT_ID"), os.environ.get("GOOGLE_CLIENT_SECRET")
    if not cid and not secret:
        return _result("Google OAuth", "skipped", "not configured (demo workspace only)")
    if not (cid and secret):
        return _result("Google OAuth", "fail", "set both GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET")
    redirect = os.environ.get("GOOGLE_COWORKER_REDIRECT_URI", "")
    if os.environ.get("APP_ENV") == "production" and not redirect.startswith("https://"):
        return _result("Google OAuth", "fail", "GOOGLE_COWORKER_REDIRECT_URI must be https in production")
    from coworker import mail_push

    push = "real-time Gmail on" if mail_push.gmail_enabled() else "Gmail polled every minute (set GMAIL_PUBSUB_TOPIC for real time)"
    return _result("Google OAuth", "ok", f"client configured; redirect {redirect or '(default)'}; {push}")


def check_slack() -> dict[str, str]:
    cid, secret = os.environ.get("SLACK_CLIENT_ID"), os.environ.get("SLACK_CLIENT_SECRET")
    if not cid and not secret:
        return _result("Slack OAuth", "skipped", "not configured (users can paste a token)")
    if not (cid and secret):
        return _result("Slack OAuth", "fail", "set both SLACK_CLIENT_ID and SLACK_CLIENT_SECRET")
    events = "real-time events on" if os.environ.get("SLACK_SIGNING_SECRET") else "polling every minute (set SLACK_SIGNING_SECRET for real-time)"
    return _result("Slack OAuth", "ok", f"client configured; {events}")


def check_microsoft() -> dict[str, str]:
    cid, secret = os.environ.get("MICROSOFT_CLIENT_ID"), os.environ.get("MICROSOFT_CLIENT_SECRET")
    if not cid and not secret:
        return _result("Outlook (Microsoft 365)", "skipped", "not configured (Gmail only)")
    if not (cid and secret):
        return _result("Outlook (Microsoft 365)", "fail", "set both MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET")
    from coworker.connectors import microsoft

    redirect = microsoft.redirect_uri()
    if os.environ.get("APP_ENV") == "production" and not redirect.startswith("https://"):
        return _result("Outlook (Microsoft 365)", "fail", "MICROSOFT_REDIRECT_URI must be https in production")
    return _result("Outlook (Microsoft 365)", "ok", f"client configured (tenant {os.environ.get('MICROSOFT_TENANT', 'common')}); redirect {redirect}")


def check_public_url() -> dict[str, str]:
    """Recall transcripts and Slack events are pushed to BACKEND_URL, so it must be reachable from the internet."""
    url = os.environ.get("BACKEND_URL", "")
    host = urlparse(url).hostname or ""
    if not url or host in ("localhost", "127.0.0.1", "0.0.0.0") or host.endswith(".local"):
        status = "fail" if os.environ.get("APP_ENV") == "production" else "skipped"
        return _result("Public backend URL", status, f"BACKEND_URL={url or '(unset)'}: meeting bots and Slack events can't reach it")
    if not url.startswith("https://"):
        return _result("Public backend URL", "fail", "BACKEND_URL must be https for webhooks")
    return _result("Public backend URL", "ok", url)


def check_crms() -> dict[str, str]:
    pairs = {"HubSpot": "HUBSPOT", "Salesforce": "SALESFORCE", "Pipedrive": "PIPEDRIVE"}
    half = [name for name, env in pairs.items() if bool(os.environ.get(f"{env}_CLIENT_ID")) != bool(os.environ.get(f"{env}_CLIENT_SECRET"))]
    if half:
        return _result("CRM OAuth", "fail", f"set both client id and secret for {', '.join(half)}")
    ready = [name for name, env in pairs.items() if os.environ.get(f"{env}_CLIENT_ID")]
    if not ready:
        return _result("CRM OAuth", "skipped", "no CRM OAuth apps (users can paste HubSpot or Pipedrive tokens)")
    return _result("CRM OAuth", "ok", f"{', '.join(ready)} configured")


def check_smtp() -> dict[str, str]:
    url = os.environ.get("SMTP_URL", "")
    if not url:
        return _result("SMTP relay", "skipped", "SMTP_URL not set (notifications use the user's Gmail)")
    import smtplib
    import ssl
    from urllib.parse import unquote

    u = urlparse(url)
    try:
        secure = u.scheme == "smtps"
        server: smtplib.SMTP = (smtplib.SMTP_SSL(u.hostname or "", u.port or 465, timeout=TIMEOUT,
                                                 context=ssl.create_default_context())
                                if secure else smtplib.SMTP(u.hostname or "", u.port or 587, timeout=TIMEOUT))
        with server:
            if not secure:
                server.starttls(context=ssl.create_default_context())
            if u.username:
                server.login(unquote(u.username), unquote(u.password or ""))
    except Exception as exc:
        return _result("SMTP relay", "fail", f"{exc.__class__.__name__}: {str(exc)[:100]}")
    return _result("SMTP relay", "ok", f"logged in to {u.hostname}")


def check_s3() -> dict[str, str]:
    bucket = os.environ.get("TWIN_S3_BUCKET", "")
    if not bucket:
        return _result("Twin storage (S3)", "skipped", "TWIN_S3_BUCKET not set (local disk)")
    try:
        from coworker import blobstore

        blobstore._s3().head_bucket(Bucket=bucket)
    except Exception as exc:
        return _result("Twin storage (S3)", "fail", f"{exc.__class__.__name__}: {str(exc)[:100]}")
    return _result("Twin storage (S3)", "ok", f"bucket {bucket} reachable")


def check_redis() -> dict[str, str]:
    url = os.environ.get("RATE_LIMIT_REDIS_URL") or os.environ.get("REDIS_URL", "")
    if not url:
        return _result("Redis", "skipped", "not set (per-process rate limits)")
    try:
        import redis

        redis.Redis.from_url(url, socket_timeout=3, socket_connect_timeout=3).ping()
    except Exception as exc:
        return _result("Redis", "fail", f"{exc.__class__.__name__}: {str(exc)[:100]}")
    return _result("Redis", "ok", "ping ok")


def check_voiceprint() -> dict[str, str]:
    from coworker import voiceprint

    if not voiceprint.available():
        return _result("Voice match", "fail", "ffmpeg missing: voice cloning will be blocked")
    return _result("Voice match", "ok", f"{voiceprint.backend()} backend, ffmpeg available")


CHECKS = [check_anthropic, check_elevenlabs, check_recall, check_tavus, check_google, check_microsoft, check_slack,
          check_crms, check_smtp, check_s3, check_redis, check_voiceprint, check_public_url]


def run_all() -> list[dict[str, str]]:
    return [check() for check in CHECKS]


def main() -> None:  # pragma: no cover - CLI wrapper
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results = run_all()
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"{r['status'].upper():8s} {r['name']:18s} {r['detail']}")
    raise SystemExit(1 if any(r["status"] == "fail" for r in results) else 0)


if __name__ == "__main__":  # pragma: no cover
    main()
