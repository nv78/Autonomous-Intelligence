"""Incident-response commands.

    python -m coworker.admin revoke-all --user 42     # kill switch + revoke every token
    python -m coworker.admin pause-everyone           # pause every coworker
    python -m coworker.admin approve-voice --user 42 --reviewer you@ourogen.ai
                                                      # manual voice-match review

``revoke-all`` pauses the coworker, cancels queued actions, revokes Google
and Slack tokens with the providers, and deletes the stored tokens.
"""
from __future__ import annotations

import argparse
from typing import Any

from coworker import executor
from coworker.connectors import google, hubspot, microsoft, slack
from coworker.connectors.base import decrypt_token
from coworker.store import Store, get_store


def revoke_all(store: Store, user_id: int) -> dict[str, Any]:
    cancelled = executor.pause(store, user_id, "incident response: all access revoked")
    revoked = []
    for row in store.list_connections(user_id):
        token = decrypt_token(row.get("token_enc"))
        if row["provider"] == "google":
            google.revoke(token)
        elif row["provider"] == "slack":
            slack.revoke(token)
        elif row["provider"] == "hubspot":
            hubspot.revoke(token)
        elif row["provider"] == "microsoft":
            microsoft.revoke(token)
        store.delete_connection(user_id, row["provider"])
        revoked.append(row["provider"])
    store.log(user_id, "security", f"All access revoked ({', '.join(revoked) or 'no connections'}) by an administrator")
    return {"cancelled": cancelled, "revoked": revoked}


def pause_everyone(store: Store) -> int:
    users = [r["user_id"] for r in store.query("SELECT user_id FROM cw_coworkers WHERE status = 'active'")]
    for user_id in users:
        executor.pause(store, int(user_id), "incident response: paused by an administrator")
    return len(users)


def main() -> None:  # pragma: no cover - CLI wrapper
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("revoke-all")
    r.add_argument("--user", type=int, required=True)
    sub.add_parser("pause-everyone")
    v = sub.add_parser("approve-voice")
    v.add_argument("--user", type=int, required=True)
    v.add_argument("--reviewer", required=True)
    args = parser.parse_args()
    from app import create_app

    with create_app().app_context():
        if args.cmd == "revoke-all":
            print(revoke_all(get_store(), args.user))
        elif args.cmd == "approve-voice":
            from coworker import twin

            print(twin.approve_voice_match(get_store(), args.user, args.reviewer))
        else:
            print(f"Paused {pause_everyone(get_store())} coworkers")


if __name__ == "__main__":  # pragma: no cover
    main()
