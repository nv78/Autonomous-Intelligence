# Set up the Coworker

Everything works with **no API keys** in the fictional demo workspace. Each key below unlocks one more real capability.

## Run it

```bash
cp packages/backend/.env.example packages/backend/.env
docker compose up --build
```

Open `http://localhost:3000`, create an account, and you land in coworker onboarding. Choose **Try the Anote demo workspace**.

## Configuration

| Variable | Unlocks |
|---|---|
| `ANTHROPIC_API_KEY` | Claude for chat, drafting, and calls (default model `claude-opus-5-5`; override with `COWORKER_MODEL`). Without it, an offline planner handles the common requests. |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_COWORKER_REDIRECT_URI` | Your real Gmail, Calendar, and Drive |
| `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET` | Slack OAuth. You can also paste a user token (`xoxp-…`) in Settings. |
| `ELEVENLABS_API_KEY` | Server voice and voice cloning for your twin |
| `RECALL_API_KEY` | Meeting bot for Zoom, Meet, and Teams |
| `TAVUS_API_KEY`, `TAVUS_REPLICA_ID` | Real-time video avatar |
| `STRIPE_PRICE_COWORKER*`, `COWORKER_ENFORCE_PLANS=1` | Paid plans and plan gating |
| `PILOT_SLACK_WEBHOOK_URL`, `PILOT_BOOKING_URL`, `PILOT_ADMIN_EMAILS` | Founder pilot applications from ourogen.ai |
| `SMTP_URL`, `SMTP_FROM` | Relay for approval and digest emails when the user's Gmail can't send (`smtp://user:pass@host:587` or `smtps://…:465`) |
| `NOTIFY_BATCH_SECONDS`, `NOTIFY_MIN_INTERVAL_SECONDS` | Approval email batching (default 300s) and rate limit (default 1800s) |
| `COWORKER_SYNC_MODE` | `thread` (default) syncs on a background thread in the web process; `worker` leaves sync to `coworker-worker` |

### Google

1. In Google Cloud Console, enable the Gmail, Calendar, and Drive APIs.
2. On your OAuth client, add the redirect URI `http://localhost:5000/api/coworker/connections/google/callback`.
3. While the app is unverified, add yourself as a test user on the consent screen. Restricted Gmail scopes need Google's verification (CASA assessment) before public launch.

### Background worker

The web app runs the coworker loop while it's open. The `coworker-worker` service in `docker-compose.yml` runs it for everyone in the background:

```bash
python -m coworker.worker            # every 60s
python -m coworker.worker --once
```

## Evals

```bash
cd packages/backend
python -m coworker.evals.run
```

Suites cover triage, call guardrails, recall, and prompt-injection resistance. They also run in CI through `tests/test_coworker_trust.py`.
