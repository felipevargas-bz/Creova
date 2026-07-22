# Security and Privacy

## 1. Objectives

- Prevent unauthorized use and cost abuse.
- Protect bot tokens, provider keys, storage credentials, and generated assets.
- Minimize stored personal data and sensitive content.
- Preserve accountability for administrative actions.
- Limit the blast radius of a compromised component or provider.
- Keep authorization decisions deterministic and independent from usernames.

## 2. Access model

1. Extract `from_user.id` from the Telegram update.
2. Reject the update when identity is missing or the chat is not private.
3. Load an effective access grant by numeric Telegram ID.
4. Apply role, validity window, suspension, revocation, and limits.
5. Verify resource ownership inside every use case.
6. Record sensitive access mutations and denied administrative attempts.

A Telegram username may change or be reassigned and therefore never grants access.

## 3. Allowlist

The allowlist is stored in PostgreSQL. Environment bootstrap exists only to create the first administrator or recover controlled operational access.

Administrative actions:

- `grant`: create a new grant with actor and reason;
- `suspend`: temporarily block access;
- `revoke`: permanently invalidate a grant;
- `expire`: end access through a validity date;
- `set-limits`: change user-specific quotas and budgets.

Each mutation creates an append-only audit event. Revoked grants are not reactivated; a new grant is created instead.

## 4. Roles and least privilege

- `user`: operate only owned generation resources.
- `admin`: manage grants, limits, and policy settings through protected operational interfaces.
- `operator`: perform deployment, recovery, and diagnostics without receiving unrestricted content access by default.

Role checks do not replace ownership checks. Administrative capabilities should be narrowly defined rather than represented as unrestricted database access in application code.

## 5. Secrets

Minimum secret set:

- Telegram bot token;
- Telegram webhook secret;
- AI-provider API key;
- database credentials;
- object-storage credentials;
- optional telemetry credentials.

Rules:

- never include secrets in container images, build arguments, source control, examples, screenshots, or logs;
- use separate secrets per environment;
- rotate after suspected exposure or personnel changes;
- do not expose values through `/whoami`, health checks, exception messages, or metrics;
- prefer workload identity and short-lived credentials when supported;
- prevent accidental serialization of settings objects containing secret fields.

## 6. Webhook security

- Require HTTPS in production.
- Validate `X-Telegram-Bot-Api-Secret-Token` with constant-time comparison.
- Enforce `Content-Type: application/json` and a configured body-size limit.
- Reject malformed payloads safely.
- Keep processing time short.
- Deduplicate with unique `update_id`.
- Restrict `allowed_updates` initially to `message` and `callback_query`.
- Keep health endpoints separate from the webhook route.
- Do not assume IP allowlisting is sufficient by itself.

## 7. Input and file security

- Enforce prompt length and parameter limits before persistence and provider calls.
- Restrict callback payload versions and sizes.
- Accept reference files only from trusted Telegram file identifiers in the first file-enabled phase.
- Do not fetch arbitrary user-provided URLs.
- Download with byte, time, redirect, and host restrictions.
- Detect MIME type from content rather than filename alone.
- Quarantine unverified files.
- Reject executable or unsupported formats.
- Strip metadata when policy requires it.
- Use streaming to avoid loading large generated images into memory.

## 8. Initial retention baseline

Configurable starting point:

- generated assets: 30 days;
- request and job metadata: 90 days;
- audit events: 180 days;
- full prompts: the shortest period compatible with support and product needs;
- temporary drafts and failed downloads: hours or a small number of days.

Before regulated or external-customer use, legal and business owners must approve retention, deletion, export, and incident-notification obligations.

## 9. Safe logging

Allowed when operationally necessary:

- internal correlation IDs;
- pseudonymized or partially redacted Telegram ID;
- content kind;
- state and transition;
- duration and retry count;
- normalized error code;
- prompt hash and length;
- byte size and digest of stored assets.

Prohibited by default:

- Telegram bot token;
- provider or storage keys;
- full prompt;
- binary or base64 content;
- signed URLs;
- raw provider response;
- authorization headers;
- database connection strings;
- unredacted personal metadata not required for diagnosis.

## 10. Cost protection

- Per-user quota by content type.
- Per-user and global concurrency limits.
- Daily or rolling user budget.
- Global provider budget.
- Atomic reservation before queueing.
- Settlement against actual cost when available.
- Release of abandoned reservations.
- Provider circuit breaker and kill switches.
- Optional automatic suspension for anomalous usage patterns.
- Keep video-specific policies deferred until the video phase.

## 11. Encryption and transport

- Use TLS for Telegram webhook, database, object storage, and provider traffic in production.
- Use server-side object-storage encryption where available.
- Consider field-level encryption for prompts only when the operational and key-management model is clear.
- Never treat hashing as encryption.
- Keep encryption keys outside the application database.

## 12. Incident response

Minimum response procedure:

1. pause affected generation paths when cost or data exposure is possible;
2. revoke or rotate affected credentials;
3. preserve audit events, correlation identifiers, and relevant immutable logs;
4. identify the exposure window and affected resources;
5. invalidate temporary access through TTL, key rotation, or credential revocation;
6. restore from known-good configuration or artifacts;
7. notify stakeholders according to applicable obligations;
8. document root cause, impact, containment, and preventive actions.

## 13. Privacy boundaries

- Telegram necessarily receives content transmitted through the bot channel.
- The AI provider receives the inputs required for generation.
- Object storage retains generated binaries until policy deletion.
- Operators should diagnose through metadata whenever possible.
- A future social publisher must have its own privacy review and credential boundary.

## Credential incident and provider-key policy

The Telegram token previously shared in a conversation must be considered compromised and rotated before use. The repository records only the public username `FeloCreova_bot` and secret variable names. Real Telegram, Google, OpenAI, and Anthropic credentials must never enter documentation, prompts, source code, fixtures, logs, commits, or database rows.

Provider availability may be exposed as safe booleans or health states. Secret values, prefixes, lengths, hashes, and raw authentication failures must not be exposed to users. Full prompts are excluded from logs by default and access to stored prompt content is auditable.
