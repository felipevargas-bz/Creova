# Provider and Conversation Design

## 1. Why provider roles are separate

A user experiences “Nano Banana,” “ChatGPT,” and “Claude” as creative collaborators, but their APIs do not expose identical capabilities. Creova therefore models two independent roles:

- `PromptAssistant`: analyzes and improves the request;
- `ImageRenderer`: produces the image bytes.

This prevents capability confusion and allows a Claude-assisted brief to be rendered by Nano Banana or OpenAI.

## 2. Owned application ports

```python
class PromptAssistant(Protocol):
    async def assess(self, command: AssessBriefCommand) -> BriefAssessment: ...
    async def optimize(self, command: OptimizePromptCommand) -> OptimizedPrompt: ...

class ImageRenderer(Protocol):
    async def generate(self, spec: ConfirmedImageSpec, idempotency_key: str) -> RenderedImage: ...
```

Provider SDK objects never cross these boundaries.

## 3. Structured assistant contract

`BriefAssessment` should be schema constrained and contain:

- `brief_patch`;
- `material_unknowns` ordered by impact;
- `next_question` or `null`;
- `answer_options` when useful;
- `is_ready_for_review`;
- `safe_summary`;
- `optimized_prompt` only when ready.

Do not request or store hidden chain-of-thought. Ask for concise field-level reasons only when needed for observability.

## 4. Question policy

The application, not the provider, owns question limits and stopping rules.

Ask a question only when:

- its answer can materially alter the image;
- it is not already explicit or safely inferable;
- it is not redundant with a prior answer;
- the question limit has not been reached;
- the user has not chosen to review now.

Question selection priority generally favors purpose, main subject, intended composition, style, visible text, and aspect ratio, but the provider may rank unknowns based on context.

## 5. Prompt assembly

The final prompt is renderer-aware but provider-neutral in the domain. Infrastructure translators map logical settings to provider-specific API fields.

Prompt assembly should preserve:

- all explicit user constraints;
- exact required text, clearly delimited;
- important exclusions;
- composition and aspect ratio;
- reference-image semantics;
- safety policy outcome.

The final prompt is shown to the user before confirmation.

## 6. Provider registry

A registry exposes capability descriptors without secret values:

```text
provider_id
user_label
assistant_available
renderer_available
supports_reference_images
supported_aspect_ratios
supported_quality_levels
health_state
```

Availability depends on configuration, health, policy, and current circuit-breaker state.

## 7. Credential handling

- Bot username is public: `FeloCreova_bot`.
- Bot token is secret configuration and must never be stored in repository artifacts.
- No generated artifact or operational transcript contains a real secret.
- Local secrets live in `.env`, which is ignored.
- Production secrets live in a secret manager.
- Tests use obviously fake values and assert redaction.

## 8. Cost control

Prompt assistance and rendering have separate usage records. The system may permit brief refinement while a renderer budget is exhausted, but confirmation must fail before job creation if the generation budget cannot be reserved.

## 9. Publishing notice

The delivery message mentions future publishing as a product notice only. It does not emit a publication job, request social credentials, or create platform-specific data.
