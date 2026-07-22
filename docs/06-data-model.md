# Data Model

## 1. General conventions

- Use UUID primary keys for internal entities.
- Store Telegram IDs as `BIGINT`, never 32-bit `INT`.
- Use `TIMESTAMPTZ` and UTC semantics.
- Use `NUMERIC` for money and cost values.
- Use normalized text states with application validation and selected database `CHECK` constraints.
- Keep raw provider payloads out of general-purpose JSON fields unless explicitly redacted and justified.

## 2. Main tables

### `users`

- `id UUID PRIMARY KEY`
- `telegram_user_id BIGINT UNIQUE NOT NULL`
- `telegram_username TEXT NULL`
- `display_name TEXT NULL`
- `timezone TEXT NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`
- `last_seen_at TIMESTAMPTZ NULL`

The username and display name are informational only.

### `access_grants`

- `id UUID PRIMARY KEY`
- `user_id UUID NOT NULL REFERENCES users(id)`
- `role TEXT NOT NULL`
- `status TEXT NOT NULL`
- `valid_from TIMESTAMPTZ NOT NULL`
- `valid_until TIMESTAMPTZ NULL`
- `limits JSONB NOT NULL DEFAULT '{}'`
- `reason TEXT NOT NULL`
- `created_by UUID NULL REFERENCES users(id)`
- `created_at TIMESTAMPTZ NOT NULL`
- `revoked_at TIMESTAMPTZ NULL`

Recommended indexes:

- `(user_id, status, valid_from, valid_until)`;
- partial or exclusion strategy to prevent conflicting effective grants when appropriate.

### `conversation_drafts`

- `id UUID PRIMARY KEY`
- `user_id UUID NOT NULL REFERENCES users(id)`
- `chat_id BIGINT NOT NULL`
- `kind TEXT NULL`
- `step TEXT NOT NULL`
- `data JSONB NOT NULL`
- `version INTEGER NOT NULL`
- `expires_at TIMESTAMPTZ NOT NULL`
- `created_at`, `updated_at`

Only one current draft per user and chat should be effective unless product requirements change.

### `generation_requests`

