# ADR-0007: PostgreSQL as the System of Record

- Status: Accepted
- Date: 2026-07-21

## Context

Creova requires relations, constraints, transactions, flexible logical parameters, concurrent locking, append-only accounting, and durable idempotency.

## Decision

PostgreSQL stores identity, access grants, drafts, requests, jobs, provider operations, asset metadata, usage ledger, notifications, audit records, and outbox events. Binary assets are not stored in the database.

## Consequences

- Database constraints protect idempotency and key invariants.
- Alembic migrations, backups, restore tests, and monitoring are required.
- JSONB is reserved for flexible normalized data; frequently queried fields remain typed columns.
