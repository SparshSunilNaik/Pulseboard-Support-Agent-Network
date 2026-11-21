// Generated from sample_outputs/*.json. Do not edit by hand.
window.SAMPLES = [
 {
  "id": "q-01-timezone-export",
  "question": "My scheduled exports stopped after I changed my workspace timezone. What should I check?",
  "origin": "sample",
  "file": "sample_outputs/q-01-timezone-export.json",
  "output": {
   "classification": "answerable",
   "answer": "First, open the export config and confirm the normalized next-run time in the new timezone. Then, confirm the source report still exists and is accessible. Next, confirm destination credentials are valid. Finally, re-enable if it was auto-paused, then Save to recompute the schedule. After saving, exports that were silent-start paused are re-scheduled and resume from the next valid slot rather than backfilling. [7] (workspace-settings.md / Why did my scheduled exports stop?)\nSolutions:\n  * Change the workspace timezone to match the new timezone.\n  * Check the source report and ensure it still exists and is accessible.\n  * Verify the destination credentials are valid.\n  * Enable automatic pause/resume of scheduled exports.\n  * Save the export configuration and recompute the schedule.\n  * Re-enable scheduled exports.\n  * Ensure the workspace timezone matches the new timezone.\n  * Verify that the source report is still accessible and that the destination credentials are valid. [8] (workspace-settings.md / Troubleshooting schedule issues)\n\nscheduled-exports.md; resolved_cases.json; workspace-settings.md; data-retention.md; notifications.md.\n[Source: scheduled-exports.md, resolved_cases.json, workspace-settings.md, data-retention.md, notifications.md]",
   "sources": [
    {
     "document": "resolved_cases.json",
     "passage": "case-001"
    },
    {
     "document": "workspace-settings.md",
     "passage": "Timezone setting"
    },
    {
     "document": "data-retention.md",
     "passage": "Effect on scheduled exports"
    },
    {
     "document": "scheduled-exports.md",
     "passage": "How schedules work"
    },
    {
     "document": "scheduled-exports.md",
     "passage": "Fixing a stopped export"
    },
    {
     "document": "notifications.md",
     "passage": "Timezone influence"
    }
   ],
   "confidence": 0.97,
   "requires_human": false,
   "reason": "all checks passed",
   "node_trace": [
    "triage:answerable",
    "retrieval:top_k",
    "generate:attempt_1",
    "verify:passed",
    "finalize:answerable"
   ]
  }
 },
 {
  "id": "q-02-readonly-api",
  "question": "Can a read-only user create API credentials?",
  "origin": "sample",
  "file": "sample_outputs/q-02-readonly-api.json",
  "output": {
   "classification": "answerable",
   "answer": "Yes, only Owner and Admin roles can access the API credentials page. Read-only and Editor roles receive 403 from the credentials endpoint. However, a read-only user cannot create API credentials, create reports, modify settings, invite users, or access the application token page at all. The API credentials page returns a 403 for Read-only accounts. To create an API credential, sign in as Owner or Admin, open Settings > API credentials, create a new key, copy the secret once, and then use it to create the API key. Editor/Read-only roles have no access to the API credentials page, and the API refuses their tokens (HTTP 403).\nFollow-up: Is there any way to grant API-key access to lower roles? Yes, see User roles and permissions. For example, you can grant API key access to Editor/Read-only roles by creating a new API key for them. This will allow them to view and edit reports, but not make changes to other parts of the application. You can also assign these roles to specific users within the organization\n\napi-credentials.md; user-roles-and-permissions.md; resolved_cases.json.\n[Source: api-credentials.md, user-roles-and-permissions.md, resolved_cases.json]",
   "sources": [
    {
     "document": "resolved_cases.json",
     "passage": "case-002"
    },
    {
     "document": "user-roles-and-permissions.md",
     "passage": "Read-only role"
    },
    {
     "document": "api-credentials.md",
     "passage": "Who can create API credentials"
    },
    {
     "document": "resolved_cases.json",
     "passage": "case-006"
    },
    {
     "document": "user-roles-and-permissions.md",
     "passage": "Admin actions"
    },
    {
     "document": "user-roles-and-permissions.md",
     "passage": "Roles overview"
    }
   ],
   "confidence": 0.93,
   "requires_human": false,
   "reason": "all checks passed",
   "node_trace": [
    "triage:answerable",
    "retrieval:top_k",
    "generate:attempt_1",
    "verify:passed",
    "finalize:answerable"
   ]
  }
 },
 {
  "id": "q-03-escalation",
  "question": "The suggested solution did not work. What information should I collect before escalating?",
  "origin": "sample",
  "file": "sample_outputs/q-03-escalation.json",
  "output": {
   "classification": "requires_escalation",
   "answer": "I understand; let's get this to a human. Before escalating, please collect exactly the diagnostic packet: (1) the workspace slug and your email, (2) the original suggested solution and the outcome, (3) the run ID or correlation ID from Help -> Diagnostic log, (4) the exact error text / reason code, (5) the workspace timezone and plan. An Agent will need all five items or the escalation is returned.",
   "sources": [
    {
     "document": "escalation-procedure.md",
     "passage": "Information to collect before escalating"
    }
   ],
   "confidence": 0.92,
   "requires_human": true,
   "reason": "winner=requires_escalation sim=0.600 among prototypes",
   "node_trace": [
    "triage:requires_escalation",
    "safe_response:requires_escalation"
   ]
  }
 },
 {
  "id": "q-04-refund",
  "question": "Write a refund for my subscription.",
  "origin": "sample",
  "file": "sample_outputs/q-04-refund.json",
  "output": {
   "classification": "out_of_scope",
   "answer": "I can't take that action: 'Write a refund for my subscription.' is outside what Pulseboard Support can do. Refunds and account changes are handled by our billing team and are never issued directly by automated support. Please open a billing ticket via Settings -> Billing, or email billing@pulseboard.example. A human will follow up.",
   "sources": [
    {
     "document": "billing-subscriptions.md",
     "passage": "Refunds and invoices"
    }
   ],
   "confidence": 0.95,
   "requires_human": true,
   "reason": "matched rule 'out_of_scope' (deterministic)",
   "node_trace": [
    "triage:out_of_scope",
    "safe_response:out_of_scope"
   ]
  }
 },
 {
  "id": "q-05-ambiguous",
  "question": "How do I get my report to arrive every Monday? I heard exports are possible, is that on my plan?",
  "origin": "sample",
  "file": "sample_outputs/q-05-ambiguous.json",
  "output": {
   "classification": "requires_clarification",
   "answer": "To help you accurately, I need a bit more context. Which Pulseboard workspace are you referring to, and which plan is it on (Starter, Workspace, Enterprise)? Knowing the plan and feature you mean lets me give a precise answer — describing the plan often decides whether something like exports or data retention applies.",
   "sources": [],
   "confidence": 0.6,
   "requires_human": true,
   "reason": "matched rule 'requires_clarification' (requires plan/version disambiguation)",
   "node_trace": [
    "triage:requires_clarification",
    "safe_response:requires_clarification"
   ]
  }
 }
];
