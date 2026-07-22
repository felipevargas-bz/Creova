# ADR-0013: Command and Wizard UX with Explicit Confirmation

- Status: Accepted
- Date: 2026-07-21

## Context

The chat should feel simple, but unrestricted LLM interpretation could trigger ambiguous and expensive actions.

## Decision

Use structured commands and a button-based wizard. Free text may start the wizard but must not automatically create a billable generation. Video always requires confirmation. Image confirmation follows configurable policy.

## Consequences

- Predictable and testable user experience.
- Lower prompt-injection risk in system control paths.
- More interaction steps than fully automatic generation.
