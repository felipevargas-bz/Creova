# Product Requirements

## 1. Functional requirements

### Access and Telegram

- **FR-ACC-001:** The system MUST authorize by numeric `telegram_user_id` only.
- **FR-ACC-002:** Unknown, inactive, expired, suspended, or revoked users MUST be denied.
- **FR-ACC-003:** The MVP MUST accept only private chats with `@FeloCreova_bot`.
- **FR-ACC-004:** Telegram usernames and display names MUST be treated as informational metadata.
- **FR-ACC-005:** Telegram updates and callback actions MUST be deduplicated.

### Credentials

- **FR-SEC-001:** The Telegram token and provider API keys MUST be loaded from environment variables or a production secret manager.
- **FR-SEC-002:** Real credentials MUST NOT appear in documentation, prompts, code, fixtures, logs, or commits.
- **FR-SEC-003:** The application MUST fail safely when the Telegram token is missing.
- **FR-SEC-004:** An unavailable optional provider MUST be omitted or disabled in the provider menu.
- **FR-SEC-005:** Startup diagnostics MUST identify missing variable names without printing secret values.

### Provider selection

- **FR-PRV-001:** The creative assistant menu MUST support `nano_banana`, `chatgpt`, and `claude` when configured.
- **FR-PRV-002:** The image renderer menu MUST support `nano_banana` and `chatgpt` when configured.
- **FR-PRV-003:** Selecting Nano Banana as assistant SHOULD default the renderer to Nano Banana.
- **FR-PRV-004:** Selecting ChatGPT as assistant SHOULD default the renderer to ChatGPT.
- **FR-PRV-005:** Selecting Claude MUST require Nano Banana or ChatGPT as renderer before confirmation.
- **FR-PRV-006:** The UI MUST NOT claim that Claude generated the final image.
- **FR-PRV-007:** Provider model IDs MUST remain configuration, not domain values.

### Assisted image request

- **FR-BRF-001:** A free-text message or `/create` MUST start an image request draft rather than trigger generation.
- **FR-BRF-002:** The system MUST preserve the original user prompt separately from the optimized prompt.
- **FR-BRF-003:** The assistant MUST extract a structured brief containing, when relevant: purpose, subject, action, environment, composition, visual style, lighting, palette, camera or viewpoint, aspect ratio, required text, constraints, exclusions, and references.
- **FR-BRF-004:** The assistant MUST identify material unknowns and rank them by expected impact on the final image.
- **FR-BRF-005:** The bot MUST ask one concise question at a time.
- **FR-BRF-006:** The flow MUST stop asking when the brief is sufficiently specific, the configured maximum is reached, or the user chooses to review immediately.
- **FR-BRF-007:** Every question flow MUST provide a path to `Use your best judgment`, `Review now`, and `Cancel`.
- **FR-BRF-008:** The assistant MUST not invent brand names, factual claims, exact likenesses, or text that the user did not request.
- **FR-BRF-009:** Prompt-assistant responses SHOULD use schema-constrained structured output.
- **FR-BRF-010:** The final prompt MUST be derived from the approved structured brief and renderer capabilities.

### Review and confirmation

- **FR-CNF-001:** Before generation, the bot MUST show the selected creative assistant, selected renderer, concise brief, aspect ratio, quality, and optimized prompt.
- **FR-CNF-002:** The user MUST be able to edit a brief field, change assistant, change renderer, request another refinement, confirm, or cancel.
- **FR-CNF-003:** Confirmation MUST be explicit, durable, authorized again, and idempotent.
- **FR-CNF-004:** A stale confirmation callback MUST not generate an outdated draft.
- **FR-CNF-005:** Confirmation MUST reserve quota and budget atomically with job creation.
- **FR-CNF-006:** No provider generation call may occur before confirmation.

### Generation and delivery

- **FR-GEN-001:** Generation MUST execute in a worker, not in a Telegram webhook or polling handler.
- **FR-GEN-002:** Provider calls MUST use a stable idempotency fingerprint where supported and durable local deduplication everywhere.
- **FR-GEN-003:** The worker MUST validate output type, byte size, image dimensions, digest, and storage success.
- **FR-GEN-004:** The result MUST be delivered in Telegram when practical or through an authorized short-lived link.
- **FR-GEN-005:** The system MUST persist safe status, provider, model snapshot, cost metadata, and terminal outcome.
- **FR-GEN-006:** After successful delivery, the bot MUST say: “Publishing is not available yet, but Creova will support it in a future version.”
- **FR-GEN-007:** The post-delivery notice MUST not imply that publishing credentials or integrations already exist.

### History and cancellation

- **FR-HIS-001:** Users MAY inspect only their own requests and retained assets.
- **FR-HIS-002:** A draft or queued job MAY be cancelled idempotently.
- **FR-HIS-003:** A submitted provider operation MUST expose the real cancellation limitation safely.
- **FR-HIS-004:** History MUST distinguish original prompt, final prompt, assistant provider, renderer provider, and result status.

## 2. Non-functional requirements

- **NFR-001:** Python 3.12-compatible code with strict typing in domain and application layers.
- **NFR-002:** PostgreSQL is the source of truth for access, conversations, requests, jobs, and audit records.
- **NFR-003:** Binary assets are private in S3-compatible storage.
- **NFR-004:** Normal Telegram update handling targets less than two seconds without waiting for an AI provider.
- **NFR-005:** All timestamps use UTC internally.
- **NFR-006:** Every provider adapter has contract tests and a fake implementation.
- **NFR-007:** Prompt and credential retention follows explicit privacy policy.
- **NFR-008:** Logs MUST exclude secrets, authorization headers, binary data, signed URLs, and full prompt text by default.
- **NFR-009:** All code, comments, documentation, bot messages, and commits are in English.
- **NFR-010:** Every commit subject contains `🦅` plus a relevant emoji.

## 3. Acceptance scenario

Given an authorized user in a private chat, when the user selects Claude and writes “Create an image for a coffee launch,” the bot asks only material questions such as the product appearance, visual style, audience, and aspect ratio. It then shows a final creative brief and optimized prompt. Because Claude cannot be the renderer, the bot asks the user to select Nano Banana or ChatGPT. Only after the user confirms does Creova create a job. When the image is ready, Creova delivers it and explains that publishing is not available yet but is planned.