- `id UUID PRIMARY KEY`
- `short_id TEXT UNIQUE NOT NULL`
- `user_id UUID NOT NULL REFERENCES users(id)`
- `kind TEXT NOT NULL`
- `prompt TEXT NOT NULL`
- `prompt_hash TEXT NOT NULL`
- `parameters JSONB NOT NULL`
- `status TEXT NOT NULL`
- `source_chat_id BIGINT NOT NULL`
- `source_message_id BIGINT NULL`
- `idempotency_key TEXT UNIQUE NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- `confirmed_at TIMESTAMPTZ NULL`
- `completed_at TIMESTAMPTZ NULL`

Recommended indexes:

- `(user_id, created_at DESC)`;
- `(status, created_at)`;
- unique `short_id` and `idempotency_key`.

### `generation_jobs`

- `id UUID PRIMARY KEY`
- `request_id UUID UNIQUE NOT NULL REFERENCES generation_requests(id)`
- `job_type TEXT NOT NULL`
- `status TEXT NOT NULL`
- `priority SMALLINT NOT NULL DEFAULT 100`
- `attempt_count INTEGER NOT NULL DEFAULT 0`
- `max_attempts INTEGER NOT NULL`
- `next_attempt_at TIMESTAMPTZ NOT NULL`
- `lease_owner TEXT NULL`
- `lease_expires_at TIMESTAMPTZ NULL`
- `cancel_requested_at TIMESTAMPTZ NULL`
- `last_error_code TEXT NULL`
- `last_error_safe_message TEXT NULL`
- `created_at`, `updated_at`, `started_at`, `finished_at`

Claim index:

`(status, next_attempt_at, priority, created_at)`.

Database constraints should prevent impossible combinations, such as a lease owner without a lease expiration when the state is `leased`.

### `provider_operations`

- `id UUID PRIMARY KEY`
- `job_id UUID NOT NULL REFERENCES generation_jobs(id)`
- `provider TEXT NOT NULL`
- `provider_operation_id TEXT NULL`
- `model TEXT NOT NULL`
- `status TEXT NOT NULL`
- `idempotency_key TEXT UNIQUE NOT NULL`
- `request_fingerprint TEXT NOT NULL`
- `estimated_cost_usd NUMERIC(18, 8) NOT NULL DEFAULT 0`
- `actual_cost_usd NUMERIC(18, 8) NULL`
- `metadata JSONB NOT NULL DEFAULT '{}'`
- `created_at`, `updated_at`, `submitted_at`, `completed_at`

Recommended uniqueness:

- provider operation ID unique within provider when non-null;
- one active primary operation per job unless an explicit retry-generation design is approved.

### `generated_assets`

- `id UUID PRIMARY KEY`
- `request_id UUID NOT NULL REFERENCES generation_requests(id)`
- `provider_operation_id UUID NULL REFERENCES provider_operations(id)`
- `storage_key TEXT UNIQUE NOT NULL`
- `mime_type TEXT NOT NULL`
- `size_bytes BIGINT NOT NULL`
- `sha256 TEXT NOT NULL`
- `width INTEGER NULL`
- `height INTEGER NULL`
- `duration_ms BIGINT NULL`
- `status TEXT NOT NULL`
- `retention_until TIMESTAMPTZ NOT NULL`
- `created_at`, `updated_at`, `deleted_at`

Signed URLs are never stored as durable asset fields.

### `processed_telegram_updates`

- `update_id BIGINT PRIMARY KEY`
- `payload_hash TEXT NULL`
- `received_at TIMESTAMPTZ NOT NULL`
- `processed_at TIMESTAMPTZ NULL`
- `status TEXT NOT NULL`
- `result_code TEXT NULL`
- `request_id UUID NULL REFERENCES generation_requests(id)`
- `last_error_code TEXT NULL`

The processing design must define how failed updates are retried without duplicating accepted business effects.

### `notifications`

- `id UUID PRIMARY KEY`
- `request_id UUID NULL REFERENCES generation_requests(id)`
- `kind TEXT NOT NULL`
- `status TEXT NOT NULL`
- `telegram_chat_id BIGINT NOT NULL`
- `telegram_message_id BIGINT NULL`
- `idempotency_key TEXT UNIQUE NOT NULL`
- `attempt_count INTEGER NOT NULL DEFAULT 0`
- `next_attempt_at TIMESTAMPTZ NOT NULL`
- `last_error_code TEXT NULL`
- `created_at`, `updated_at`, `sent_at`

### `usage_ledger`

- `id UUID PRIMARY KEY`
- `user_id UUID NOT NULL REFERENCES users(id)`
- `request_id UUID NULL REFERENCES generation_requests(id)`
- `entry_type TEXT NOT NULL`
- `amount_usd NUMERIC(18, 8) NOT NULL`
- `units JSONB NOT NULL DEFAULT '{}'`
- `idempotency_key TEXT UNIQUE NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL`

Entry types include `reserve`, `charge`, `release`, and `adjustment`. Ledger entries are append-only.

### `audit_events`

- `id UUID PRIMARY KEY`
- `event_type TEXT NOT NULL`
- `actor_user_id UUID NULL REFERENCES users(id)`
- `subject_type TEXT NOT NULL`
- `subject_id TEXT NOT NULL`
- `correlation_id TEXT NULL`
- `metadata JSONB NOT NULL DEFAULT '{}'`
- `created_at TIMESTAMPTZ NOT NULL`

Audit events are append-only and may be expired only by approved retention policy.

### `outbox_events`

- `id UUID PRIMARY KEY`
- `event_type TEXT NOT NULL`
- `aggregate_type TEXT NOT NULL`
- `aggregate_id UUID NOT NULL`
- `idempotency_key TEXT UNIQUE NOT NULL`
- `payload JSONB NOT NULL`
- `occurred_at TIMESTAMPTZ NOT NULL`
- `published_at TIMESTAMPTZ NULL`
- `attempt_count INTEGER NOT NULL DEFAULT 0`
- `next_attempt_at TIMESTAMPTZ NOT NULL`
- `last_error_code TEXT NULL`

## 3. Important constraints

- Unique Telegram `update_id` and business idempotency keys.
- Unique object-storage key.
- Positive byte sizes, attempts, and configured limits.
- Valid status values through application and selected database checks.
- No persistent signed URLs.
- No mutation of ledger or audit history.
- JSONB contains normalized logical parameters, not unfiltered provider responses.
- User history queries always include `user_id` ownership filtering.

## 4. Acceptance transaction

1. Resolve and lock the relevant quota or budget accounting scope.
2. Verify access, ownership context, concurrency, and available capacity.
3. Create or reuse the generation request by idempotency key.
4. Append usage reservation.
5. Create the job.
6. Create audit and outbox records.
7. Commit.

The provider call occurs only after commit.

## 5. Completion transaction

1. Verify durable provider-operation state.
2. Verify the asset exists and integrity metadata is complete.
3. Insert the generated asset.
4. Mark job and request successful through validated transitions.
5. Settle the usage reservation.
6. Insert notification and `content.ready.v1` outbox records.
7. Commit.

## 6. Migration strategy

- Use Alembic with deterministic revisions.
- Prefer expand-and-contract changes.
- Add nullable or backward-compatible fields before code depends on them.
- Backfill in controlled steps for large tables.
- Remove old fields only after all deployed code stops using them.
- Include a reasonable downgrade for the initial scaffold and non-destructive changes.
