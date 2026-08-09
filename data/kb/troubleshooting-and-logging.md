# Troubleshooting & Logging

## Diagnostic log

Every workspace has a diagnostic log. It records:

- Run-level events for scheduled exports with a **run ID** (see
  **scheduled-exports.md**),
- Query failures with a correlation/request ID,
- Auth events (login failures, failed 2FA, API auth results),
- Setting-change audit events (see **workspace-settings.md**).

The log is found at **Help → Diagnostic log**. Each row shows UTC timestamp,
event type, user, resource, status, and the correlation ID that links a single
request across our services.

## Reading rows

- A row with status `failed` contains a `reason_code` field like
  `report_not_found`, `destination_auth`, `quota_exceeded`.
- A row is written only for **completed** events; an export that never ran has
  no row — check scheduling issues first (timezone) rather than blaming the
  runner.

## Where diagnostics live and how long

- The diagnostic log keeps events for **90 days** and rolls over oldest first.
- When a ticket is escalated, you attach the correlation IDs, not the full log.
- The support client can request a **diagnostic bundle** (a JSON export of a
  filtered log window) from any workspace; the Owner downloads it under
  Help → Troubleshooting or support asks for it.

## Common triage flow

1. Find the run ID or correlation ID from the user.
2. Check the corresponding row in the diagnostic log (status + reason_code).
3. Match the reason_code to the fix matrix in **scheduled-exports.md** or
   **api-credentials.md** for auth-related codes.
4. If no row exists, the event never started: inspect the schedule itself.