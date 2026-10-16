# Ourogen Coworker

Ourogen Coworker is an AI version of you at work. It learns from your email, Slack, calendar, and docs, then takes work off your plate:

- replies to inbound leads, scheduling requests, and support questions in your voice
- briefs you before meetings and nudges deals that go quiet
- answers teammates' questions on Slack from what it knows
- runs first sales calls by voice, qualifies the prospect, and sends the follow-up
- joins Zoom, Meet, and Teams calls through a meeting bot

It always identifies itself as your AI, and nothing goes out without your approval until you decide otherwise.

## Tell it in chat

The chat is the control plane. Say what you want and the coworker reports back in the same chat:

| You say | It does |
|---|---|
| "Reply to my unanswered emails" | Drafts one reply per waiting thread, each a card to approve. After sending, it posts exactly what went out. |
| "Join my 2pm with Dana and pitch the pilot" | Joins the call (meeting bot or call studio), says it's an AI, follows your context, then posts the summary, lead score, and a drafted follow-up. |
| "What did you do today?" | Lists calls taken, emails sent, and what's waiting for you. |
| "From now on, handle inbound leads" | Proposes a standing responsibility for you to confirm. |

On your phone (the Expo app in `packages/mobile`), the same chat delegates to your coworker. Push notifications have **Approve** and **Reject** buttons on the notification itself. The coworker tab shows Approvals, Today, and Calls. During a live call you can read the transcript, whisper an instruction only the coworker sees, or tap **Take over**: the coworker leaves, writes up the call so far, and opens the meeting link for you.

The chat sidebar shows **Today**, the work your coworker did, next to your chats. **Coworker → Today** shows one day at a time, with "Send my coworker" for meetings still ahead.

## Reach it anywhere, let it work on a schedule

- **Scheduled tasks**: "every weekday at 8:30 tell me what's on my plate", "every Friday at 4 draft my status update". See [Scheduled tasks](guide/scheduled-tasks.md).
- **Slack**: @mention the bot in any channel, or DM it.
- **Text messages**: text it, and approve with `YES 12`. See [Ways to reach your coworker](guide/channels.md).
- **Unattended**: a background worker keeps it working when nobody has the app open, with retries and alerts when something fails.

## How it works

| Layer | What it does | Code |
|---|---|---|
| Connectors | Gmail, Calendar, Drive, Outlook, Slack, HubSpot, Salesforce, Pipedrive, or a fictional demo workspace | `coworker/connectors/` |
| Memory | People graph, timeline, decision log, recall with citations | `coworker/memory.py` |
| Style | Learns your greeting, sign-off, length, and phrasing | `coworker/style.py` |
| Agent | Claude tool-use loop; offline planner without a key | `coworker/brain.py`, `coworker/tools.py` |
| Approvals | Autonomy levels, hard floors, send delay, undo, kill switch | `coworker/policy.py`, `coworker/executor.py` |
| Responsibilities | Standing jobs triggered by new mail, Slack, calendar, schedules | `coworker/responsibilities.py`, `coworker/schedules.py` |
| Channels | Slack bot, text messages, and scheduled runs share one entry point | `coworker/channels.py`, `coworker/slackbot.py`, `coworker/sms.py` |
| Operations | Worker heartbeat, run history, retries | `coworker/worker.py`, `coworker/ops.py` |
| Calls | Voice agent, sales playbook, meeting bot, summaries | `coworker/meetings.py` |
| Twin | Voice and likeness, only with verified consent | `coworker/twin.py`, `coworker/voice.py` |

The web app's chat stays the control plane. You delegate in chat, approve cards inline, and use **Coworker** in the sidebar for approvals, responsibilities, calls, activity, memory, your twin, and settings.

## Next

- [Your first 10 minutes](guide/getting-started.md)
- [Team admin guide](admin/team.md)
- [Operator runbook](operations/runbook.md)
- [Roadmap](roadmap.md)
- [Set it up](setup.md)
- [Trust, consent, and safety](trust.md)
- [API reference](api.md)
