# Operator runbook

This is for whoever runs Ourogen Coworker in production. For first-time setup and every vendor's console steps, follow `PILOT_LAUNCH.md` in the repository. For the full list of settings, see [Set up](../setup.md).

## What runs where

```
 Browser / mobile app / Slack / Twilio / Gmail Pub/Sub / Graph / Recall
                 │ HTTPS
                 ▼
        backend (Flask, gunicorn) ──── MySQL (chats, users, cw_* tables)
                 │                 └── Redis (rate limits), S3 (twin files)
                 │
        coworker-worker (same image) ── every 60s, for each active coworker:
                 sync → responsibilities and scheduled tasks → due actions
                 → approval notifications → weekly report → heartbeat
```

- **backend** serves the API and all webhooks: Slack events and buttons, Twilio texts, mail push, meeting bot. Slow work (answering a Slack mention, a text) runs off the request, so webhooks return within the vendors' time limits.
- **coworker-worker** does everything that happens without a person present. If it stops, the coworker only works while someone has the web app open.

## Health

| Check | Healthy |
|---|---|
| `curl https://<host>/health` | `"status": "ok"` and `"worker": "ok"` (a worker ticked in the last 3 minutes; `COWORKER_WORKER_STALE_SECONDS`) |
| `docker compose ps` | `coworker-worker` is `healthy` (its health check is `python -m coworker.ops --check`) |
| `docker compose exec backend python -m coworker.config` | Production configuration passes (strong `JWT_SECRET_KEY`, `PROVIDER_KEY_ENCRYPTION_KEY` set, https URLs) |
| `docker compose exec backend python -m coworker.vendor_check` | Every configured vendor shows `ok` |

**Alerts** go to Sentry (`SENTRY_DSN`) and Slack (`ALERT_SLACK_WEBHOOK_URL`), throttled per problem:
- the worker is stale;
- a scheduled task failed every attempt;
- an approved action failed to send;
- a sync errored.

## Playbooks

**Worker stale or missing**
1. `docker compose logs --tail 200 coworker-worker`.
2. Then `docker compose up -d coworker-worker`. It has `restart: unless-stopped`, so a crash loop shows in its logs.

Missed scheduled runs within 2 hours run once on recovery; older ones are skipped. Users see a banner while the worker is stale.

**A user's connection says "reconnect"**
The provider revoked or expired the token (password change, admin policy, an app-consent change). The user already got a reconnect email and push. They reconnect in **Settings**. Nothing is lost; the next sync catches up.

**A vendor is down** (Anthropic, Google, Microsoft, Slack, Twilio, Recall)
- Scheduled tasks retry twice, then notify the owner.
- An approved action whose send fails is marked `failed`. It shows in the user's Activity and raises an alert, and isn't resent automatically. Once the vendor is back, the user can ask the coworker to redo it (for example, "reply to Dana again").
- If the outage is long, consider pausing affected coworkers. Pausing cancels queued sends.

**Slack bot doesn't answer**
1. Check `SLACK_BOT_ENABLED=1` and `SLACK_SIGNING_SECRET`.
2. In the Slack app, check that the `app_mention` and `message.im` bot events are subscribed and the Interactivity URL is set.
3. Check that the user clicked **Add the bot** (Settings shows "Bot is on").

A 401 in the backend logs on `/slack/events` means a wrong signing secret.

**Texts don't arrive or aren't answered**
1. In the Twilio console, check the message logs. US numbers need A2P 10DLC registration.
2. A 401 on `/sms/inbound` means the webhook URL Twilio signs differs from `BACKEND_URL`; set `TWILIO_WEBHOOK_URL` to the exact URL.

**Stop everything for one user**
Pause their coworker:
- `POST /api/coworker/pause` as them;
- or, in a Team org, remove them, which also revokes connections.

## Data and retention

- Synced content older than `COWORKER_RETENTION_DAYS` (default 180) is purged by the worker every 6 hours, along with old call transcripts.
- The audit trail is kept for `COWORKER_ACTIVITY_RETENTION_DAYS` (default 730).
- Back up MySQL daily; the `cw_*` tables hold all coworker state.
- Twin files live in S3 (or the `twin_data` volume locally).
- `PROVIDER_KEY_ENCRYPTION_KEY` encrypts every stored OAuth token. Losing or changing it breaks every connection, so keep it in your secrets manager.

## Schema changes

The backend creates and upgrades the `cw_*` tables on first use, including adding new columns to existing tables. SQL for each change is also in `packages/backend/database/migrations/` if you prefer to apply it yourself.
