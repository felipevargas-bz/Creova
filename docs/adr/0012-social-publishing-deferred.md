# ADR-0012: Social Publishing Deferred to a Future Bounded Context

- Status: Accepted
- Date: 2026-07-21

## Context

The product vision includes publishing generated content, but the MVP must generate and deliver content only.

## Decision

Do not include social-network SDKs, tokens, tables, commands, or publishing logic. The generation module emits `content.ready.v1` through the outbox. A future publisher consumes that internal reference under a separate credential and domain boundary.

## Positive consequences

- Controlled MVP scope.
- Smaller security and privacy surface.
- Generation availability does not depend on social APIs.

## Negative consequences

- The initial flow ends with manual delivery or download.
- Approval, platform variants, schedules, and social credentials require later design.
