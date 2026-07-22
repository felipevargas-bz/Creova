# ADR-0011: External Secrets, Minimal Logging, and Configurable Retention

- Status: Accepted
- Date: 2026-07-21

## Decision

- Load secrets from environment injection or a secret manager.
- Never place secrets in the database, repository, logs, or chat.
- Use structured logs without full prompts by default.
- Keep object storage private and signed URLs short-lived.
- Start with configurable retention of 30 days for assets, 90 days for request metadata, and 180 days for audit records.
- Audit administrative actions.

## Trade-off

Minimal content in logs can make diagnosis harder. Compensate with correlation IDs, hashes, lengths, normalized error codes, metrics, and controlled support procedures.
