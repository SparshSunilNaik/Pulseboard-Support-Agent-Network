# API Credentials

## Overview

Pulseboard exposes a REST API. Calls are authenticated with an API key sent
in the `Authorization: Bearer <key>` header. API keys are workspace-scoped:
a key works for the workspace it was created in and nowhere else.

## Who can create API credentials

Only **Owner** and **Admin** users can create, list, and revoke API
credentials. **Editor** and **Read-only** roles have no access to the API
credentials page, and the API refuses their tokens (HTTP 403). There is no
way to grant API-key access to lower roles. See **user-roles-and-permissions.md**.

## Creating a key

1. Sign in as Owner or Admin.
2. Open **Settings → API credentials**.
3. Click **Create key**, give it a name and optional expiry.
4. Copy the generated secret once, because it is stored hashed and is
   shown only at creation time.

## Key scoping and rotation

Each key can be restricted to read-only or read-write scope and to a single
report dataset. Rotate keys regularly: create a new key, update the consumer,
then revoke the old one. Revoked keys stop working immediately.

## Common failures

- **403 Invalid or restricted token** — key was revoked, expired, or the
  calling user's role does not permit API access. See roles above.
- **401 Unauthorized** — malformed or missing `Authorization` header, or the
  key is not workspace-scoped to the resource host.
- API credentials never expire by default; set an expiry at creation to
  follow least-privilege practice.