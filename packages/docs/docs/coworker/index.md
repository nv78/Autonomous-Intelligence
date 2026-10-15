# Ourogen Coworker

Ourogen Coworker is an AI version of you at work. It learns from your email, Slack, calendar, and docs, then takes work off your plate:

- replies to inbound leads, scheduling requests, and support questions in your voice
- briefs you before meetings and nudges deals that go quiet
- answers teammates' questions on Slack from what it knows
- runs first sales calls by voice, qualifies the prospect, and sends the follow-up
- joins Zoom, Meet, and Teams calls through a meeting bot

It always identifies itself as your AI, and nothing goes out without your approval until you decide otherwise.

## How it works

| Layer | What it does | Code |
|---|---|---|
| Connectors | Gmail, Calendar, Drive, Slack, or a fictional demo workspace | `coworker/connectors/` |
| Memory | People graph, timeline, decision log, recall with citations | `coworker/memory.py` |
| Style | Learns your greeting, sign-off, length, and phrasing | `coworker/style.py` |
| Agent | Claude tool-use loop; offline planner without a key | `coworker/brain.py`, `coworker/tools.py` |
| Approvals | Autonomy levels, hard floors, send delay, undo, kill switch | `coworker/policy.py`, `coworker/executor.py` |
| Responsibilities | Standing jobs triggered by new mail, Slack, calendar, schedules | `coworker/responsibilities.py` |
| Calls | Voice agent, sales playbook, meeting bot, summaries | `coworker/meetings.py` |
| Twin | Voice and likeness, only with verified consent | `coworker/twin.py`, `coworker/voice.py` |

The web app's chat stays the control plane. You delegate in chat, approve cards inline, and use **Coworker** in the sidebar for approvals, responsibilities, calls, activity, memory, your twin, and settings.

## Next

- [Set it up](setup.md)
- [Trust, consent, and safety](trust.md)
- [API reference](api.md)
