# Data Retention

## Retention windows

Data is retained for the following periods, measured from creation or from the
last modification of the workspace, whichever is later:

| Data type | Retention | Action at end |
|-----------|-----------|---------------|
| Raw event payloads | 90 days | purged nightly |
| Aggregated report data | 24 months | compressed, then purged |
| Export run history | 90 days | removed from UI |
| Diagnostic log | 90 days | removed (see troubleshooting-and-logging.md) |
| Audit log | 24 months | immutable until expiry |

Base data used by scheduled exports is subject to the same retention windows.

## Effect on scheduled exports

Scheduled exports read from aggregated report data. If the retention window
has passed and the underlying rows have been pruned, the export **fails with
`report_not_found`** or "no data available" at run time. A change to the
workspace timezone does not by itself change retention, but it changes the
next-run slot, which can push the run outside the retention window. See
**scheduled-exports.md** and **workspace-settings.md**.

## Deleting data and legal holds

An Owner may delete datasets; the placed deletion is processed within 24
hours for the aggregated store and flagged as `pending_purge`. Deleted data
is not recoverable after 7 days; grant holders have no grace period for
exports that reference purged rows. Enterprise contracts may enable **legal
holds** that freeze purge; contact support to verify via the correct channel.

## Exports of retained data

Users can export retained data via scheduled exports or the API. Exports of
pruned datasets produce no data; the retention metadata describes whether a
datasource has been pruned.