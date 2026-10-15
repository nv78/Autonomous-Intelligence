"""Email attachments: read them into memory, and attach them to replies.

**Reading.** When Gmail or Outlook sync a new message, its file attachments
(PDF, Word, Excel, PowerPoint, plain text; up to ``MAX_BYTES`` each and
``MAX_PER_MESSAGE`` per message) are downloaded, turned into text, and stored
as ``doc`` items in the same thread. Recall then finds them like any other
document and cites the file by name. Attachment text is untrusted input: a
file that looks like a prompt-injection attempt is kept out of memory.

**Sending.** An email action may carry ``attachments``: a list of
``{"id", "name"}`` for attachment items the coworker has seen. The bytes
are fetched from the original mailbox at send time. Sending a file always
needs the user's approval (see ``security.assess_outbound``).
"""
from __future__ import annotations

import base64
import hashlib
import io
import logging
import re
import zipfile
from dataclasses import dataclass
from typing import Any

from coworker import security
from coworker.store import Store

log = logging.getLogger("coworker.attachments")

MAX_BYTES = 10 * 1024 * 1024
MAX_PER_MESSAGE = 5
TEXT_LIMIT = 20000
PROVIDERS = {"gmail": "gmail_att", "outlook": "outlook_att"}
EXTENSIONS = {".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".md"}


@dataclass
class File:
    name: str
    mime: str
    data: bytes


def supported(filename: str, size: int = 0) -> bool:
    name = (filename or "").lower()
    return bool(name) and any(name.endswith(ext) for ext in EXTENSIONS) and 0 <= size <= MAX_BYTES


def _xml_text(xml: bytes, tag: str) -> list[str]:
    return [html_unescape(t) for t in re.findall(rf"<{tag}[^>]*>([^<]*)</{tag}>", xml.decode("utf-8", errors="replace"))]


def html_unescape(text: str) -> str:
    import html

    return html.unescape(text)


def extract_text(data: bytes, filename: str) -> str:
    """Plain text from a supported file, or '' when it can't be read."""
    name = filename.lower()
    try:
        if name.endswith(".pdf"):
            import PyPDF2

            reader = PyPDF2.PdfReader(io.BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages[:50])
        elif name.endswith((".docx", ".xlsx", ".pptx")):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = z.namelist()
                if name.endswith(".docx"):
                    parts = _xml_text(z.read("word/document.xml"), "w:t")
                elif name.endswith(".xlsx"):
                    parts = _xml_text(z.read("xl/sharedStrings.xml"), "t") if "xl/sharedStrings.xml" in names else []
                    for sheet in sorted(n for n in names if n.startswith("xl/worksheets/sheet"))[:10]:
                        parts += _xml_text(z.read(sheet), "v")
                else:
                    slides = sorted((n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                                    key=lambda n: int(re.findall(r"\d+", n)[-1]))
                    parts = [t for s in slides[:60] for t in _xml_text(z.read(s), "a:t")]
            text = " ".join(parts)
        else:
            text = data.decode("utf-8", errors="replace")
    except Exception as exc:  # corrupt or encrypted files are skipped, never fatal to a sync
        log.info("couldn't read attachment %s: %s", filename, exc)
        return ""
    return re.sub(r"[ \t]+", " ", text).strip()[:TEXT_LIMIT]


def ingest(store: Store, user_id: int, parent: dict[str, Any], att: dict[str, Any], data: bytes) -> int | None:
    """Store one attachment as a doc item in the parent message's thread."""
    provider = PROVIDERS.get(parent.get("provider", ""), "")
    if not provider or not supported(att.get("filename", ""), len(data)):
        return None
    text = extract_text(data, att["filename"])
    if not text:
        return None
    meta = {"attachment_id": att["id"], "message_id": parent["external_id"], "mime": att.get("mime", ""),
            "size": len(data), "filename": att["filename"]}
    if security.is_suspicious(text):
        store.log(user_id, "security", f"Didn't read {att['filename']} from {parent.get('author_email')}: it looks like "
                  "a prompt-injection attempt.", {"filename": att["filename"]})
        return None
    key = hashlib.sha1(f"{parent['external_id']}:{att['id']}".encode()).hexdigest()[:40]
    return store.add_item(user_id, {
        "provider": provider, "external_id": key, "thread_id": parent.get("thread_id") or parent["external_id"],
        "kind": "doc", "direction": parent.get("direction", "inbound"), "author_name": parent.get("author_name", ""),
        "author_email": parent.get("author_email", ""), "subject": att["filename"],
        "body": f"Attachment “{att['filename']}” on “{parent.get('subject', '')}”:\n{text}",
        "occurred_at": parent.get("occurred_at"), "meta": meta,
    })


def ref_id(raw: Any) -> int | None:
    """An attachment reference as an item id: 12, "12", or {"id": 12}."""
    value = str(raw.get("id") if isinstance(raw, dict) else raw)
    return int(value) if value.isdigit() else None


def describe(store: Store, user_id: int, ids: list[Any]) -> list[dict[str, Any]]:
    """Validate attachment ids from the model or the UI into [{id, name}]; unknown ids are dropped."""
    out = []
    for raw in ids[:MAX_PER_MESSAGE]:
        item_id = ref_id(raw)
        item = store.get("cw_items", item_id, user_id) if item_id is not None else None
        if item and item.get("provider") in PROVIDERS.values():
            out.append({"id": int(item["id"]), "name": (item.get("meta") or {}).get("filename") or item["subject"]})
    return out


def files_for(store: Store, user_id: int, attachments: list[dict[str, Any]]) -> list[File]:
    """Download the attachments an approved email should carry."""
    from coworker.connectors.base import ConnectorError, Workspace

    ws = Workspace(store, user_id)
    files: list[File] = []
    for ref in attachments:
        item = store.get("cw_items", int(ref.get("id") or 0), user_id)
        if not item:
            raise ConnectorError(f"The attachment {ref.get('name', '')} is no longer available.", "not_found")
        meta = item.get("meta") or {}
        connector = ws._live("google" if item["provider"] == "gmail_att" else "microsoft")
        if connector is None:
            raise ConnectorError(f"Reconnect your mailbox to attach {meta.get('filename')}.", "reauth_required")
        data = connector.attachment_bytes(meta["message_id"], meta["attachment_id"])
        files.append(File(meta.get("filename") or item["subject"], meta.get("mime") or "application/octet-stream", data))
    return files


def b64decode_any(data: str) -> bytes:
    """Gmail returns url-safe base64 and Graph standard base64; this reads both."""
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
