# Input, Output, and Event Contracts

## 1. HTTP surface

The MVP exposes no public business API.

### `POST /telegram/webhook`

Purpose: receive Telegram updates.

Requirements:

- production-only webhook runtime mode;
- valid Telegram secret header;
- JSON content type and configured body-size limit;
- fast response after validation, deduplication, authorization, and durable acceptance;
- no generation work in the request lifecycle.

Typical responses:

- `200`: accepted or safely deduplicated;
- `400`: malformed update;
- `401` or `403`: invalid webhook secret according to the chosen policy;
- `413`: body too large;
- `415`: unsupported content type;
- `503`: critical dependency prevents safe durable acceptance.

Responses must not expose stack traces or internal configuration.

### `GET /health/live`

Confirms that the process is running. It does not call external dependencies.

### `GET /health/ready`

Checks minimum configuration and essential connectivity required to accept work safely. It returns a compact safe result without credentials or topology details.

### `GET /metrics`

Available only on an internal network or behind infrastructure authorization. Format depends on the selected observability stack.

## 2. Application commands

- `AuthorizeTelegramUser`
- `RecordTelegramUpdate`
- `CreateGenerationDraft`
- `UpdateGenerationDraft`
- `ConfirmGenerationRequest`
- `CancelGenerationRequest`
- `GetGenerationStatus`
- `ListUserHistory`
- `GetOwnedAsset`
- `ClaimGenerationJob`
- `ExecuteGenerationJob`
- `ReconcileProviderOperation`
- `StoreGeneratedAsset`
- `DeliverGeneratedAsset`
- `ExpireAssets`
- `GrantAccess`
- `SuspendAccess`
- `RevokeAccess`
- `SetAccessLimits`

Every command has a typed DTO, explicit authorization context, known error categories, and idempotency expectations.

## 3. Application queries

Queries must not mutate business state except for explicitly documented access metadata such as `last_seen_at`.

- `GetCurrentAccess`
- `GetRequestStatus`
- `ListOwnedRequests`
- `GetOwnedAssetMetadata`
- `ListAccessGrants`
- `GetUsageSummary`

## 4. Integration events

### `generation.requested.v1`

Emitted when a request is durably accepted.

```json
{
  "event_id": "uuid",
  "request_id": "uuid",
  "owner_user_id": "uuid",
  "kind": "image",
  "occurred_at": "2026-07-21T23:00:00Z"
}
```

### `generation.completed.v1`

Represents technical success before or together with an available generated asset.

```json
{
  "event_id": "uuid",
  "request_id": "uuid",
  "job_id": "uuid",
  "asset_ids": ["uuid"],
  "occurred_at": "2026-07-21T23:05:00Z"
}
```

### `generation.failed.v1`

Contains a stable safe category, not a raw provider response.

```json
{
  "event_id": "uuid",
  "request_id": "uuid",
  "job_id": "uuid",
  "error_category": "provider_transient",
  "support_code": "CRV-ABC123",
  "occurred_at": "2026-07-21T23:05:00Z"
}
```

### `content.ready.v1`

Reserved contract for future consumers:

```json
{
  "event_id": "uuid",
  "asset_id": "uuid",
  "request_id": "uuid",
  "owner_user_id": "uuid",
  "content_type": "image",
  "mime_type": "image/png",
  "storage_reference": "internal://asset/uuid",
  "created_at": "2026-07-21T23:05:00Z"
}
```

It contains no public URL, provider credential, social-account data, or Telegram token. A future publisher resolves the internal reference under its own authorization.

### `access.changed.v1`

Optional future integration event for security operations. It must not disclose more identity data than necessary.

## 5. Event envelope rules

Every integration event should include:

- `event_id`;
- event type and version;
- occurrence timestamp in UTC;
- aggregate type and ID;
- correlation ID;
- causation ID when available;
- payload with non-sensitive data only.

## 6. Versioning

- Integration event names end in `.v1`, `.v2`, and so on.
- Backward-compatible additive fields may remain in the same version.
- Semantic changes, removed fields, changed meaning, or changed required behavior require a new version.
- Internal DTOs may evolve without public compatibility promises, but migrations and tests must preserve deployed behavior.
- Consumers must ignore unknown additive fields.

## 7. Error taxonomy

Stable application categories:

- `unauthorized`
- `forbidden`
- `not_found`
- `invalid_input`
- `quota_exceeded`
- `budget_exceeded`
- `conflict`
- `provider_policy`
- `provider_transient`
- `provider_permanent`
- `ambiguous_external_effect`
- `storage_failure`
- `delivery_failure`
- `cancelled`
- `internal`

User-facing messages map from these categories and never expose raw exceptions.
