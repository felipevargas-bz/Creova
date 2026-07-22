# ADR-0003: Telegram as the Only MVP User Interface

- Status: Accepted
- Date: 2026-07-21

## Context

The product explicitly requires no custom frontend and should operate through a Telegram bot.

## Decision

Telegram is the only end-user interface for the MVP. HTTP exposes only the Telegram webhook, health endpoints, and protected internal metrics. No SPA, dashboard, mobile application, or public business API is created.

## Positive consequences

- Reduced scope and faster delivery.
- Smaller authentication and security surface.
- One conversational experience to design and test.

## Negative consequences

- User experience is constrained by Telegram capabilities.
- Sensitive administration must use a private CLI.
- Large files may require temporary links.

## Constraint

Adding a custom frontend requires a new ADR, authentication requirements, privacy analysis, and an updated threat model.
