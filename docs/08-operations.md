# Operations and Deployment

## 1. Processes

- `creova-api`: FastAPI plus Telegram dispatcher in webhook mode.
- `creova-bot`: Telegram long polling for local development only.
- `creova-worker`: generation execution, remote-operation polling, storage, delivery, reconciliation, and maintenance.
- `creova-admin`: protected CLI for allowlist and controlled operational actions.

Webhook and long polling must not run against the same bot at the same time.

## 2. Health checks

### Liveness

Fails only when the process cannot continue its event loop or serve basic requests.

### Readiness

Checks:

- valid configuration;
- PostgreSQL connectivity;
- migration compatibility or required schema state;
- object-storage connectivity when the process needs it;
- bot initialization requirements;
- worker ability to claim jobs when relevant.

Temporary AI-provider unavailability does not necessarily remove API readiness. It should instead pause or retry generation through policy.

## 3. Configuration

Configuration is environment-driven and validated at startup. Important groups:

- application environment and log level;
- Telegram token, webhook URL, webhook secret, and runtime mode;
- PostgreSQL URL and pool settings;
- object-storage endpoint, bucket, region, and credentials;
- provider credentials, models, timeouts, and capability settings;
- worker concurrency, lease duration, polling intervals, and retry limits;
- quotas, budgets, retention, and feature flags;
- observability endpoints and sampling.

Production startup must fail fast when required settings are missing or contradictory.

## 4. Observability

### Structured logs

Include safe fields such as:

- timestamp;
- level;
- service and process role;
- environment;
- correlation ID;
- request, job, operation, or asset ID;
- normalized event name;
- normalized error category;
- duration.

### Metrics

Recommended metrics:

- webhook request count and latency;
- rejected webhook requests;
- authorization denials;
- duplicate Telegram updates;
- queue depth and oldest-job age;
- claims, lease expirations, retries, and terminal failures;
- provider latency and error rate by safe category;
- asset upload duration and bytes;
- delivery success and retries;
- reservations, charges, releases, and estimated spend;
- cleanup backlog and orphan counts.

### Alerts

Initial alerts:

- sustained webhook failure;
- readiness failure;
- queue age above threshold;
- repeated lease expiration;
- provider error spike;
- storage failure spike;
- budget threshold reached;
- cleanup backlog growth;
- failed backup or restore test.

## 5. Backups and recovery

- PostgreSQL: daily backups and point-in-time recovery when supported.
- Object storage: lifecycle policy and optional versioning according to cost and privacy needs.
- Test restoration periodically, not only backup creation.
- Keep application secrets outside application backups.
- Document recovery point objective and recovery time objective before production use.
- Reconcile database asset metadata against object storage after restore.

## 6. Safe deployment sequence

1. Run tests, linting, type checks, dependency review, and secret scanning.
2. Build a reproducible image.
3. Apply backward-compatible migrations.
4. Deploy API instances.
5. Deploy workers.
6. Configure or verify the Telegram webhook.
7. Verify readiness and run an authorized smoke test with a fake provider when possible.
8. Observe error rate, queue behavior, and budget metrics.

## 7. Rollback

- Use expand-and-contract migrations.
- Avoid destructive schema changes in the same release that stops reading old fields.
- Keep feature flags for each provider, each renderer, and the global generation pause.
- Roll back application code only when the deployed schema remains compatible.
- Do not retry ambiguous provider effects blindly during rollback.

## 8. Periodic tasks

- recover expired leases;
- resume or reconcile remote operations;
- retry notifications;
- release orphaned reservations;
- expire and delete assets;
- purge metadata according to retention;
- publish or retry outbox events;
- reconcile estimated and actual cost;
- find database/object-storage orphans;
- refresh safe operational summaries.

Each maintenance task must be idempotent and observable.

## 9. Runbook: provider outage

1. Confirm provider-specific errors and scope.
2. Enable provider or content-type pause if continued calls create cost or noise.
3. Keep accepted jobs durable.
4. Retry only errors classified as safe and transient.
5. Communicate truthful status to users.
6. Resume gradually and watch queue age and budget.

## 10. Runbook: suspected credential exposure

1. Pause affected operations.
2. Rotate the credential immediately.
3. Review audit and provider usage for the exposure window.
4. Replace secrets in the deployment platform.
5. Restart or roll workloads safely.
6. Verify no secret remains in logs, artifacts, CI output, or chat history.
7. Document the incident and preventive controls.

## 11. Runbook: worker crash loop

1. Stop repeated claims if leases are cycling rapidly.
2. Inspect normalized errors and the oldest affected job.
3. Confirm database and storage availability.
4. Disable the affected provider or content kind when necessary.
5. Deploy a fix or configuration correction.
6. Allow lease recovery and verify no duplicate external operation occurred.

## 12. Operational ownership

Before production, assign owners for:

- provider budget and keys;
- Telegram bot configuration;
- database backups and restores;
- object-storage lifecycle;
- incident response;
- security review;
- retention approval;
- release and rollback authority.
