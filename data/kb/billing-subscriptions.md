# Billing & Subscriptions

## Plans overview

Pulseboard ships three plans: **Starter**, **Workspace**, and **Enterprise**.

- **Starter** (free): 3 seats, dashboard-only, no scheduled exports, no API.
- **Workspace** (paid): 10 seats, scheduled exports (daily/weekly), read-only
  API scope, email support.
- **Enterprise** (custom): unlimited seats by contract, SSO/SAML, monthly
  exports, priority phone support, data region pinning.

## Questions about the right plan

Scheduled exports require at least the **Workspace** plan; the **Enterprise**
plan adds monthly cadence and SAML. If a user asks "does my plan include
scheduled exports", the plan must first be confirmed because Starter does not
include them at all. See **scheduled-exports.md**.

## Invoices and payments

Invoices are generated at renewal every Sunday UTC. Payment is charged to the
card on file; a failed payment re-attempts 3 times over 7 days before the
workspace is downgraded to FreeStarter read-only mode. An upgrade prorates
the remaining period; a downgrade applies at the next renewal.

## Refunds and chargebacks

Refunds are not processed by the Pulseboard support team. To request a
refund, the customer must contact the payments team via the billing portal
(email from the account holder) or open a ticket categorised as **Billing /
Refund**, which routes to the finance desk. Support agents cannot issue or
write refunds. Self-serve refunds exist for the first 14 days of a Workspace
plan if fewer than 2 paid invoices have been raised; the user starts it from
**Settings → Billing → Request refund**. Subscription cancellation is
processed on the same page under Manage plan.