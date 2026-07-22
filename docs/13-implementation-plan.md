# Implementation Plan

Execute the milestones in order. Each implementation phase must finish with tests, documentation updates, and an English commit subject containing `🦅` plus a relevant emoji.

## Milestones

1. Audit the foundation and verify secret-safe configuration.
2. Complete configuration, secret redaction, provider availability, and composition root.
3. Add PostgreSQL schema and migrations for access, conversations, briefs, requests, jobs, assets, usage, and audit records.
4. Complete allowlist CLI and Telegram private-chat transport.
5. Implement provider capability registry.
6. Implement durable conversation and adaptive brief policy.
7. Add prompt-assistant adapters for Gemini, OpenAI, and Anthropic.
8. Add Nano Banana and OpenAI image renderers.
9. Add explicit confirmation, durable queue, worker, storage, and delivery.
10. Add history, cancellation, quotas, budgets, reconciliation, observability, security hardening, CI, and release validation.

## Mandatory product checks

- Free text cannot trigger generation.
- A stale callback cannot confirm a newer or older draft.
- Claude cannot be persisted as renderer.
- Provider menus reflect configured availability.
- Missing secrets are never printed.
- Every successful delivery includes the future-publishing notice.
- No social SDK or credential appears in runtime dependencies.
