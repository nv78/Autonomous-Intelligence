# Launching a real pilot user

This is the checklist for putting one real person (say, a friend who runs a company) on Ourogen in production: their own inbox, calendar, Slack, and meetings.

It assumes production is `https://chat.ourogen.ai`, deployed by `.github/workflows/deploy.yml` when `develop` is merged into `main`. Substitute your domain wherever you see it.

**Time:** about half a day of setup on your side, then 10 minutes for the pilot user.

---

## 0. Before you merge to `main`: don't take the live chatbot down

With `APP_ENV=production`, the new backend **refuses to start** when `JWT_SECRET_KEY` is weak (shorter than 32 characters or a default value) or `PROVIDER_KEY_ENCRYPTION_KEY` is missing. That protects users' OAuth tokens, but it also means a deploy onto an old `.env` would take chat.ourogen.ai offline.

1. On the EC2 host, add the new settings to the backend's environment file first.
2. Then run the check against that file with the image CI built from `develop`, or any checkout of this repo:

```bash
# on the host, from APP_DIR (adjust the env file name to the one your compose file uses)
docker run --rm --env-file .env <ECR_REGISTRY>/<ECR_REPOSITORY>:<develop-sha> python -m coworker.config
# or from a checkout:  cd packages/backend && set -a && . /path/to/.env && set +a && python -m coworker.config
```

It prints `OK: safe to start in production` or the exact settings to fix, and exits 1 on errors.

- **Changing `JWT_SECRET_KEY` signs everyone out once.** Pick the value now and never change it again.
- **Generate `PROVIDER_KEY_ENCRYPTION_KEY` once** with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. If it ever changes, every saved connection stops working.
- **The coworker stores its data in the same MySQL database as the chatbot,** and creates its tables on first use. Don't set `COWORKER_DB_URL` in production.

## 1. Ship the code and run the worker

1. Merge `develop` into `main`. The deploy workflow builds the backend image (it includes ffmpeg for voice checks), restarts the stack on the EC2 host, and publishes the web app.
2. On the EC2 host, open the compose file in `APP_DIR`. Check two things:
   - It has a **`coworker-worker`** service: `python -m coworker.worker --interval 60`, with the same image and environment as the backend. See `docker-compose.yml` in this repo. Without the worker, the coworker only works while the user has the web app open.
   - Its environment passes through every variable in steps 2–7 below.
3. Set `BACKEND_URL=https://chat.ourogen.ai` and `FRONTEND_URL=https://chat.ourogen.ai`. Meeting bots and Slack push events to `BACKEND_URL`, so it must be public and use HTTPS.
4. Set `ANTHROPIC_API_KEY`. Without it, the coworker falls back to a scripted planner.
5. Set `PROVIDER_KEY_ENCRYPTION_KEY`. It encrypts OAuth tokens at rest. Generate it once and never change it, or every connection breaks.
6. When everything below is set, run this on the host:

   ```bash
   docker compose exec backend python -m coworker.vendor_check
   ```

   Every vendor you configured should show `ok`.

## 2. Google (Gmail, Calendar, Drive)

1. In Google Cloud Console, enable the Gmail, Calendar, and Drive APIs.
2. On the OAuth client, add this authorized redirect URI:
   `https://chat.ourogen.ai/api/coworker/connections/google/callback`
3. On the **OAuth consent screen**, leave the app in **Testing** and add the pilot user's Google address as a **test user**. Up to 100 test users can connect without Google's verification.
4. Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_COWORKER_REDIRECT_URI` (the URI above).

> **Testing-mode caveat:** while the app is in Testing, Google expires refresh tokens after **7 days**. The coworker then stops reading and sending. It emails and pushes the user a **Reconnect Google** link, and Settings shows a Reconnect button. Reconnecting takes one click.
>
> To remove the weekly reconnect, publish the app. Gmail's restricted scopes require Google's verification and a third-party security assessment (CASA). Plan on several weeks; this is tracked in #381.

## 3. Microsoft 365 (Outlook mail and calendar)

1. In the Azure portal, go to **Microsoft Entra ID → App registrations → New registration**.
   - Supported account types: **any organizational directory and personal Microsoft accounts**.
   - Redirect URIs: platform **Web**, both of these:
     - `https://chat.ourogen.ai/api/coworker/connections/microsoft/callback` (connecting Outlook)
     - `https://chat.ourogen.ai/auth/microsoft/callback` ("Continue with Microsoft" sign-in)
2. Under **Certificates & secrets**, create a client secret.
3. Under **API permissions**, add these Microsoft Graph **delegated** permissions:
   - `User.Read`
   - `Mail.Read`, `Mail.ReadWrite`, `Mail.Send`
   - `Calendars.Read`, `Calendars.ReadWrite`
   - `offline_access`
