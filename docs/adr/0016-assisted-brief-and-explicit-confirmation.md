# ADR-0016: Assisted Brief Refinement and Explicit Confirmation

- Status: Accepted
- Date: 2026-07-21

## Context

Generating immediately from a short prompt can waste budget and miss the user's intent. A fixed questionnaire creates unnecessary friction.

## Decision

Use a durable adaptive conversation that extracts a structured creative brief, asks one high-impact question at a time, stops according to application-owned policy, shows the final brief and optimized prompt, and requires explicit versioned confirmation before creating a billable job.

## Consequences

- The user retains control over the final request.
- Prompt quality improves without forcing every field.
- Conversation and question policy require durable state and tests.
- Confirmation becomes an idempotent security and budget boundary.
