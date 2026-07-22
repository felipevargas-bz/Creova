# ADR-0017: Inject Credentials Only Through Secret Configuration

- Status: Accepted
- Date: 2026-07-21

## Context

The public bot username is known, but a Telegram token was exposed in a conversation. Embedding credentials in prompts or project files would allow anyone with access to control the bot or consume provider budgets.

## Decision

- Document `FeloCreova_bot` as public identity.
- Treat the exposed token as compromised and require rotation.
- Load the replacement token and provider keys only from environment variables or a production secret manager.
- Never include real values in prompts, code, tests, logs, documentation, or commits.
- Validate required credential presence without printing values.

## Consequences

- Initial setup includes a mandatory token-rotation step.
- Local development requires an ignored `.env` file.
- Provider availability is derived from safe configuration metadata.
