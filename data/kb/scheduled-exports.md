# Scheduled Exports

## Overview

Scheduled exports push a dashboard or report on a recurring cadence (daily,
weekly, monthly) to a destination such as email or an SFTP/cloud bucket.
Every export references a **source report**, a **schedule**, a **format**
(CSV or XLSX) and a **destination**. Scheduled exports are a paid feature:
they require a Workspace or Enterprise plan. See **billing-subscriptions.md**.

## How schedules work

Schedules are evaluated against the **workspace timezone** by default. Each
schedule row shows the next-run time computed in that timezone. This is the
single most important thing to inspect when an export "suddenly stopped".

## Why exports stop

Common causes, in order of likelihood:

1. **Timezone shift.** Changing the workspace timezone moves the computed
   next-run time. A run that lands outside allowed hours (midnight-05:00
   in the workspace timezone) is skipped. See **workspace-settings.md**.
2. **Source report changed or deleted** — the reference breaks and the run
   fails with report-not-found.
3. **Destination credentials changed** (SFTP password, bucket policy).
4. **Plan downgraded** below the tier that includes scheduled exports.
5. **Retention window passed** — the source data has been pruned. See
   **data-retention.md**.

## Checking the export log

Every run writes to the export log (Settings → scheduled exports → run history).
Each entry has a run ID, trigger time (UTC and workspace local), result
(success / warning / failed) and a link to the diagnostic page. Warning states
are re-attempted twice with backoff before a failure notification is sent.

## Fixing a stopped export

- Open the export config and confirm the **normalized next-run time** in the
  new timezone.
- Confirm the source report still exists and is accessible.
- Confirm destination credentials are valid.
- Re-enable if it was auto-paused, then **Save** to recompute the schedule.
- After saving, exports that were silent-start paused are re-scheduled and
  resume from the next valid slot rather than backfilling.