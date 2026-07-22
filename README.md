# Creova

Creova is a private Telegram bot that helps an authorized user turn a simple idea into a carefully specified AI image. The bot conducts a short creative interview, refines the prompt, presents a final brief for confirmation, generates the image only after explicit approval, and delivers the result in Telegram.

The registered Telegram identity for this project is **@FeloCreova_bot**. The bot token is a secret and is never stored in this repository, documentation, or commits.

## Security notice before first use

A Telegram bot token was previously pasted into a chat. Treat that token as compromised. Open `@BotFather`, use `/revoke` or generate a new token for `@FeloCreova_bot`, and place only the rotated token in your local `.env` or production secret manager.

Never paste the replacement token into chats, prompts, or generated artifacts. Tooling must read credential names from configuration and use placeholders only.

## Repository status

This repository is an architecture and implementation foundation. It contains product documentation, ADRs, diagrams, a typed Python scaffold, starter tests, and an ordered implementation plan.

## MVP scope

- Telegram is the only user interface.
- Only private chats are accepted.
- A deny-by-default allowlist authorizes numeric Telegram user IDs.
- The user can select Nano Banana, ChatGPT, or Claude as the creative assistant.
- Nano Banana and ChatGPT can be selected as image renderers.
- Claude is a prompt-refinement assistant and must hand the approved prompt to Nano Banana or ChatGPT for rendering.
- The bot asks only useful clarification questions and stores a structured creative brief.
- Generation begins only after the user confirms the final brief, optimized prompt, renderer, aspect ratio, and quality.
- Generated assets are stored privately and delivered through Telegram or a short-lived signed link.
- After delivery, the bot explains that social publishing is not available yet and will arrive in a future version.

## Explicitly out of scope

- Social-network publishing, scheduling, credentials, or analytics.
- Video generation in the MVP.
- A web frontend or native application.
- Public registration, billing, or marketplace functionality.
- Long-lived memory across unrelated image requests.

## Provider behavior

| User-facing choice | Prompt assistance | Native image rendering in Creova |
|---|---:|---:|
| Nano Banana | Yes | Yes, through the Gemini API |
| ChatGPT | Yes | Yes, through the OpenAI API |
| Claude | Yes | No; the user must choose Nano Banana or ChatGPT as renderer |

Provider names are user-facing labels. SDKs, model IDs, limits, and prices remain infrastructure configuration.

## Conversation summary

1. The user starts a new image request.
2. The bot asks which creative assistant to use.
3. The user sends a simple image idea.
4. The assistant extracts a structured brief and identifies material ambiguity.
5. The bot asks one concise, high-value question at a time, with a configurable maximum.
6. The bot shows the creative brief and optimized final prompt.
7. The user may confirm, edit a field, ask for another refinement, change provider, or cancel.
8. If Claude was selected, the user chooses Nano Banana or ChatGPT as renderer before confirmation.
9. Explicit confirmation creates a durable generation job.
10. The worker renders, validates, stores, and delivers the image.
11. The bot states that publishing is not supported yet but is planned.

## Repository layout

```text
creova/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── docker-compose.yml
├── .env.example
├── docs/
│   ├── adr/
│   └── diagrams/
├── migrations/
├── scripts/
├── src/creova/
└── tests/
```

`AGENTS.md` is intentionally included in the ZIP for local coding agents and intentionally listed in `.gitignore` so it is not committed.

## Local setup

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
ruff check .
mypy src
```

Then set these values in `.env`:

```env
CREOVA_TELEGRAM_BOT_USERNAME=FeloCreova_bot
CREOVA_TELEGRAM_BOT_TOKEN=replace-with-the-newly-rotated-token
CREOVA_BOOTSTRAP_ADMIN_IDS=your-numeric-telegram-id
CREOVA_BOOTSTRAP_ALLOWED_USER_IDS=your-numeric-telegram-id
```

Add only the API keys for providers you enable. Missing keys must disable the corresponding provider gracefully rather than crash unrelated flows.

## Non-negotiable rules

- Never commit or print real credentials.
- Keep all code, identifiers, comments, logs, bot messages, documentation, and commits in English.
- Every commit subject includes `🦅` and at least one change-related emoji.
- Authorize only by numeric Telegram user ID.
- Never generate before explicit user confirmation.
- Never claim that Claude directly rendered an image.
- Never add social publishing to the MVP.
- Keep provider SDKs outside the domain and application layers.
