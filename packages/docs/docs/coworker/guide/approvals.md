# Approvals and autonomy

Every outbound action is an **action**: an email, a Slack post, a calendar invite, or a CRM update. Each one gets an autonomy level. The level decides whether the coworker asks you first.

| Level | In Settings | What happens |
|---|---|---|
| `suggest` | Prepare only | It drafts the action. You send it yourself. |
| `approve` | Ask first (default) | A card waits for your approval in chat, in **Approvals**, by email, by push, and optionally by text. |
| `notify` | Do it, then tell me | It sends after a short delay (so you can undo), then tells you. |
| `silent` | Just do it | It sends. The action shows up in **Activity**. |

Levels apply per kind of action (**Settings → Autonomy**) and per responsibility or scheduled task. A task's own level wins for what that task does.

## Things that always ask

Some cases always wait for you, whatever the level:

- the message looks like phishing or a prompt-injection attempt;
- a recipient is new or outside the thread;
- an attachment would go out;
- it would create or change a responsibility;
- your organization caps the level or blocks the domain (see [Team admin](../admin/team.md)).

## Approve from anywhere

- **Web**: the card in chat, or **Coworker → Approvals**.
- **Phone**: the push notification's **Approve** button.
- **Email**: the "review and approve" link in the approval email.
- **Text**: reply `YES 12` (or `NO 12`, or `EDIT 12 <new text>`).
- **Slack**: the **Approve / Skip** buttons on the bot's message.

## Undo and the kill switch

- **Undo**: the **Undo** button on an action's card (in chat or **Approvals**) cancels it during the send delay, or reverses it afterwards where the service allows: a Slack post is deleted, an invite cancelled. Sent email can't be recalled. That's why email defaults to asking first.
- **Pause**: the button in the Coworker header stops everything immediately. You can also text `PAUSE`, or reply `STOP` to any email from your coworker. Queued actions are cancelled, and responsibilities and scheduled tasks stop until you resume.
