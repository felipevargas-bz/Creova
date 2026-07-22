# ADR-0017: Inject Credentials Only Through Secret Configuration

- Status: Accepted
- Date: 2026-07-21

## Context

The public bot username is not a secret. Runtime credentials, provider keys, webhook secrets, and storage credentials are sensitive operational data and must not be embedded in prompts, project files, logs, fixtures, documentation, or commits.

## Decision

- Document `FeloCreova_bot` as public identity.
- Load the bot token and provider keys only from environment variables or a production secret manager.
- Never include real values in prompts, code, tests, logs, documentation, or commits.
- Validate required credential presence without printing values.

## Consequences

- Local development requires an ignored `.env` file.
- Provider availability is derived from safe configuration metadata.
