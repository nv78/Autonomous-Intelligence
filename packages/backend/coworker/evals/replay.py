"""Replay harness: turn real decisions into regression cases.

    # From a pilot user's workspace (run where the database is reachable)
    python -m coworker.evals.replay export --user 42 --out cases.jsonl
    # Against the current code, with nothing sent anywhere
    python -m coworker.evals.replay run --cases cases.jsonl

``export`` anonymizes every decided action that came from an inbound
message: email addresses become ``person-N@example-M.test``, the user's
and contacts' names become placeholders, and only the trigger, the action
payload, the user's decision, and what the coworker concluded at the time
are kept. ``run`` replays each case in a throwaway workspace and checks
that today's code reaches the same conclusions:

* the trigger is triaged into the same category,
* the same risk flags fire on the same outbound payload, and
* anything that needed the user's approval before still needs it.

A replay never changes a decision the user made; it catches the coworker
getting quietly less careful.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from typing import Any

from coworker import memory, policy, security
from coworker.store import Store

EMAIL_RE = re.compile(r"[\w.+-]+@([\w-]+\.)+[\w-]+")


class _Anonymizer:
    def __init__(self, names: list[str]) -> None:
        self.emails: dict[str, str] = {}
        self.domains: dict[str, str] = {}
        self.names = sorted({n for n in names if n and len(n) > 2}, key=len, reverse=True)

    def email(self, value: str) -> str:
        value = value.lower()
        if value not in self.emails:
            domain = value.split("@")[-1]
            self.domains.setdefault(domain, f"example-{len(self.domains) + 1}.test")
            self.emails[value] = f"person-{len(self.emails) + 1}@{self.domains[domain]}"
        return self.emails[value]

    def text(self, value: str) -> str:
        out = EMAIL_RE.sub(lambda m: self.email(m.group(0)), value or "")
        for i, name in enumerate(self.names):
            out = re.sub(re.escape(name), f"Person {chr(65 + i % 26)}", out, flags=re.IGNORECASE)
        return out

    def payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        def scrub(v: Any) -> Any:
            if isinstance(v, str):
                return self.text(v)
            if isinstance(v, list):
                return [scrub(x) for x in v]
            if isinstance(v, dict):
                return {k: scrub(x) for k, x in v.items()}
            return v
        return {k: scrub(v) for k, v in payload.items()}


def export(store: Store, user_id: int, limit: int = 500) -> list[dict[str, Any]]:
    coworker = store.get_coworker(user_id) or {}
    names = [coworker.get("owner_name") or ""] + [p.get("name") or "" for p in store.people(user_id, include_hidden=True)]
    names += [part for n in list(names) for part in n.split() if len(part) > 3]
    anon = _Anonymizer(names)
    ctx = memory.company_context(store, user_id)
    rows = store.query(
        "SELECT * FROM cw_actions WHERE user_id = %s AND source_item_id IS NOT NULL AND status NOT IN ('proposed') "
        "ORDER BY id DESC LIMIT %s", (user_id, limit),
    )
    cases = []
    for a in rows:
        item = store.get("cw_items", a["source_item_id"], user_id)
        if not item:
            continue
        decision = "rejected" if a["status"] == "rejected" else "edited" if a["edited"] else (
            "expired" if a["status"] == "expired" else "approved")
        cases.append({
            "trigger": {
                "kind": item["kind"], "subject": anon.text(item.get("subject") or ""), "body": anon.text(item.get("body") or ""),
                "author_email": anon.email(item.get("author_email") or "unknown@unknown.test"),
                "labels": (item.get("meta") or {}).get("labels") or [],
            },
            "action": {"type": a["type"], "payload": anon.payload(a.get("payload") or {}), "autonomy": a["autonomy"]},
            "decision": decision,
            "expected": {
                "category": memory.classify(item, ctx),
                "risks": sorted({r["code"] for r in a.get("risk") or []}),
                "held": a["approval_reason"] is not None and not str(a["approval_reason"]).startswith("Allowed"),
            },
        })
    return cases


def _workspace() -> Store:
    path = os.path.join(tempfile.mkdtemp(prefix="cw-replay-"), "replay.db")
    store = Store(f"sqlite:///{path}")
    store.create_coworker(1, "Owner", "owner@example-0.test", mode="demo")
    return store


def replay(cases: list[dict[str, Any]]) -> dict[str, Any]:
    store = _workspace()
    ctx = memory.company_context(store, 1)
    regressions = []
    for i, case in enumerate(cases):
        t = case["trigger"]
        item = {"kind": t["kind"], "subject": t["subject"], "body": t["body"], "author_email": t["author_email"],
                "meta": {"labels": t.get("labels") or []}}
        got_category = memory.classify(item, ctx)
        payload = case["action"]["payload"]
        participants = {t["author_email"].lower()}
        risks = security.assess_outbound(
            case["action"]["type"], payload, known_emails=set(), thread_participants=participants,
            trigger_text=t["body"], thread_text=t["body"], owner_email="owner@example-0.test",
        ) if policy.ACTION_TYPES.get(case["action"]["type"], {}).get("external") else []
        held = not policy.decide(case["action"]["type"], case["action"].get("autonomy", "approve"), risks)["auto"]
        got_risks = sorted({r["code"] for r in risks})
        problems = []
        if got_category != case["expected"]["category"]:
            problems.append(f"category {case['expected']['category']} → {got_category}")
        lost = set(case["expected"]["risks"]) - set(got_risks) - {"new_recipient", "outside_thread", "cross_thread_data"}
        if lost:
            problems.append(f"risk flags no longer raised: {', '.join(sorted(lost))}")
        if case["expected"]["held"] and not held:
            problems.append("needed approval before, would now run without it")
        if problems:
            regressions.append({"case": i, "subject": t["subject"][:60], "decision": case["decision"], "problems": problems})
    n = len(cases)
    return {"n": n, "regressions": regressions, "score": 1 - len(regressions) / n if n else 1.0}


def main() -> None:  # pragma: no cover - CLI wrapper
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export")
    ex.add_argument("--user", type=int, required=True)
    ex.add_argument("--out", required=True)
    ex.add_argument("--limit", type=int, default=500)
    rp = sub.add_parser("run")
    rp.add_argument("--cases", required=True)
    args = parser.parse_args()
    if args.cmd == "export":
        from app import create_app
        from coworker.store import get_store

        with create_app().app_context():
            cases = export(get_store(), args.user, args.limit)
        with open(args.out, "w") as fh:
            fh.writelines(json.dumps(c) + "\n" for c in cases)
        print(f"Exported {len(cases)} anonymized cases to {args.out}")
        return
    with open(args.cases) as fh:
        cases = [json.loads(line) for line in fh if line.strip()]
    result = replay(cases)
    print(f"{result['score']:.0%} unchanged ({result['n']} cases)")
    for r in result["regressions"]:
        print(f"  regression #{r['case']} “{r['subject']}”: {'; '.join(r['problems'])}")
    raise SystemExit(0 if not result["regressions"] else 1)


if __name__ == "__main__":  # pragma: no cover
    main()
