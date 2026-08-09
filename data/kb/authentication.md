# Authentication

## Overview

Pulseboard supports social login (Google / GitHub), email+password, and
SAML single sign-on for Enterprise workspaces. All sessions use HttpOnly
cookies with a 12-hour idle timeout. To sign in, open the workspace login
page at the account's registered domain.

## Email and password

Passwords must be at least 12 characters. Failed login attempts are rate
limited: 5 failures trigger a temporary lockout of 15 minutes on that
account and IP. A support ticket is not required to unlock a lockout; the
user waits or resets the password via the reset email.

## Two-factor authentication (2FA)

2FA is optional for personal accounts and required when the workspace has
enabled "require 2FA for admins". TOTP codes come from an authenticator app.
If a user loses their device, an Owner can clear 2FA from the Admin panel
so the user can re-enroll on next sign-in.

## SAML Single Sign-On

Owner or Admin enables SAML under Settings → Security. Team members who sign
in via SAML are role-mapped from the Identity Provider's group claims.
Forcing SAML disables password login for members (except the Owner fallback).

## Session behaviour

- Sessions are bound to the browser. Signing in elsewhere does not revoke the
  existing session.
- Idle sessions are closed after 24 hours; Administrators can force-logout
  all sessions under Security → Sessions page. Choose a valid one.