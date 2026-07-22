# ADR-0010: Idempotency, Leases, and Transactional Outbox

- Status: Accepted
- Date: 2026-07-21

## Context

Telegram may redeliver updates, workers may crash after external effects, and generation may incur cost. Duplicate execution is unacceptable.

## Decision

- Store Telegram `update_id` uniquely.
- Use a unique request idempotency key.
- Persist provider-operation intent and remote identifiers around external effects.
- Claim jobs through recoverable leases.
- Create integration events and notification work through a transactional outbox or equivalent durable record.
- Use database constraints as the final duplicate barrier.

## Consequences

- Workflows are more explicit and somewhat more complex.
- Common retry and crash scenarios avoid duplicate business effects.
- A reconciler is required for ambiguous provider states.
