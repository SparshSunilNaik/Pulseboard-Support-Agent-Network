# User Roles & Permissions

## Roles overview

Pulseboard uses four roles: **Owner**, **Admin**, **Editor**, and
**Read-only**. Owners and Admins manage the workspace; Editors create content;
Read-only members can view but cannot change anything.

| Role | View reports | Create reports | Manage users | Manage API keys | Billing | Settings |
|------|-------------|----------------|--------------|-----------------|---------|----------|
| Owner | yes | yes | yes | yes | yes | yes |
| Admin | yes | yes | yes | yes | yes | yes |
| Editor | yes | yes | no | no | no | no |
| Read-only | yes | no | no | **no** | no | no |

## Read-only role

Read-only is the most restricted member role. Read-only users can:

- View reports already published to the workspace.
- Run read-only queries against published datasets.
- Download exported files they are entitled to via a shared link.

Read-only users **cannot** create API credentials, create reports, modify
settings, invite users, or access the application token page at all. The API
credentials page returns a 403 for Read-only accounts. See
**api-credentials.md**.

## Admin actions

Admins can invite and remove members, create API credentials, change most
workspace settings, and set export destinations. Admins cannot change the
workspace currency, delete the workspace, or transfer ownership; those are
Owner-only. See **workspace-settings.md** and **billing-subscriptions.md**.

## Invitations and seats

Invitations are sent with one of the four roles and consume a **seat**.
Seats are counted against the plan; the plan boundary is enforced by
billing. See **billing-subscriptions.md**.