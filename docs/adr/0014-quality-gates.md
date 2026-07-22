# ADR-0014: Mandatory Quality Gates

- Status: Accepted
- Date: 2026-07-21

## Decision

Every change must pass Ruff, Mypy strict mode, and Pytest. Critical authorization, ownership, idempotency, accounting, and state-transition paths require unit and integration tests. CI must also scan for secrets and validate migrations.

All repository content and commit messages must be in English. Every commit subject must include the eagle emoji `🦅` and at least one additional emoji related to the change.

## Consequences

- Higher initial implementation effort.
- Fewer regressions in a system with expensive external effects.
- External adapters are tested through contracts, fake servers, and controlled opt-in real-provider tests.
