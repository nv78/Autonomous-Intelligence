"""Text your coworker: SMS and WhatsApp through Twilio.

* **Linking a phone**: the owner adds a number in Settings, we text a
  6-digit code, and only a verified number is linked to them (one user per
  number). Texts from anyone else get one short reply and never reach a
  coworker.
* **Talking**: a text from a verified number runs as a chat turn (the same
  tools and approvals as the web chat) in the owner's "Text messages" chat,
  and the answer is texted back.
* **Approving**: ``YES 12`` approves action 12, ``NO 12`` skips it,
  ``EDIT 12 <new text>`` changes the message and approves it. A bare
  ``YES`` approves the only pending action. ``PAUSE`` / ``RESUME`` is the
  kill switch. ``STOP`` opts the number out of texts (carrier rules), and
  ``START`` opts back in. ``HELP`` lists the commands.
* **Notifications**: new approvals and scheduled-task results can be
  texted. Nothing is texted between 9pm and 8am in the owner's time zone.

Configure ``TWILIO_ACCOUNT_SID``, ``TWILIO_AUTH_TOKEN``, and
``TWILIO_FROM_NUMBER`` (and ``TWILIO_WHATSAPP_FROM`` for WhatsApp), and
point the number's "A message comes in" webhook at
``<BACKEND_URL>/api/coworker/sms/inbound``.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import re
import secrets
from datetime import timedelta
from typing import Any

import requests

from coworker.store import IntegrityError, Store, iso, parse_iso, utcnow

log = logging.getLogger("coworker.sms")

API = "https://api.twilio.com/2010-04-01"
CODE_TTL = timedelta(minutes=10)
MAX_CODE_SENDS_PER_HOUR = 5
MAX_ATTEMPTS = 5
SEGMENT = 1500
MAX_SEGMENTS = 3
QUIET_START, QUIET_END = 21, 8
NOTIFY_KINDS = ("approvals",)  # scheduled tasks text you when the task itself says "Text me"
HELP = ("Ourogen: text me anything you'd ask in chat. YES 12 approves action 12, NO 12 skips it, "
        "EDIT 12 <new text> changes and sends it. PAUSE stops your coworker, RESUME restarts it. STOP ends texts.")


class SmsError(Exception):
    def __init__(self, message: str, code: str = "invalid", status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


def is_configured() -> bool:
    return bool(os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN")
                and os.environ.get("TWILIO_FROM_NUMBER"))


def service_number() -> str:
    return os.environ.get("TWILIO_FROM_NUMBER", "")


def normalize(number: str) -> str:
    """E.164 (+15551234567). A bare 10-digit number is taken as US/Canada."""
    raw = (number or "").strip().removeprefix("whatsapp:")
    digits = re.sub(r"\D", "", raw)
    if not raw.startswith("+") and len(digits) == 10:
        digits = "1" + digits
    if not 8 <= len(digits) <= 15:
        raise SmsError("Enter a phone number with its country code, like +1 555 123 4567.")
    return "+" + digits


# -- Twilio -----------------------------------------------------------------------------------

def send(to: str, body: str, whatsapp: bool = False) -> list[str]:
    """Text ``body`` (split into at most 3 messages). Returns Twilio message ids."""
    if not is_configured():
        raise SmsError("Texting isn't configured on this server.", "not_configured", 501)
    sid = os.environ["TWILIO_ACCOUNT_SID"]
    sender = os.environ.get("TWILIO_WHATSAPP_FROM", "") if whatsapp else service_number()
    if whatsapp and not sender:
        raise SmsError("WhatsApp isn't configured on this server.", "not_configured", 501)
    ids = []
    for part in split(body):
        resp = requests.post(f"{API}/Accounts/{sid}/Messages.json", timeout=15,
                             auth=(sid, os.environ["TWILIO_AUTH_TOKEN"]),
                             data={"From": f"whatsapp:{sender}" if whatsapp else sender,
                                   "To": f"whatsapp:{to}" if whatsapp else to, "Body": part})
        if resp.status_code >= 300:
            raise SmsError(f"Twilio refused the message ({resp.status_code}): {resp.text[:200]}", "provider_error", 502)
        ids.append(str((resp.json() or {}).get("sid", "")))
    return ids


def split(body: str) -> list[str]:
    body = re.sub(r"\*\*(.+?)\*\*", r"\1", re.sub(r":::cw .*", "", body or "")).strip() or "Done."
    parts: list[str] = []
    while body and len(parts) < MAX_SEGMENTS:
        if len(body) <= SEGMENT:
            parts.append(body)
            break
        cut = body.rfind("\n", 0, SEGMENT)
        cut = cut if cut > SEGMENT // 2 else SEGMENT
        parts.append(body[:cut].rstrip())
        body = body[cut:].lstrip()
    if len(parts) == MAX_SEGMENTS and body and parts[-1] != body:
        parts[-1] = parts[-1][:SEGMENT - 40].rstrip() + "… (more in the Ourogen app)"
    return parts


def webhook_url() -> str:
    default = f"{os.environ.get('BACKEND_URL', 'http://localhost:5000').rstrip('/')}/api/coworker/sms/inbound"
    return os.environ.get("TWILIO_WEBHOOK_URL", default)


def valid_signature(params: dict[str, str], signature: str, url: str | None = None) -> bool:
    """Twilio signs the full public URL plus the sorted POST parameters with the auth token (HMAC-SHA1)."""
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    if not token or not signature:
        return False
    data = (url or webhook_url()) + "".join(f"{k}{params[k]}" for k in sorted(params))
    expected = base64.b64encode(hmac.new(token.encode(), data.encode(), hashlib.sha1).digest()).decode()
    return hmac.compare_digest(expected, signature)


# -- linking a phone ----------------------------------------------------------------------------

def _hash(code: str) -> str:
    key = os.environ.get("JWT_SECRET_KEY", "") or os.environ.get("PROVIDER_KEY_ENCRYPTION_KEY", "") or "dev"
    return hmac.new(key.encode(), code.encode(), hashlib.sha256).hexdigest()


def phone_for(store: Store, user_id: int) -> dict[str, Any] | None:
    return store.one("SELECT * FROM cw_phones WHERE user_id = %s", (user_id,))


def owner_of(store: Store, number: str) -> dict[str, Any] | None:
    return store.one("SELECT * FROM cw_phones WHERE number = %s AND verified = 1", (number,))


def start(store: Store, user_id: int, number: str, whatsapp: bool = False) -> dict[str, Any]:
    number = normalize(number)
    taken = owner_of(store, number)
    if taken and int(taken["user_id"]) != user_id:
        raise SmsError("That number is linked to another account.", "conflict", 409)
    current = phone_for(store, user_id)
    hour_ago = iso(utcnow() - timedelta(hours=1))
    sends = [t for t in ((current or {}).get("prefs") or {}).get("code_sends", []) if t > hour_ago]
    if len(sends) >= MAX_CODE_SENDS_PER_HOUR:
        raise SmsError("Too many codes. Try again in an hour.", "rate_limited", 429)
    code = f"{secrets.randbelow(10 ** 6):06d}"
    prefs = {**((current or {}).get("prefs") or {}), "code_sends": [*sends, iso()], "whatsapp": bool(whatsapp)}
    values = {"number": number, "verified": 0, "code_hash": _hash(code), "code_sent_at": iso(), "attempts": 0,
              "prefs": prefs}
    if current:
        store.update("cw_phones", int(current["id"]), user_id, values)
    else:
        try:
            store.insert("cw_phones", {"user_id": user_id, "created_at": iso(), **values})
        except IntegrityError as exc:
            raise SmsError("That number is linked to another account.", "conflict", 409) from exc
    send(number, f"Your Ourogen code is {code}. It expires in 10 minutes. If you didn't ask for this, ignore it.", whatsapp)
    return state(store, user_id)


def verify(store: Store, user_id: int, code: str) -> dict[str, Any]:
    row = phone_for(store, user_id)
    if not row or not row.get("code_hash"):
        raise SmsError("Add your number first.", "not_found", 404)
    if int(row.get("attempts") or 0) >= MAX_ATTEMPTS:
        raise SmsError("Too many wrong codes. Send a new one.", "rate_limited", 429)
    sent = parse_iso(row.get("code_sent_at") or "")
    if not sent or utcnow() - sent > CODE_TTL:
        raise SmsError("That code expired. Send a new one.", "expired", 410)
    if not hmac.compare_digest(_hash(re.sub(r"\D", "", code or "")), row["code_hash"]):
        store.update("cw_phones", int(row["id"]), user_id, {"attempts": int(row.get("attempts") or 0) + 1})
        raise SmsError("That code isn't right.", "invalid_code", 400)
    taken = owner_of(store, row["number"])
    if taken and int(taken["user_id"]) != user_id:
        raise SmsError("That number is linked to another account.", "conflict", 409)
    prefs = {**(row.get("prefs") or {}), "notify": (row.get("prefs") or {}).get("notify", ["approvals"]), "opted_out": False}
    store.update("cw_phones", int(row["id"]), user_id, {"verified": 1, "code_hash": "", "attempts": 0, "prefs": prefs})
    store.log(user_id, "settings", f"Linked {mask(row['number'])} for texting your coworker")
    send(row["number"], f"You're set. Text this number anytime to reach your AI coworker. {HELP}", bool(prefs.get("whatsapp")))
    return state(store, user_id)


def set_prefs(store: Store, user_id: int, notify: list[str]) -> dict[str, Any]:
    row = phone_for(store, user_id)
    if not row:
        raise SmsError("Add your number first.", "not_found", 404)
    store.update("cw_phones", int(row["id"]), user_id,
                 {"prefs": {**(row.get("prefs") or {}), "notify": [k for k in notify if k in NOTIFY_KINDS]}})
    return state(store, user_id)


def remove(store: Store, user_id: int) -> None:
    store.execute("DELETE FROM cw_phones WHERE user_id = %s", (user_id,))


def mask(number: str) -> str:
    return number[:2] + "•" * max(0, len(number) - 6) + number[-4:]


def state(store: Store, user_id: int) -> dict[str, Any]:
    row = phone_for(store, user_id)
    prefs = (row or {}).get("prefs") or {}
    return {
        "configured": is_configured(), "serviceNumber": service_number(),
        "whatsappAvailable": bool(os.environ.get("TWILIO_WHATSAPP_FROM")),
        "number": row["number"] if row else "", "verified": bool(row and row.get("verified")),
        "whatsapp": bool(prefs.get("whatsapp")), "notify": prefs.get("notify", []), "optedOut": bool(prefs.get("opted_out")),
    }


# -- texts in ------------------------------------------------------------------------------------

def _quiet(store: Store, user_id: int) -> bool:
    from coworker import scheduling

    hour = utcnow().astimezone(scheduling.tz_for(store.get_coworker(user_id) or {})).hour
    return hour >= QUIET_START or hour < QUIET_END


def notify(store: Store, user_id: int, body: str, kind: str = "tasks") -> bool:
    """Text the owner, outside quiet hours. Approval texts are a phone setting; tasks choose "Text me" themselves."""
    row = phone_for(store, user_id)
    prefs = (row or {}).get("prefs") or {}
    if not row or not row.get("verified") or prefs.get("opted_out"):
        return False
    if kind in NOTIFY_KINDS and kind not in prefs.get("notify", []):
        return False
    if not is_configured() or _quiet(store, user_id):
        return False
    try:
        send(row["number"], body, bool(prefs.get("whatsapp")))
        return True
    except (SmsError, requests.RequestException) as exc:
        log.warning("couldn't text user %s: %s", user_id, exc)
        return False


def notify_approvals(store: Store, user_id: int, pending: list[dict[str, Any]]) -> bool:
    lines = [f"#{p['id']} {p['title'][:90]}" for p in pending[:5]]
    more = f"\n…and {len(pending) - 5} more in the app" if len(pending) > 5 else ""
    example = pending[0]["id"]
    return notify(store, user_id, "Ourogen needs your OK:\n" + "\n".join(lines) + more +
                  f"\nReply YES {example} to approve, NO {example} to skip.", "approvals")


_YES = re.compile(r"^\s*(?:yes|y|approve|ok|send)\s*#?(\d+)?\s*$", re.I)
_NO = re.compile(r"^\s*(?:no|n|skip|reject)\s*#?(\d+)?\s*$", re.I)
_EDIT = re.compile(r"^\s*edit\s*#?(\d+)\s+(.+)$", re.I | re.S)


def handle_inbound(store: Store, sender: str, text: str, whatsapp: bool = False) -> str:
    """The reply to one inbound text. Never raises for user mistakes."""
    try:
        number = normalize(sender)
    except SmsError:
        return ""
    row = owner_of(store, number)
    if not row:
        return "This number isn't linked to an Ourogen coworker. Add it in Ourogen → Settings → Text messages."
    user_id = int(row["user_id"])
    word = text.strip().upper()
    prefs = row.get("prefs") or {}
    if word in ("STOP", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"):
        store.update("cw_phones", int(row["id"]), user_id, {"prefs": {**prefs, "opted_out": True}})
        return ""  # the carrier sends the opt-out confirmation
    if word in ("START", "UNSTOP"):
        store.update("cw_phones", int(row["id"]), user_id, {"prefs": {**prefs, "opted_out": False}})
        return "You'll get texts from your coworker again."
    if word in ("HELP", "INFO", "?"):
        return HELP
    from coworker import executor

    if word == "PAUSE":
        executor.pause(store, user_id, "Paused by text message")
        return "Paused. Nothing will go out until you text RESUME or resume in the app."
    if word == "RESUME":
        executor.resume(store, user_id)
        return "Back on. I'll pick up where I left off."
    if (m := _YES.match(text)) or (m := _NO.match(text)) or (m := _EDIT.match(text)):
        return _decide(store, user_id, m, text)
    from coworker import channels

    answer = channels.converse(store, user_id, "sms", number, text.strip()[:4000], "📱 Text messages")
    pending = [a for a in answer["actions"] if a["status"] == "proposed"]
    if pending:
        return answer["text"] + f"\nReply YES {pending[0]['id']} to approve."
    return answer["text"]


def _decide(store: Store, user_id: int, m: re.Match[str], text: str) -> str:
    from coworker import executor
    from coworker.executor import ActionError

    action_id = int(m.group(1)) if m.group(1) else 0
    if not action_id:
        pending = store.query("SELECT id FROM cw_actions WHERE user_id = %s AND status = 'proposed' ORDER BY id DESC",
                              (user_id,))
        if len(pending) != 1:
            return (f"You have {len(pending)} actions waiting. Reply with the number, like YES {pending[0]['id']}."
                    if pending else "Nothing is waiting for your approval.")
        action_id = int(pending[0]["id"])
    try:
        if m.re is _NO:
            action = executor.reject(store, user_id, action_id, "Skipped by text message")
            return f"Skipped #{action_id}: {action['title']}"
        changes = None
        if m.re is _EDIT:
            current = store.get("cw_actions", action_id, user_id) or {}
            field = "body" if current.get("type") == "email.send" else "text"
            changes = {field: m.group(2).strip()}
        executor.approve(store, user_id, action_id, changes)
        executor.run_due(store, user_id)
        action = store.get("cw_actions", action_id, user_id) or {}
        done = "Sent" if action.get("status") == "executed" else "Approved"
        return f"{done} #{action_id}: {action.get('title', '')}"
    except ActionError as exc:
        return f"Couldn't do #{action_id}: {exc}"


# -- setup (python -m coworker.sms setup | test +15551234567) --------------------------------

def _twilio(method: str, path: str, **data: str) -> dict[str, Any]:
    sid = os.environ["TWILIO_ACCOUNT_SID"]
    resp = requests.request(method, f"{API}/Accounts/{sid}{path}", auth=(sid, os.environ["TWILIO_AUTH_TOKEN"]),
                            data=data or None, timeout=15)
    if resp.status_code in (401, 403):
        raise SmsError("Twilio rejected the Account SID / Auth Token.", "unauthorized", 401)
    if resp.status_code >= 300:
        raise SmsError(f"Twilio error {resp.status_code}: {resp.text[:200]}", "provider_error", 502)
    return dict(resp.json() or {})


def number_settings() -> dict[str, Any]:
    """The Twilio record for TWILIO_FROM_NUMBER (its SID and current webhook)."""
    if not is_configured():
        raise SmsError("Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER first.", "not_configured", 501)
    from urllib.parse import quote

    found = _twilio("GET", f"/IncomingPhoneNumbers.json?PhoneNumber={quote(service_number())}").get("incoming_phone_numbers") or []
    if not found:
        raise SmsError(f"{service_number()} isn't a number in this Twilio account.", "not_found", 404)
    return dict(found[0])


def configure_webhook() -> dict[str, str]:
    """Point the number's "A message comes in" webhook at this backend. Safe to run again."""
    url = webhook_url()
    if not url.startswith("https://"):
        raise SmsError(f"The webhook must be public https; got {url}. Set BACKEND_URL (or TWILIO_WEBHOOK_URL).")
    record = number_settings()
    if record.get("sms_url") != url or str(record.get("sms_method", "")).upper() != "POST":
        _twilio("POST", f"/IncomingPhoneNumbers/{record['sid']}.json", SmsUrl=url, SmsMethod="POST")
        return {"number": service_number(), "webhook": url, "changed": "yes"}
    return {"number": service_number(), "webhook": url, "changed": "no (already set)"}


def main(argv: list[str]) -> None:  # pragma: no cover - CLI wrapper
    if len(argv) < 2 or argv[1] not in ("setup", "test"):
        raise SystemExit("usage: python -m coworker.sms setup | test +15551234567")
    try:
        if argv[1] == "setup":
            result = configure_webhook()
            print(f"OK: texts to {result['number']} go to {result['webhook']} (changed: {result['changed']})")
        else:
            print("Sent:", send(normalize(argv[2]), "Test from your Ourogen coworker. Texting works."))
    except (SmsError, IndexError) as exc:
        raise SystemExit(f"FAILED: {exc}") from exc


if __name__ == "__main__":  # pragma: no cover
    import sys

    main(sys.argv)
