# Threat Model

## 1. Protected assets

- Telegram bot token and webhook secret.
- AI-provider credentials and budget.
- Database and object-storage credentials.
- User prompts and generated assets.
- Allowlist grants and roles.
- Request history, audit trail, and usage ledger.
- Integrity of request, job, provider-operation, asset, and cost state.

## 2. Trust boundaries

- user ↔ Telegram;
- Telegram ↔ Creova webhook;
- API ↔ PostgreSQL;
- worker ↔ AI provider;
- worker ↔ object storage;
- worker ↔ Telegram delivery API;
- operator ↔ CLI and deployment platform;
- future publisher ↔ generation outbox.

## 3. Threats and controls

### T1 — Unauthorized user

**Risk:** provider cost, data access, or system discovery.

**Controls:** deny by default, numeric ID, private chats only, ownership checks, quotas, neutral errors, and auditability.

### T2 — Forged webhook request

**Risk:** invented updates and unauthorized commands.

**Controls:** HTTPS, secret header, constant-time comparison, content-type and body limits, strict parsing, and update deduplication.

### T3 — Redelivery or replay

**Risk:** duplicate generation and duplicate charges.

**Controls:** unique `update_id`, business idempotency keys, durable provider operations, uniqueness constraints, and idempotent notifications.

### T4 — Credential exposure

**Risk:** bot takeover, data access, or uncontrolled provider spend.

**Controls:** secret manager, per-environment credentials, rotation, least privilege, redaction, cost alerts, and emergency kill switches.

### T5 — Abuse by an authorized user

**Risk:** excessive spend, denial of service, or policy violations.

**Controls:** rate limits, quotas, concurrency, budget reservation, confirmation, suspension, circuit breakers, and image-generation limits.

### T6 — Prompt injection against an LLM router

**Risk:** tool misuse, secret extraction, or administrative action.

**Controls:** deterministic command parsing for privileged actions, no secrets in model context, no administrative tools available to a content model, per-request isolation, and server-side validation.

### T7 — Malicious reference file

**Risk:** parser exploit, SSRF, decompression bomb, or storage abuse.

**Controls:** trusted Telegram file IDs, no arbitrary URLs, byte and time limits, MIME detection, quarantine, updated libraries, metadata stripping, and format allowlist.

### T8 — Malicious or malformed provider response

**Risk:** unsafe URL fetch, unexpected metadata, invalid file, or resource exhaustion.

**Controls:** allowlisted provider hosts, bounded redirects, streaming, size and timeout limits, MIME validation, digest verification, and sanitized metadata.

### T9 — Cross-user data leak

**Risk:** `/status`, `/history`, callback data, or signed links expose another user's resource.

**Controls:** every query filters by owner; short IDs are not authorization tokens; signed links require fresh authorization; horizontal-authorization tests are mandatory.

### T10 — Worker race

**Risk:** duplicate external operation.

**Controls:** transactional leases, `SKIP LOCKED`, durable operation intent, provider idempotency where available, uniqueness constraints, and reconciliation of ambiguous effects.

### T11 — Leaked signed URL

**Risk:** temporary third-party asset access.

**Controls:** short TTL, private bucket, no logging, no durable persistence, fresh authorization before generation, and optional revocation through key rotation or object deletion.

### T12 — Incomplete deletion

**Risk:** indefinite retention or privacy-policy violation.

**Controls:** lifecycle rules, idempotent cleanup, `deleting` and `deleted` states, orphan reconciliation, and cleanup backlog metrics.

### T13 — Budget race

**Risk:** concurrent requests exceed configured spend.

**Controls:** database-coordinated reservations, locking or serializable policy where required, idempotent ledger entries, and global pause on threshold breach.

### T14 — Notification confusion

**Risk:** generation succeeds but user receives duplicate, stale, or misleading messages.

**Controls:** notification idempotency keys, independent retry state, message edit throttling, and truth-preserving status mapping.

### T15 — Supply-chain compromise

**Risk:** malicious dependency or build artifact.

**Controls:** lockfile, dependency review, trusted package sources, CI isolation, reproducible builds, vulnerability scanning, secret scanning, and minimal runtime image.

### T16 — Operator misuse

**Risk:** unauthorized grant changes or unnecessary content access.

**Controls:** private CLI, authenticated infrastructure access, least privilege, append-only audit, reason required for mutations, and separation of operator and admin permissions.

## 4. Initially accepted risks

- Dependence on provider availability, policy, and contract changes.
- Telegram can access content transmitted through its channel according to its service model.
- Remote cancellation may be unavailable or too late.
- Retention defaults require legal review before broad commercial use.
- PostgreSQL as a queue is accepted for initial scale and will be revisited only with measured evidence.

## 5. Review triggers

Review this threat model when:

- reference files or arbitrary URLs are introduced;
- a new provider is added;
- social publishing is designed;
- public or multi-tenant access is considered;
- billing is introduced;
- an administrative web interface is proposed;
- retention or regulated data requirements change;
- a security incident reveals a new attack path.

## Additional threats: credential exposure and prompt orchestration

Treat credentials in source control, logs, prompts, screenshots, or build artifacts as immediate account-control and budget-abuse threats. Mitigations include credential rotation, secret-manager injection, repository scanning, log redaction, least-privilege provider keys, spend limits, and provider-specific circuit breakers.

Prompt orchestration introduces risks of malicious instructions embedded in user text or reference images. Provider system prompts must treat user content as creative data, not privileged instructions. Structured output is validated before merging into domain state. The application owns authorization, question limits, provider choice, confirmation, and generation decisions.
