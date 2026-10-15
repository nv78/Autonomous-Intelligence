# Coworker API

All routes live under `/api/coworker` and need a JWT (`Authorization: Bearer <token>`), except the OAuth callbacks, the meeting-bot webhook, and pilot applications.

| Area | Routes |
|---|---|
| Setup | `GET /`, `POST /` (`{"mode": "demo" \| "live"}`), `PATCH /`, `POST /demo/simulate`, `POST /demo/reset` |
| Connections | `GET /connections`, `POST /connections/google/start`, `GET /connections/google/callback`, `POST /connections/slack/start`, `GET /connections/slack/callback`, `POST /connections/slack/token`, `DELETE /connections/<provider>`, `POST /sync` (queues a background sync, returns `202`), `GET /sync/status` |
| Memory | `POST /memory/rebuild`, `GET /memory/learned`, `GET /memory/people`, `PATCH`/`DELETE /memory/people/<id>`, `GET /memory/timeline`, `DELETE /memory/<id>`, `GET /memory/recall?q=`, `GET /memory/status?name=`, `GET /inbox`, `GET /items/<id>` |
| Style | `GET /style`, `POST /style/rules`, `DELETE /style/rules` |
| Chat | `POST /chat/stream` (SSE events: `session_id`, `text`, `tool`, `card`, `title`, `error`, `done`) |
| Approvals | `GET /actions?status=&ids=`, `PATCH /actions/<id>`, `POST /actions/<id>/approve`, `/reject`, `/undo` |
| Oversight | `GET /activity` (`?format=csv`), `GET /digest`, `GET /status`, `POST /pause`, `POST /resume`, `POST /tick` |
| Responsibilities | `GET /responsibilities`, `POST /responsibilities`, `PATCH`/`DELETE /responsibilities/<id>`, `POST /responsibilities/<id>/run`, `GET /onboarding/suggestions` |
| Autonomy | `GET /autonomy`, `PUT /autonomy` |
| Calls | `GET`/`PUT /playbook`, `GET /meetings`, `POST /meetings`, `GET /meetings/<id>`, `POST /meetings/<id>/turn`, `POST /meetings/<id>/end`, `POST /meetings/recall/webhook` |
| Twin | `GET /twin`, `POST /twin/assets`, `GET /twin/assets/<id>/file`, `DELETE /twin/assets/<id>`, `POST /twin/consent/challenge`, `POST /twin/consent`, `POST /twin/voice`, `DELETE /twin`, `POST /twin/avatar/session`, `POST /voice/tts` |
| Billing & data | `GET /billing`, `POST /billing/checkout`, `GET /export`, `DELETE /data` |
| Pilot | `POST /pilot/applications` (public), `GET /pilot/applications` (`PILOT_ADMIN_EMAILS` only) |

## Example: delegate in chat

```bash
curl -N -X POST http://localhost:5000/api/coworker/chat/stream \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message": "Reply to Dana"}'
```

The stream includes a `card` event with the proposed email. Approve it:

```bash
curl -X POST http://localhost:5000/api/coworker/actions/12/approve -H "Authorization: Bearer $TOKEN"
```

## Example: sync and watch progress

`POST /sync` returns in well under a second. The sync runs in the background:

```bash
curl -X POST "http://localhost:5000/api/coworker/sync?rebuild=1" -H "Authorization: Bearer $TOKEN"
curl http://localhost:5000/api/coworker/sync/status -H "Authorization: Bearer $TOKEN"
# {"running": true, "total": 412, "items": {"gmail": 380, "gcal": 32}, "job": {"phase": "syncing", ...}}
```

Phases go `queued`, `syncing`, `learning`, then `done` or `error`.
