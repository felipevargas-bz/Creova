# ADR-0015: Separate Prompt Assistants from Image Renderers

- Status: Accepted
- Date: 2026-07-21

## Context

Creova must offer Nano Banana, ChatGPT, and Claude. These providers do not expose identical image-output capabilities. Treating every provider as an image renderer would create false product behavior and brittle abstractions.

## Decision

Define separate `PromptAssistant` and `ImageRenderer` ports.

- Nano Banana implements both roles.
- ChatGPT/OpenAI implements both roles.
- Claude/Anthropic implements `PromptAssistant` only.
- The `ImageRenderer` domain enum intentionally has no Claude value.
- A Claude-assisted request must select Nano Banana or ChatGPT before confirmation.

## Consequences

- Provider capabilities are represented honestly.
- The user can benefit from Claude's creative refinement without misattributing image generation.
- A request stores both assistant provider and renderer provider.
- UI and tests require a handoff when Claude is selected.
