# ADR-0004: Allowlist by Numeric Telegram User ID with Default Denial

- Status: Accepted
- Date: 2026-07-21

## Context

The bot must remain private. Telegram usernames are mutable and may be reassigned, so they are not stable identities.

## Decision

Authorize with `from_user.id` stored as a signed 64-bit integer. Deny every user unless an effective grant exists. The MVP accepts only private chats. Grants are managed through a protected CLI and every mutation is audited.

## Positive consequences

- Stable identity and lower impersonation risk.
- Clear per-user policy, quota, and ownership checks.
- Deterministic authorization independent from display metadata.

## Negative consequences

- Administrators must obtain the numeric ID.
- Bootstrap and operational recovery procedures are required.

## Mitigations

`/start` and `/whoami` may show the user's own ID safely. A controlled environment bootstrap creates the first administrator and then synchronizes authorization into PostgreSQL.
