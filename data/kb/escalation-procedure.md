# Escalation Procedure

## When to escalate

Escalate to a human support agent only when both of these hold:

1. The knowledge-base guidance and the automated diagnostics have already been
   attempted and the issue is not resolved, **and**
2. The case is one of: data loss, outage lasting over 30 minutes, security
   incident, billing dispute, or a repeat failure that persists across a
   reconfiguration of the export.

Do not escalate a simple settings question, and do not escalate first-touch
cases that the diagnostics can answer.

## Information to collect before escalating

Before escalating a case, the agent must gather a standard diagnostic packet.
Without this packet the human team returns the case to the queue:

1. Exact user's email and workspace slug.
2. The original question and the solution already attempted (and its result).
3. Export/report **run ID** and timestamp of the last failed run (see
   **scheduled-exports.md** and **troubleshooting-and-logging.md**).
4. Error message exactly as shown, plus the HTTP status code if applicable.
5. Workspace timezone and the current plan (`Workspace` / `Enterprise`).
6. Whether the issue reproduces for other members or only one account.

## Creating an escalation

- Owner or Admin pastes the packet into **Help → Escalate**, tagging a
  priority (P1/P2/P3) and the category.
- The agent records a reference: the case ID is returned immediately.
- P1 incidents page out the on-call human automatically.

You must always attach the diagnostic packet; a ticket missing the run ID
or the attempted return is auto-replied with a request for more information
rather than being queued.