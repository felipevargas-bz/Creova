# ADR-0005: Webhook in Production and Long Polling Locally

- Status: Accepted
- Date: 2026-07-21

## Context

Telegram offers webhook delivery and `getUpdates` as mutually exclusive modes. Production benefits from HTTPS webhook delivery and horizontal API scaling, while local development benefits from simple polling.

## Decision

- Production uses an HTTPS webhook and validates `X-Telegram-Bot-Api-Secret-Token`.
- Local development may use long polling.
- Both modes must never run for the same bot simultaneously.

## Consequences

- Scripts or CLI commands are required to configure, inspect, and remove the webhook.
- Runtime mode is controlled by validated configuration.
- Deduplication by `update_id` applies to both modes.
