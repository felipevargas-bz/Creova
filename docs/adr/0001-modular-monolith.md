# ADR-0001: Modular Monolith with Hexagonal Architecture

- Status: Accepted
- Date: 2026-07-21

## Context

Creova must receive Telegram messages, persist requests, execute durable jobs, store assets, and communicate with external providers. The initial team and expected load do not justify microservices, but the code must not become coupled to Telegram or a specific AI provider.

## Considered options

1. Single bot script.
2. Modular monolith with layers and ports.
3. Microservices from the beginning.

## Decision

Use a modular monolith with domain, application, infrastructure, and presentation boundaries. The same deployable artifact may run as `api`, `polling`, `worker`, or `admin` process roles.

## Positive consequences

- Simple development and deployment.
- Local transactions for request, quota, ledger, and job creation.
- Clear internal boundaries that can later be extracted.
- Less distributed infrastructure and fewer failure modes.

## Negative consequences

- Requires discipline to prevent cross-layer dependencies.
- Scaling occurs by process role rather than fully independent services.

## Review criteria

Reconsider only when a module demonstrates sustained independent scaling, security, availability, ownership, or release-cycle needs.
