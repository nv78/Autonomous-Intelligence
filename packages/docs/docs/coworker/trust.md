# Trust, consent, and safety

An AI that emails people and joins calls on your behalf has to be trustworthy by construction. Each rule below is enforced in code, and the table names where.

!!! warning "Legal review"
    This page describes the product's controls. It is not legal advice. Have counsel review it, including recording-consent and digital-replica laws in your jurisdictions, before the first external pilot.

## 1. It always says it's an AI

| Rule | Enforcement |
|---|---|
| Every call opens with an AI disclosure | `meetings.disclosure_line`, first transcript turn |
| Asked "are you human?", it says it's an AI | `meetings._guardrail_reply`, evaluated before the model |
| A model reply claiming to be human is replaced | `meetings.respond` hard rule |
| Emails sent without approval always carry a disclosure footer | `executor._execute`, `disclosure()` |
| Slack messages are visibly marked as from the AI | `connectors/slack.py` `AI_PREFIX` |
| The meeting bot is named "<Name>'s AI coworker (Ourogen)" and posts a disclosure in chat | `connectors/recall.py` |
| The avatar always shows an "AI" badge | `web/src/coworker/AvatarStage.tsx` |

## 2. You approve what matters

- Autonomy per action type: `suggest`, `approve` (default), `notify`, `silent`.
- **Hard floors** force approval whatever the setting: first contact with someone new, pricing/discounts/contracts/payments, details from another conversation, more than 5 recipients, anything triggered by a suspicious message, and deletion (`policy.decide`, `security.assess_outbound`).
- Changing responsibilities always needs a yes.
- Posting in a Slack Connect channel (shared with another company) always needs approval.
- Approval emails link to a confirmation page for each action. Opening the link changes nothing; only pressing Approve or Reject does, so mail scanners can't approve on your behalf. Links expire after 72 hours.
- If you reply in an email thread yourself, the coworker drops its pending draft for that thread instead of sending a second reply.
- The coworker only ever *suggests* more autonomy after 20 unedited approvals.

## 3. You can see and stop everything

- Every proposal, approval, send, failure, and escalation is in the activity log, exportable as CSV.
- The kill switch pauses all responsibilities and cancels queued sends (`executor.pause`). Replying **STOP** to any notification or digest email does the same.
- Emails wait out an undo window (`send_delay_seconds`, 20s by default when live).
- Incident response: `python -m coworker.admin revoke-all --user <id>` revokes every token.

## 4. Inbound content is data, never instructions

Email, Slack, and call content is wrapped in `<untrusted_content>` before any model sees it, and it's scanned for injection, concealment, and payment-fraud patterns. The policy assumes the model can be fooled: a red-team suite of 60 injection variants checks that the policy layer still holds the resulting actions for approval. Responsibilities never answer suspicious messages.

## 5. Calls and recording consent

- The coworker announces it's taking notes and asks if that's okay.
- If anyone objects or asks it to leave, it stops recording and leaves (`LEAVE_RE`).
- All-party consent is the default (`recording_consent`). Until the other side agrees, the coworker answers them live but stores only a placeholder for what they said, and nothing derived from it. It asks at most twice. You can switch to one-party consent in Settings where the law allows.
- Discounts, contracts, legal terms, and security questionnaires are escalated to you, never decided on the call.

## 6. Your likeness is yours

- Only the account holder can create a twin.
- Before any cloning, you record a randomized on-camera statement with a one-time code. The transcript must contain your name, the word "authorize", and the code (`twin.verify`).
- One click deletes the cloned voice at the provider, every uploaded file, and the consent recording.
- **Prototype limit:** consent verification checks the spoken statement and code. It doesn't yet biometrically match the consent video to the samples. That match is required before general availability.

## 7. Your data

- OAuth tokens are encrypted at rest (`PROVIDER_KEY_ENCRYPTION_KEY`).
- Disconnecting revokes the token with the provider and deletes everything synced from it.
- Synced email, Slack, calendar, and docs are deleted after 180 days, and raw call transcripts after 180 days (call summaries are kept). The activity log is kept for two years as an audit trail.
- **Download my data** exports everything stored. **Delete my coworker** removes it all.
- Customer data is not used to train models.

## 8. At work

On a work account (a company email domain), the coworker asks you to confirm that you own the company or your employer allows it. Until you do, it reads and drafts but sends nothing (`governance.needs_employer_ok`).

An employer can ask us to turn coworkers off for their whole domain. We add it to `COWORKER_DISABLED_DOMAINS`, which blocks new coworkers on that domain, pauses existing ones, and refuses approvals. SSO and a self-serve admin console are on the roadmap.
