# ADR-0008: S3-Compatible Object Storage for Assets

- Status: Accepted
- Date: 2026-07-21

## Context

Generated images should not inflate PostgreSQL and require private storage, lifecycle policies, streaming upload, and temporary delivery links.

## Decision

Use a private S3-compatible bucket. Use MinIO locally. PostgreSQL stores the object key, digest, MIME type, byte size, dimensions or duration, status, and retention deadline.

## Consequences

- Portability across S3-compatible providers.
- Short-lived signed URLs can deliver files unsuitable for direct Telegram upload.
- Cleanup must reconcile database state and bucket contents.
- The storage SDK remains behind an application port.
