# ADR-0006: Durable PostgreSQL Job Queue

- Status: Accepted
- Date: 2026-07-21

## Context

Image generation can take significant time. Creova needs durable processing, but adding Redis and a separate broker would increase operational complexity for the initial scale.

## Considered options

1. In-memory background tasks.
2. Redis and Celery or another broker.
3. PostgreSQL job table with leases.

## Decision

Use PostgreSQL with `FOR UPDATE SKIP LOCKED`, expiring leases, `next_attempt_at`, bounded backoff, and reconciliation.

## Positive consequences

- Job persistence and atomic creation with the request and usage reservation.
- Fewer infrastructure components.
- Multiple workers can claim work safely.

## Negative consequences

- Claim, retry, and reconciliation logic must be implemented carefully.
- This design is not intended for extremely high queue throughput.

## Review criteria

Evaluate a dedicated broker only when measured queue load, latency, or PostgreSQL pressure justifies the additional system.
