# Creova Project Definition

## 1. Executive summary

Creova is a private AI image-creation assistant operated through `@FeloCreova_bot`. An authorized user can send a simple idea such as “a futuristic coffee shop in Bogotá,” choose an AI assistant, answer a small number of useful creative questions, review the resulting brief and optimized prompt, explicitly confirm the request, and receive the generated image.

The MVP is intentionally image-only. Social publishing and video generation are future capabilities and must not leak into current entities, credentials, commands, or deployment permissions.

## 2. Vision

Make high-quality AI image creation feel like collaborating with a patient creative director, while preserving access control, provider choice, cost control, reproducibility, and operational safety.

## 3. User problem

A short prompt often omits details that strongly affect the result: purpose, subject, composition, visual style, environment, lighting, palette, camera, text, aspect ratio, and constraints. Asking every possible question creates friction, while generating immediately can waste money and produce an unsuitable image.

Creova solves this by identifying only material ambiguity, asking one concise question at a time, and requiring confirmation before any billable generation.

## 4. Product promise

- Start from a simple natural-language idea.
- Receive intelligent assistance rather than a static form.
- Choose Nano Banana, ChatGPT, or Claude as the creative assistant.
- Use Nano Banana or ChatGPT as the actual image renderer.
- See exactly what will be generated before paying for generation.
- Retain a traceable brief, optimized prompt, provider selection, result, and status.
- Stay private through a numeric Telegram ID allowlist.

## 5. Actors

### Authorized user

Creates and refines image requests, confirms or cancels them, receives generated assets, and views owned history.

### Administrator

Manages allowlist grants, roles, quotas, provider availability, and operational policy through a private CLI.

### Operator

Deploys, monitors, restores, and troubleshoots the system using safe metadata and auditable administrative actions.

## 6. MVP scope

### Included

- Telegram private-chat interface.
- Bot identity `FeloCreova_bot`.
- Numeric Telegram ID allowlist with deny-by-default behavior.
- Creative assistant selection: Nano Banana, ChatGPT, or Claude.
- Image renderer selection: Nano Banana or ChatGPT.
- Structured creative brief extraction.
- Adaptive clarification with a maximum question count.
- Optimized prompt generation and review.
- Explicit confirmation before generation.
- Durable asynchronous generation jobs.
- Private object storage and Telegram delivery.
- History, status, cancellation before submission, quotas, budgets, auditability, and cleanup.
- A post-delivery notice that social publishing is not available yet.

### Excluded

- Direct image rendering by Claude.
- Social-network publishing or scheduling.
- Social credentials or platform SDKs.
- Video generation.
- Public registration or billing.
- A web or mobile frontend.
- Long-term personal memory outside a request.

## 7. Success criteria

- No unauthorized user can create or inspect a request.
- No image generation begins without durable explicit confirmation.
- Duplicate Telegram updates or callbacks do not create duplicate generations.
- The clarification flow asks only material questions and never exceeds the configured limit.
- Claude requests always resolve to Nano Banana or ChatGPT for rendering before confirmation.
- Provider outages are isolated and visible as provider availability, not system-wide failure.
- Every delivered image has a stored brief, final prompt, renderer, asset digest, and audit trail.
- Every successful result includes the future-publishing notice.

## 8. Product principles

- **Private by default.**
- **Ask only what matters.**
- **Confirm before cost.**
- **Represent provider capabilities honestly.**
- **Keep conversation state durable.**
- **Prefer deterministic structured outputs for brief extraction.**
- **Make retries idempotent.**
- **Keep publishing future-ready but absent.**
- **Keep every repository artifact in English.**
