# Definition of Done

A story or implementation prompt is complete only when every applicable item below is satisfied.

## Functional behavior

- Acceptance criteria are met.
- Happy path and known error paths are implemented.
- Authorization, role, and ownership checks are explicit.
- Expensive and externally visible actions are idempotent.
- User-facing messages are clear, truthful, safe, and written in English.
- Deferred social publishing remains outside the MVP.

## Code quality

- Layer boundaries and dependency direction are respected.
- Application and domain code are fully typed.
- Business rules are not duplicated in Telegram or HTTP handlers.
- No production secrets or environment-specific values are committed.
- State changes use approved domain or application methods.
- Source code, comments, docstrings, identifiers, logs, and exceptions are written in English.
- No ambiguous `TODO` remains.

## Commit quality

- Commit messages are written in English.
- Every commit subject contains the eagle emoji `🦅`.
- Every commit subject contains at least one additional emoji related to the change.
- Subjects are imperative and describe the real change.
- Example: `🔒 🦅 Enforce owner checks for asset links`.

## Data

- Required migration and reasonable downgrade are included.
- Indexes and constraints represent important invariants.
- Timestamps use UTC semantics.
- Retention and deletion behavior are considered.
- No signed URL is persisted as a durable asset reference.
- Migration compatibility and rollback implications are documented.

## Tests

- Unit tests cover rules and state transitions.
- Integration tests cover relevant persistence and external-effect boundaries.
- A bug fix includes a regression test.
- Concurrency behavior is tested where correctness depends on locking or reservations.
- `make check` passes.

## Security and privacy

- Inputs and external payloads are validated.
- Logs and errors are redacted.
- Secret handling follows policy.
- Horizontal authorization is tested.
- Cost-abuse controls are enforced.
- Threat model and security documentation are updated when the attack surface changes.

## Operations

- Structured logs and metrics exist for the new flow.
- Failures map to stable categories.
- Configuration is documented and validated.
- A feature flag, rollback path, or recovery plan is considered.
- Background tasks are idempotent and observable.

## Documentation

- README and affected design documents are updated.
- A new or superseding ADR exists when a significant decision changes.
- Evidence of completed checks is included in the pull request or commit history.

## Assisted image completion conditions

The MVP is not done until the three creative assistant choices work when configured, Claude requires a valid renderer handoff, the final brief and optimized prompt are visible before confirmation, confirmation is durable and idempotent, generation cannot be triggered from free text or a stale callback, provider credentials are redacted, and the successful result message includes the future-publishing notice.