4. Set these environment variables:
   - `MICROSOFT_CLIENT_ID`
   - `MICROSOFT_CLIENT_SECRET`
   - `MICROSOFT_TENANT=common`
   - `MICROSOFT_REDIRECT_URI` (the first URI above). Sign-in uses `BACKEND_URL` + `/auth/microsoft/callback`; override it with `MICROSOFT_LOGIN_REDIRECT_URI` if needed.

> If the pilot user's company blocks user consent for unverified apps, their IT admin must approve the app once. They can grant admin consent from the app's **API permissions** page. Completing **Publisher verification** (it needs a Microsoft Partner Network ID) removes the "unverified" warning for everyone.

## 3b. Real-time email (recommended)

Without this step, the worker checks mail every minute. With it, a new email gets a draft in seconds.

- **Outlook** needs nothing extra. Once `BACKEND_URL` is public HTTPS, each Outlook connection subscribes to inbox notifications at `/api/coworker/microsoft/notify` and renews the subscription itself.
- **Gmail** uses Google Cloud Pub/Sub, in the same project as your OAuth client:
  1. Create a topic, e.g. `gmail-push`. On its **Permissions** tab, give `gmail-api-push@system.gserviceaccount.com` the **Pub/Sub Publisher** role.
  2. Create a **push** subscription on the topic. Set its endpoint to `https://chat.ourogen.ai/api/coworker/google/push?token=<a long random string>`.
  3. Set two variables:
     - `GMAIL_PUBSUB_TOPIC=projects/<project-id>/topics/gmail-push`
     - `GMAIL_PUSH_TOKEN=<that same string>`

     To use signed OIDC tokens instead of the `token` in the URL, turn on authentication on the subscription and set `GMAIL_PUSH_AUDIENCE` (and optionally `GMAIL_PUSH_SERVICE_ACCOUNT`).
  4. Each Gmail connection starts its watch on the next sync and renews it before the 7-day expiry.

If a watch or subscription can't be created, the coworker keeps polling and retries an hour later.

## 4. Slack (real time)

1. Create a Slack app at https://api.slack.com/apps.
2. Under **OAuth & Permissions**, add these **user** token scopes:
   - `channels:history`, `groups:history`, `im:history`, `mpim:history`
   - `channels:read`, `groups:read`, `im:read`
   - `users:read`, `users:read.email`
   - `chat:write`
3. Add the redirect URL: `https://chat.ourogen.ai/api/coworker/connections/slack/callback`
4. Under **Event Subscriptions**:
   - Turn it on.
   - Set the Request URL to `https://chat.ourogen.ai/api/coworker/slack/events`. Slack verifies it immediately, so deploy first.
   - Under **Subscribe to events on behalf of users**, add `message.im`, `message.mpim`, `message.channels`, and `message.groups`.
5. Set `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_REDIRECT_URI`, and `SLACK_SIGNING_SECRET` (from **Basic Information**).

With the signing secret set, Slack pushes each message and the coworker answers in seconds. Without it, Slack is polled every minute.

To install in someone else's workspace, either turn on public distribution, or have them paste a user token (`xoxp-…`) in **Settings**.

### @mention the coworker (Slack bot)

With the bot, anyone can talk to the coworker in Slack: "@Ourogen what did Acme say about pricing?" in a channel, or a DM to the bot.
- **The owner's messages are commands**, the same as the web chat. Proposed actions come back with **Approve / Skip** buttons.
- **A teammate's question** is answered in the thread from the owner's memory and docs.
  - It's posted right away only when the owner's Slack autonomy is "notify" or "silent".
  - Otherwise the owner gets the answer to approve by DM, or a question when the coworker doesn't know.

1. In the same Slack app, open **App Home**:
   - Add a bot user (display name e.g. "Ourogen").
   - Turn on the **Messages tab** and "Allow users to send messages".
2. Under **OAuth & Permissions**, add these **bot** token scopes: `app_mentions:read`, `chat:write`, `im:history`, `im:read`, `im:write`, `users:read`.
3. Under **Event Subscriptions → Subscribe to bot events**, add `app_mention` and `message.im`.
4. Under **Interactivity & Shortcuts**:
   - Turn it on.
   - Set the Request URL to `https://chat.ourogen.ai/api/coworker/slack/interactive`.
5. Set `SLACK_BOT_ENABLED=1`. Each user reconnects Slack once (**Settings → Slack → Add the bot**).

## 5. Meetings (Recall.ai) and voice (ElevenLabs)

