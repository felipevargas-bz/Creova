# Audit Plan

## Scope

This audit covers the current Creova foundation for the image-only assisted MVP. It reviewed the repository documentation, local agent instructions, ADRs 0015 through 0017, source code, tests, configuration, and ignore rules.

No provider integrations were added.

## Findings

### Correct alignment

- The MVP is consistently image-only. Video generation is documented as a future phase, not an MVP capability.
- Telegram is consistently the only user interface.
- Social publishing is consistently deferred. Existing references are future-boundary or post-delivery notice requirements, not runtime publishing logic.
- Claude is consistently modeled as a prompt assistant only. The domain `ImageRenderer` enum has no Claude value, and tests cover the required renderer handoff.
- The public Telegram username is `FeloCreova_bot` in documentation and runtime configuration.
- No Telegram-token-shaped, OpenAI-key-shaped, Google-key-shaped, Slack-token-shaped, or private-key-shaped secret was found in non-ignored project files by the available regex scan.
- `.env`, `.env.*`, `AGENTS.md`, `.venv`, IDE metadata, and Python/tool caches are ignored.
- `.env.example` is now present and intended to be tracked with placeholders only.

### Foundation fixes applied

- Added `.env.example` because setup documentation requires it and the repository previously did not contain it.
- Added development artifact ignores for `.venv`, `.mypy_cache`, `.ruff_cache`, and `*.egg-info`.
- Set `enable_decoding=False` in `Settings.model_config` so comma-separated environment variables documented in `.env.example` are parsed by project validators instead of failing JSON decoding.
- Updated `Mapping` imports to satisfy Ruff's Python 3.12 upgrade rule.

### Non-blocking findings

- `MANIFEST.txt` lists some packaging-oriented files that are not currently present, such as `.dockerignore` and `.github/workflows/ci.yml`. This does not block tests, but packaging should either add those files or regenerate the manifest before release.
- `docs/14-verification.md` records an older verification snapshot. The current audit supersedes it for this run, but future verification records should avoid claiming unavailable tools when the environment has changed.

## Exact Implementation Order

1. Keep secret safety in place: maintain `.env`, `.env.*`, `AGENTS.md`, local IDE metadata, virtual environments, package metadata, and tool caches as ignored files.
2. Keep `.env.example` tracked with placeholder values only.
3. Complete persistent PostgreSQL migrations for access grants, conversations, creative briefs, requests, generation jobs, assets, usage, audit records, idempotency records, and outbox records.
4. Implement the allowlist administration CLI against PostgreSQL.
5. Implement Telegram update deduplication, private-chat enforcement, command routing, and callback version checks.
6. Implement the provider capability registry without provider SDK calls in the domain or application layers.
7. Implement durable conversation state, question limits, review controls, and expiration.
8. Implement prompt-assistant adapters for Nano Banana/Gemini, ChatGPT/OpenAI, and Claude/Anthropic.
9. Implement renderer adapters for Nano Banana/Gemini and ChatGPT/OpenAI only.
10. Implement explicit confirmation as the durable authorization, quota, budget, and job-creation boundary.
11. Implement the worker queue, leases, retries, reconciliation, storage validation, and Telegram delivery.
12. Implement status, history, cancellation, quotas, budgets, cleanup, observability, and release checks.
13. Add social publishing and video only in later phases with separate ADRs, credentials, and domain boundaries.

## Risks

- Local `.env` values can affect tests because `Settings` intentionally reads `.env`. Tests should pass with documented comma-separated values and should override secrets with fake values.
- The Telegram token previously exposed outside the repository must remain treated as compromised. Only a rotated value may be used locally or in production secret storage.
- Missing optional provider keys must disable provider availability without crashing unrelated flows.
- Claude handoff must remain enforced in UI, persistence, confirmation, and worker code.
- Confirmation idempotency is the highest-cost boundary and needs broad tests before provider calls are introduced.
- Packaging and CI are not complete until the manifest, CI workflow, linting, typing, unit tests, and secret scanning are aligned.

## Commands Run

```bash
sed -n '1,220p' README.md
sed -n '1,220p' AGENTS.md
sed -n '1,240p' docs/00-project-definition.md
sed -n '1,260p' docs/01-product-requirements.md
sed -n '1,280p' docs/02-architecture.md
sed -n '1,260p' docs/15-provider-and-conversation-design.md
sed -n '1,220p' docs/adr/0015-separate-prompt-assistants-and-image-renderers.md
sed -n '1,220p' docs/adr/0016-assisted-brief-and-explicit-confirmation.md
sed -n '1,220p' docs/adr/0017-secret-only-credential-injection.md
git status --short --ignored .env .env.example AGENTS.md .gitignore
git ls-files .env .env.example AGENTS.md .gitignore
rg -n "<removed prompt artifact patterns>" -S .
git ls-files -co --exclude-standard -z | xargs -0 rg -n -I "([0-9]{8,10}:[A-Za-z0-9_-]{30,}|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{35}|xox[baprs]-[A-Za-z0-9-]{20,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)" || true
git ls-files -co --exclude-standard -z | xargs -0 rg -n -I "<non-English term pattern>" || true
git ls-files -co --exclude-standard -z | xargs -0 rg -n -I "Claude.*(render|generate|generated|image)|claude.*(renderer|render|generate|generated)|video generation|video.*MVP|social.*(SDK|credential|token|publish|publication|logic|command|table)" || true
command -v gitleaks || true
command -v trufflehog || true
command -v detect-secrets || true
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy src
```

## Verification Results

```text
.venv/bin/pytest
16 passed

.venv/bin/ruff check .
All checks passed

.venv/bin/mypy src
Success: no issues found in 21 source files

Dedicated secret scanners
gitleaks, trufflehog, and detect-secrets were not installed.

Available regex secret scan
No matches in non-ignored project files.
```
