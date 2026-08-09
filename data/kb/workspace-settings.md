# Workspace Settings

## Overview

Every Pulseboard account belongs to a single workspace. The workspace is the
container for dashboards, users, API credentials, scheduled exports and billing.
A workspace is created with one owner account, which can later transfer
ownership to another member with the Owner role.

## Timezone setting

The workspace has one global timezone setting. It is found under
**Settings → General → Workspace timezone**. This timezone is used to display
report timestamps and to schedule exports and digest notifications.

- The workspace default timezone is UTC unless a different zone is chosen.
- Changing the workspace timezone re-aligns **every scheduled export** which
  was configured with "Use workspace timezone". Exports do not fire at the new
  local time until you re-check their schedule. See **scheduled-exports.md**.
- Scheduled reports that were created on the **old timezone** keep their stored
  offset. A common cause of "exports stopped suddenly" is a timezone change
  that moved the next run out of valid business hours, or past the retention
  window. See **data-retention.md**.

## Changing settings

Changing the workspace name, timezone or currency requires the Owner or Admin
role. Read-only viewers cannot change workspace settings. Changing the
timezone does not require re-authentication, but changing the billing currency
does. All setting changes are written to the audit log.

## Audit trail

Every settings change is recorded with timestamp, acting user, and the
previous and new value. Audit logs are kept for 24 months. Owners can download
the audit log from Settings → Audit log.