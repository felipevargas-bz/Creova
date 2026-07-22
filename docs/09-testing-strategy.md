# Testing Strategy

## 1. Test pyramid

### Unit tests

Domain and application behavior without database or network:

- active, expired, suspended, and revoked grants;
- role and ownership rules;
- request and job state transitions;
- quotas, reservations, and budgets;
- retry and backoff calculations;
- image specification and provider-selection normalization;
- error classification and redaction;
- short-ID generation and parsing;
- callback validation;
- retention calculations.

### Integration tests

Use real PostgreSQL and MinIO or another S3-compatible service through containers:

- migrations and downgrade where supported;
- uniqueness and idempotency constraints;
- concurrent `SKIP LOCKED` claims;
- lease expiration and recovery;
- atomic quota reservation;
- append-only ledger and audit behavior;
- object upload, streaming, digest, metadata, and deletion;
- outbox and notification retries.

SQLite must not replace PostgreSQL tests for locking, JSONB, transaction, or constraint behavior.

### Contract tests

- Telegram update parsing and callback payload versions;
- current provider adapter requests and responses against a fake HTTP server or recorded sanitized fixtures;
- S3-compatible adapter behavior;
- event compatibility for `content.ready.v1`;
- safe mapping of provider errors.

### End-to-end tests

Use a staging bot with a private allowlist and fake provider. Keep real-provider tests opt-in, explicitly budgeted, and disabled by default.

## 2. Mandatory critical scenarios

1. Unknown user attempts `/image`.
2. Known username with a different numeric ID attempts access.
3. Authorized user sends a command from a group.
4. Same Telegram `update_id` arrives twice.
5. Same confirmation callback is submitted twice.
6. Two workers attempt to claim the same job.
7. Worker dies after claim and before completion.
8. Provider creates an operation but the response times out before persistence.
9. A generated result exceeds direct Telegram delivery limits.
10. Cancellation occurs before submission, during processing, after completion, and when unsupported.
11. Concurrent requests compete for the final quota or budget capacity.
12. Asset expires while the user requests a signed link.
13. Webhook secret is absent or incorrect.
14. Provider error contains sensitive data and must be redacted.
15. Notification fails after successful generation.
16. Storage upload succeeds but database completion transaction fails.
17. Database restore creates an asset reconciliation mismatch.
18. A user tries to access another user's short ID.

## 3. Quality gates

- Ruff passes with no errors.
- Mypy strict mode passes for `src`.
- Full Pytest suite passes.
- Initial coverage target: 85% for domain and application layers.
- Critical authorization and state-transition branches target 100% coverage.
- Secret scanning runs in CI.
- Dependency vulnerability review runs in CI or release workflow.
- Dependencies are pinned in a lockfile when implementation begins.
- English-language repository policy is checked with a documented allowlist for proper nouns and official fields.

## 4. Required fakes

- `FakeClock`
- `FakeIdGenerator`
- `InMemoryAccessRepository`
- `FakeImageProvider`
- `FakeVideoProvider`
- `InMemoryObjectStorage`
- `FakeTelegramNotifier`
- `FakeCostEstimator`

Fakes must model:

- transient failure;
- permanent failure;
- policy rejection;
- delayed remote operations;
- ambiguous external effects;
- cancellation supported and unsupported;
- large streamed output;
- notification rate limiting.

## 5. Property and concurrency testing

Where valuable, test invariants across generated sequences:

- no terminal job returns to executable state;
- reservations never settle more than once;
- duplicate idempotency keys produce one business object;
- claims are exclusive while a lease is valid;
- ownership filtering cannot be bypassed by short-ID collision or callback data.

Concurrency tests must use barriers or controlled synchronization rather than timing-only sleeps whenever possible.

## 6. Real-provider tests

- Disabled by default.
- Require an explicit environment flag.
- Use a dedicated low-budget account or project.
- Generate the smallest acceptable artifact.
- Never run automatically on untrusted pull requests.
- Record only sanitized metadata.
- Verify official API documentation before updating fixtures.

## Provider and assisted-conversation tests

Add tests proving that Nano Banana and ChatGPT can be both assistants and renderers, Claude can be an assistant but never a renderer, missing optional keys disable only the affected provider, no generation occurs before explicit confirmation, stale callbacks are rejected, question limits are enforced, `Review now` and `Use your best judgment` terminate questioning, and every successful delivery includes the future-publishing notice.

Add secret-scanning tests or CI checks using fake token patterns only. Never place the previously exposed token in a test corpus.