1. Set `RECALL_API_KEY`. If your Recall workspace isn't in us-east-1, also set `RECALL_API_BASE` to your region's URL.
2. Set `ELEVENLABS_API_KEY` so the coworker can speak in the user's cloned voice. Without it, the bot speaks in a stock voice.
3. Set `VOICEPRINT_BACKEND=resemblyzer` before you open sign-ups to people you don't know. The built-in voice match only catches clearly different voices.

How the user sends the coworker to a meeting: in chat, *"Join my 2pm with Northwind. Find out their budget and timeline."* Here is what happens:

1. A bot named "<Name>'s AI coworker (Ourogen)" joins and posts an AI and recording disclosure in the meeting chat.
2. It asks for recording consent, then follows the call from live captions.
3. It answers out loud or in the meeting chat.
4. When the call ends, it posts a summary, a lead score, and a drafted follow-up into the chat the user asked from.

**On the call:**
- It waits for a short pause before answering (`COWORKER_TURN_SILENCE`, 0.8 seconds by default), and ignores "mm-hm" and "yeah".
- It stops talking when someone interrupts.
- If its answer is slow, it says "Good question." first.
- Calls use a fast model (Haiku when you've chosen Claude; set `COWORKER_CALL_MODEL` to override) and Recall's low-latency transcription. Set `RECALL_TRANSCRIPT=captions` to use the meeting platform's captions instead.
- Each call summary records reply-time p50 and p95.

**Expect** about 1.5–3 seconds before a spoken answer. That works for intro and qualification calls. Fully streaming speech is the next step.

## 5b. Text messages (Twilio SMS and WhatsApp)

Owners can text the coworker ("what's my next meeting?", "reply to Dana that Tuesday works") and approve by replying `YES 12`.

1. In [Twilio](https://console.twilio.com), buy a phone number that can send SMS.
   - US numbers need **A2P 10DLC** registration (brand + campaign) before carriers deliver texts. Toll-free numbers need toll-free verification instead.
2. Under the number's **Messaging configuration**, set "A message comes in" to **Webhook**, `https://chat.ourogen.ai/api/coworker/sms/inbound`, HTTP POST.
3. Set:
   - `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN`, from the console home page;
   - `TWILIO_FROM_NUMBER` in E.164 form, e.g. `+15551234567`.
4. WhatsApp (optional): set up a WhatsApp sender in Twilio with the same webhook, then set `TWILIO_WHATSAPP_FROM`.
5. Each owner links their phone in **Settings → Text messages**, using a 6-digit code.

Twilio signs each webhook with the full public URL. If the backend sits behind a proxy with a different public URL than `BACKEND_URL`, set `TWILIO_WEBHOOK_URL` to the exact URL configured in Twilio.

## 6. Notifications

| Setting | Purpose |
|---|---|
| `SMTP_URL`, `SMTP_FROM` | Approval and "reconnect" emails when the user's own mailbox can't send |
| `EXPO_ACCESS_TOKEN` | Optional. Push approvals to the mobile app |
| `SENTRY_DSN`, `ALERT_SLACK_WEBHOOK_URL` | Errors and failed sends reach you before the user notices |

## 7. Billing (optional for a friend)

Leave `COWORKER_ENFORCE_PLANS=0` to run the pilot free.

**Team plan.** Under **Coworker → Team**, an admin can:
- create an organization;
- invite teammates by email (the link only works for the invited address);
- set rules every member's coworker follows: autonomy ceilings, blocked domains, all-party recording consent, and allowed models;
- require Google or Microsoft sign-in for members (the password form refuses them);
- let anyone who signs in with Google or Microsoft at the company domain join automatically. This only works for a non-public domain that the admin's own address is on, and for one organization per domain. People an admin removed can't rejoin this way.

Members get Team features through the admin's subscription. If the Team price in Stripe is per seat, set `COWORKER_TEAM_PER_SEAT=1`. Inviting or removing someone then updates the subscription quantity, prorated. To charge, create the three coworker prices in Stripe, set `STRIPE_PRICE_COWORKER`, `STRIPE_PRICE_COWORKER_CALLS`, and `STRIPE_PRICE_COWORKER_TEAM`, then set `COWORKER_ENFORCE_PLANS=1`.

---

## The pilot user's first 10 minutes

1. Sign up at `https://chat.ourogen.ai`, then open **Coworker**. Onboarding starts.
2. **Connect Google** or **Connect Outlook**. This grants read access only. Then add Slack.
3. The coworker reads 90 days of history and shows what it learned: people, deals, and how they write. Correct anything wrong.
4. Click **Allow sending** in **Settings**. Keep every autonomy level on **Ask me first** for the first week.
5. **Twin** tab: record the consent sentence and a short voice sample, so calls can use their voice.
6. Install the mobile app from TestFlight (iOS) or Play internal testing (Android) and sign in, so approvals arrive as notifications with Approve and Reject buttons. To publish the builds, follow `packages/mobile/README.md`.
7. Try two hand-offs in chat:
   - *"Reply to my unanswered emails from today."* It drafts the replies and asks for approval. After sending, it posts exactly what went out.
   - *"Join my next call and qualify them."*
   - Once they trust it: *"Join all my external intro calls from now on."* Before each matching call, it posts a brief with a Skip link.

**What they can always do:** pause everything from the header or the phone, reply STOP to any email the coworker sends, and disconnect a source. Disconnecting deletes everything synced from it.

## Before you invite them, check

- [ ] `vendor_check` is all `ok` for what you configured.
- [ ] You connected your own account end to end: Google or Outlook, Slack, and one real meeting.
- [ ] A test email approval arrived, and approving it sent the email.
- [ ] Pausing the coworker stopped a scheduled send.
- [ ] They're on the Google test-user list, or their Microsoft tenant allows the app.

---

## Appendix: where to get each key

| Setting | Where |
|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com → API keys](https://console.anthropic.com/settings/keys) |
| `OPENAI_API_KEY`, `GEMINI_API_KEY` (optional models) | [platform.openai.com/api-keys](https://platform.openai.com/api-keys), [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| `GOOGLE_CLIENT_ID` / `_SECRET` | [Google Cloud → Credentials](https://console.cloud.google.com/apis/credentials). Set up the consent screen and test users at [OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent). Enable the [Gmail](https://console.cloud.google.com/apis/library/gmail.googleapis.com), [Calendar](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com), and [Drive](https://console.cloud.google.com/apis/library/drive.googleapis.com) APIs. |
| `MICROSOFT_CLIENT_ID` / `_SECRET` | [Azure portal → App registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade) (or [entra.microsoft.com](https://entra.microsoft.com)) |
| `SLACK_CLIENT_ID` / `_SECRET` / `SLACK_SIGNING_SECRET` | [api.slack.com/apps](https://api.slack.com/apps). Open your app → **Basic Information** |
| `RECALL_API_KEY` | [recall.ai](https://www.recall.ai) → dashboard → API keys. Use the API base URL for your workspace's region. |
| `ELEVENLABS_API_KEY` | [elevenlabs.io → API keys](https://elevenlabs.io/app/settings/api-keys). Voice cloning needs a paid plan. |
| `TAVUS_API_KEY`, `TAVUS_REPLICA_ID` (optional video avatar) | [platform.tavus.io](https://platform.tavus.io) |
| `HUBSPOT_CLIENT_ID` / `_SECRET` (optional) | [developers.hubspot.com](https://developers.hubspot.com) → your app. Users can instead paste a private-app token from HubSpot **Settings → Integrations → Private Apps**. |
| `SALESFORCE_CLIENT_ID` / `_SECRET` (optional) | In Salesforce: **Setup → App Manager → New Connected App**. Enable OAuth with scopes `api` and `refresh_token`, and callback `https://chat.ourogen.ai/api/coworker/connections/salesforce/callback` |
| `PIPEDRIVE_CLIENT_ID` / `_SECRET` (optional) | [Pipedrive Developer Hub](https://developers.pipedrive.com). Users can instead paste their personal API token (**Personal preferences → API**). |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_*` (optional) | [dashboard.stripe.com/apikeys](https://dashboard.stripe.com/apikeys), [Webhooks](https://dashboard.stripe.com/webhooks), [Products](https://dashboard.stripe.com/products) |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM_NUMBER` (optional) | [console.twilio.com](https://console.twilio.com). Buy a number under **Phone Numbers → Buy a number**; US numbers need [A2P 10DLC registration](https://console.twilio.com/us1/develop/sms/regulatory-compliance/a2p-10dlc-overview) |
| `EXPO_ACCESS_TOKEN` (optional) | [expo.dev](https://expo.dev) → account settings → Access tokens |
| `SMTP_URL` | Any SMTP relay, e.g. [Resend](https://resend.com), [Postmark](https://postmarkapp.com), [SendGrid](https://sendgrid.com). Format: `smtp://user:pass@host:587` |
| `SENTRY_DSN` | [sentry.io](https://sentry.io) → project → Client Keys (DSN) |
| `ALERT_SLACK_WEBHOOK_URL`, `PILOT_SLACK_WEBHOOK_URL` | [Slack incoming webhooks](https://api.slack.com/messaging/webhooks) |
| `JWT_SECRET_KEY`, `PROVIDER_KEY_ENCRYPTION_KEY` | Generate them yourself: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
