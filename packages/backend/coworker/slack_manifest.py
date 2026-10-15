"""The Slack app manifest: every scope, event, and URL the coworker needs, in one paste.

    python -m coworker.slack_manifest                      # for BACKEND_URL
    python -m coworker.slack_manifest https://chat.ourogen.ai

In Slack: api.slack.com/apps → Create New App → From a manifest (or, for an
existing app, App Manifest in the sidebar) → paste the JSON. Then install the
app, copy the Client ID, Client Secret, and Signing Secret from Basic
Information, and set SLACK_BOT_ENABLED=1.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from coworker import slackbot
from coworker.connectors import slack

USER_EVENTS = ["message.im", "message.mpim", "message.channels", "message.groups"]
BOT_EVENTS = ["app_mention", "message.im"]


def manifest(backend_url: str, name: str = "Ourogen") -> dict[str, Any]:
    base = backend_url.rstrip("/")
    return {
        "display_information": {
            "name": name,
            "description": "Your AI coworker. @mention it or DM it to ask questions and hand off work.",
            "background_color": "#212121",
        },
        "features": {
            "app_home": {"home_tab_enabled": False, "messages_tab_enabled": True, "messages_tab_read_only_enabled": False},
            "bot_user": {"display_name": name, "always_online": True},
        },
        "oauth_config": {
            "redirect_urls": [f"{base}/api/coworker/connections/slack/callback"],
            "scopes": {"user": list(slack.USER_SCOPES), "bot": list(slackbot.BOT_SCOPES)},
        },
        "settings": {
            "event_subscriptions": {"request_url": f"{base}/api/coworker/slack/events",
                                    "user_events": USER_EVENTS, "bot_events": BOT_EVENTS},
            "interactivity": {"is_enabled": True, "request_url": f"{base}/api/coworker/slack/interactive"},
            "org_deploy_enabled": False, "socket_mode_enabled": False, "token_rotation_enabled": False,
        },
    }


def main(argv: list[str]) -> None:  # pragma: no cover - CLI wrapper
    url = argv[1] if len(argv) > 1 else os.environ.get("BACKEND_URL", "")
    if not url.startswith("https://"):
        raise SystemExit("Pass the public https backend URL, e.g. python -m coworker.slack_manifest https://chat.ourogen.ai")
    print(json.dumps(manifest(url), indent=2))


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv)
