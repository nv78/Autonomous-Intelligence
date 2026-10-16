# Team admin guide

The Team plan gives everyone on your team their own coworker, under one set of rules. Organization admins manage it under **Coworker → Team**.

## Create the organization and invite people

1. **Coworker → Team → Create organization**. Give it a name and your company domain (e.g. `acme.com`).
2. Invite teammates by email, as **Member** or **Admin**. An invite link only works for the address it was sent to. If the email doesn't arrive, share the link shown on the page.
3. Joining an organization counts as the employer's authorization for coworkers acting on that domain.

**Removing a member** pauses their coworker and revokes every connection it had (mail, calendar, Slack, CRM). With per-seat billing, the subscription updates on the spot.

## Rules every coworker follows

Admins set ceilings. Members can be stricter, never looser.

| Rule | Effect |
|---|---|
| Most autonomy per action type | e.g. email capped at *Ask first*, even if a member picked *Just do it* |
| Never send to these domains | Blocked recipients turn an action into an error that can't be approved |
| Always ask everyone for consent on calls | Forces all-party consent before note-taking |
| Allowed AI models | Members can only pick from this list |

The rules apply everywhere the coworker acts: chat, responsibilities, scheduled tasks, the Slack bot, and text messages.

## Sign-in (SSO) and joining automatically

Under **Team rules → Sign-in**:

- **Members must sign in with Google or Microsoft**: the password form refuses them, so offboarding in your identity provider ends their access at their next sign-in.
- **Automatic joining**: anyone who signs in with Google or Microsoft at your company domain joins as a member, with no invite needed. Guards against someone taking over your domain:
  - It only counts accounts your company manages: Google Workspace accounts on your domain, or Microsoft accounts in a tenant that verified the domain. A personal Google account registered on a work address doesn't count.
  - Public email domains (gmail.com, outlook.com, and so on) can't use it.
  - Only an admin who has signed in with a Google Workspace or Microsoft work account on that domain can turn it on, and only one organization can claim each domain.
  - People an admin removed can't rejoin this way.

## Provisioning with SCIM (Okta, Microsoft Entra)

Let your identity provider add and remove people automatically:

1. **Team → Team rules → Provisioning (SCIM) → Create token**. Copy the token; it's shown once.
2. In your identity provider, add a SCIM 2.0 app with:
   - base URL `https://<your Ourogen host>/api/coworker/scim/v2`;
   - authentication: bearer token, the one you copied;
   - provisioning actions: create users, deactivate users.
3. Assign people to the app.

**What each action does**
- **Assigning someone** invites them. They join when they accept the invite. If your organization's domain is set, they also join the first time they sign in with their company Google Workspace or Microsoft account.
- **Unassigning or deactivating someone** removes them: their coworker is paused and every connection is revoked.
- **Reactivating someone** invites them again.

Users are matched by email (`userName`). Group push isn't needed. **Rotate token** replaces the token, and **Turn off** stops provisioning.

## Usage

The member list shows each member's last 30 days:
- status;
- actions done;
- share of drafts approved without edits;
- estimated hours saved;
- call minutes.

## Billing

Team features come from the admin's subscription. If your Stripe price is per seat (`COWORKER_TEAM_PER_SEAT=1` on the server), inviting, auto-joining, or removing someone updates the quantity, prorated.
