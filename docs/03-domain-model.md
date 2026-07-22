# Domain Model

## 1. Core concepts

### AccessGrant

Authorizes one numeric Telegram user ID with role, status, validity, and limits.

### ImageConversation

A durable, request-scoped conversation containing the selected creative assistant, optional renderer, stage, version, question count, expiration, and current creative brief.

### CreativeBrief

A structured representation of what the user wants. Fields are optional until review, but explicit user constraints always take precedence over inferred defaults.

Recommended fields:

- purpose and audience;
- subject and action;
- environment and time context;
- composition and viewpoint;
- style and medium;
- lighting and palette;
- aspect ratio and output quality;
- required visible text;
- constraints and exclusions;
- reference-asset IDs;
- uncertainty notes.

### BriefAssessment

A prompt-assistant result containing:

- normalized brief patch;
- readiness score or readiness decision;
- one next clarification question, when needed;
- suggested options;
- rationale stored only as safe metadata, not private chain-of-thought;
- optimized prompt when ready.

### ProviderSelection

Contains a `CreativeProvider` and an `ImageRenderer`.

Rules:

- Nano Banana assistant may default to Nano Banana renderer.
- ChatGPT assistant may default to ChatGPT renderer.
- Claude requires an explicit Nano Banana or ChatGPT renderer.
- Claude is never a valid `ImageRenderer` enum value.

### GenerationRequest

An immutable snapshot created only after confirmation. It stores the original prompt, final structured brief, optimized prompt, provider selection, logical output parameters, owner, confirmation version, and idempotency key.

### GenerationJob

A durable worker task with lease, retry, provider-operation, budget, and terminal-state metadata.

### GeneratedAsset

Private image metadata including storage key, MIME type, dimensions, byte size, SHA-256 digest, retention state, and provenance.

## 2. Conversation stages

- `awaiting_provider`
- `collecting_initial_prompt`
- `refining_brief`
- `awaiting_renderer`
- `awaiting_confirmation`
- `queued`
- `generating`
- `completed`
- `failed`
- `cancelled`
- `expired`

Transitions are validated in the domain. A stale draft version cannot be confirmed.

## 3. Invariants

- A request owner is an authorized numeric Telegram user.
- A conversation has at most one active clarification question.
- Question count never exceeds configured policy.
- The original prompt is preserved.
- Explicit user answers are distinguishable from model suggestions.
- A generation request cannot exist without confirmation.
- A confirmed request has a valid image renderer.
- `claude` cannot be represented as an image renderer.
- A generation request is immutable after job creation; changes create a new draft version or variation.
- An asset is available only after validation and private storage succeed.

## 4. Provider errors

Infrastructure errors translate into stable application categories:

- unavailable provider;
- invalid provider configuration;
- rate limited;
- transient upstream failure;
- policy rejection;
- invalid generated output;
- ambiguous external effect;
- permanent provider failure.

User-facing messages do not expose API keys, model internals, raw provider responses, or stack traces.
