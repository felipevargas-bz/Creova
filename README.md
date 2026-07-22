# Creova

Creova is a private Telegram assistant for guided AI image creation. It helps authorized users turn a simple idea into a structured creative brief, refine the prompt, choose an image renderer, confirm the request, and receive the generated image through Telegram.

The production Telegram bot username is **@FeloCreova_bot**.

## Status

Creova is under active development. The repository currently includes the application foundation, domain model, persistence schema, Telegram transport, provider capability registry, prompt-assistant contracts, and initial Gemini/OpenAI provider adapters.

## Core Features

- Private Telegram workflow for image generation.
- Deny-by-default access control by numeric Telegram user ID.
- Guided creative-brief refinement with a configurable question limit.
- Explicit review and confirmation before any billable generation.
- Separate prompt-assistant and image-renderer provider roles.
- Nano Banana and ChatGPT image rendering.
- Claude prompt assistance with renderer handoff to Nano Banana or ChatGPT.
- Durable PostgreSQL persistence for conversations, jobs, assets, usage, notifications, and audit events.
- Provider credentials loaded from environment variables or production secret management.
- Safe configuration diagnostics and redacted logs.

## Architecture

Creova follows a layered Python architecture:

- `domain`: provider-neutral entities, enums, invariants, and state transitions.
- `application`: use cases, ports, policies, prompt contracts, and orchestration.
- `infrastructure`: PostgreSQL repositories, provider adapters, fakes, and local utilities.
- `presentation`: Telegram polling/webhook transport and HTTP health endpoints.
- `migrations`: Alembic schema migrations.
- `tests`: unit and opt-in integration tests.

```text
src/creova/
├── application/
├── domain/
├── infrastructure/
│   └── db/
└── presentation/
    └── telegram/
```

## Provider Model

| User label | Prompt assistance | Image rendering |
|---|---:|---:|
| Nano Banana | Yes | Yes, via Gemini |
| ChatGPT | Yes | Yes, via OpenAI |
| Claude | Yes | No, requires renderer handoff |

Provider labels are product-facing names. SDK names, model IDs, credentials, capability checks, pricing, and rate limits remain infrastructure concerns.

## Requirements

- Python 3.12+
- PostgreSQL 16+
- Docker and Docker Compose for local infrastructure
- Telegram bot credentials for runtime use
- Provider API keys only for enabled providers

## Local Setup

Create the local environment:

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Start PostgreSQL:

```bash
docker compose up -d postgres
```

Run checks:

```bash
pytest
ruff check .
mypy src
```

## Configuration

Runtime configuration is loaded from environment variables. Local development may use `.env`; production should use a secret manager or platform-managed environment injection.

Minimum runtime variables:

```env
CREOVA_TELEGRAM_BOT_USERNAME=FeloCreova_bot
CREOVA_TELEGRAM_BOT_TOKEN=
CREOVA_DATABASE_URL=postgresql+asyncpg://creova:creova@localhost:5435/creova
```

Provider variables are optional. Missing provider keys disable only that provider:

```env
CREOVA_GOOGLE_API_KEY=
CREOVA_OPENAI_API_KEY=
CREOVA_ANTHROPIC_API_KEY=
```

Model IDs are configurable:

```env
CREOVA_GOOGLE_IMAGE_MODEL=
CREOVA_GOOGLE_ASSISTANT_MODEL=
CREOVA_OPENAI_IMAGE_MODEL=
CREOVA_OPENAI_ASSISTANT_MODEL=
CREOVA_ANTHROPIC_ASSISTANT_MODEL=
```

## Running

Polling mode:

```bash
CREOVA_TELEGRAM_MODE=polling creova-bot
```

Webhook API:

```bash
CREOVA_TELEGRAM_MODE=webhook creova-api
```

Administration CLI:

```bash
creova-admin access --help
```

## Testing

Normal test runs do not call external provider APIs:

```bash
pytest
```

Real provider smoke tests are opt-in and require local credentials:

```bash
CREOVA_REAL_PROVIDER_SMOKE=1 pytest tests/integration/test_gemini_smoke.py
CREOVA_REAL_PROVIDER_SMOKE_OPENAI=1 pytest tests/integration/test_openai_smoke.py
```

## Security

- Never commit real credentials, tokens, signed URLs, database passwords, or provider keys.
- Keep `.env`, `.env.*`, and local agent instructions ignored.
- Redact secrets from logs and diagnostics.
- Treat user prompts and reference content as untrusted creative data.
- Authorize by numeric Telegram user ID, not usernames.
- Require explicit confirmation before generation.

## Documentation

Project documentation lives under `docs/`:

- `docs/00-project-definition.md`
- `docs/01-product-requirements.md`
- `docs/02-architecture.md`
- `docs/03-domain-model.md`
- `docs/adr/`

## License

No license has been published for this repository.
