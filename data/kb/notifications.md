# Notifications

## Overview

Pulseboard sends two kinds of notifications: in-app (bell icon, top-right)
and email. Email delivery uses the workspace timezone for scheduling digests
and for "delivery success / delivery failure" confirmations of scheduled
export outputs.

## Notification types

- **Export success / failure**: sent when a scheduled export completes or
  after two warning retries fail. Each email includes the run ID and a link
  to the run log. See **scheduled-exports.md**.
- **Digest**: a daily summary of report activity, sent at 08:00 in the
  **workspace timezone**.
- **Billing**: invoice-ready and payment-failed notices.
- **Security**: new-login, session-logout, API-key-created/revoked.

## Notification settings

Each user can mute in-app bell notifications per category but **cannot** stop
export-failure emails globally on the journey level for the workspace Owner.
Per-category opt outs are under **Settings → Notifications**. Turning off
email for the export category suppresses the success emails but failure
emails still route to the Owner's and Admin's registered address.

## Timezone influence

Digest and export-failure emails are timestamped and scheduled in the
**workspace timezone**, not the user's personal timezone. If a user changed
the workspace timezone, the digest and the next export run slot shift
together. See **workspace-settings.md**.

## Troubleshooting missing emails

- Check the contact email is verified on the member profile.
- Confirm the notification category is enabled for that member.
- Confirm the workspace timezone / schedule slot so the email is not being
  re-emitted inside a disabled window.
- Filter the diagnostic log for resolved notif rows; a silent failure leaves
  no notification row (see troubleshooting-and-logging.md).