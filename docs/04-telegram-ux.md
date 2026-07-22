# Telegram Bot Experience

## 1. Principles

- Use short, warm, actionable English messages.
- Ask one question at a time.
- Explain why a choice matters only when that helps the user answer.
- Do not generate automatically from a free-text prompt.
- Always allow the user to review, delegate defaults, or cancel.
- Edit existing status messages when practical instead of flooding the chat.
- Re-authorize every callback and resource action.

## 2. Commands

### `/start`

Authorized response:

> Hi, I am Creova. I can help you turn a simple idea into a carefully designed AI image. Send me an idea or use /create to begin.

Unauthorized response:

> This bot is private and your account does not have access. Your Telegram ID is `123456789`.

### `/create`

Starts a new image conversation. If an active draft exists, offer `Continue`, `Start over`, or `Cancel`.

### `/status`

Shows the state of a confirmed generation request.

### `/history`

Shows owned recent requests and retained results.

### `/cancel`

Cancels the active draft or requests job cancellation when possible.

### `/whoami`

Shows numeric Telegram ID, role, access status, and summarized quota.

### `/help`

Explains the workflow and provider roles without exposing model IDs or secret configuration.

## 3. Provider selection

Message:

> Which AI should help shape your image?

Buttons:

- `Nano Banana`
- `ChatGPT`
- `Claude`
- `Cancel`

If a provider credential is absent or unhealthy, omit or disable that option with a neutral `Unavailable` label for authorized users.

Provider explanation:

- Nano Banana: helps refine and can generate the image.
- ChatGPT: helps refine and can generate the image.
- Claude: helps refine the creative brief; you will choose Nano Banana or ChatGPT to generate the final image.

## 4. Initial prompt

> Describe the image you have in mind. A simple idea is enough—I will help with the details.

Example:

> A premium coffee product photo for Instagram, with a Colombian mountain feeling.

This message creates a draft only.

## 5. Clarification behavior

The assistant extracts what is already known and asks the highest-impact missing question.

Example:

> What should be the main subject of the image?

Buttons may contain concrete options plus:

- `Use your best judgment`
- `Review now`
- `Cancel`

Useful clarification dimensions include purpose, subject, environment, composition, style, lighting, palette, aspect ratio, visible text, and exclusions. The bot must not mechanically ask every dimension.

## 6. Claude renderer handoff

When Claude is the selected assistant and the brief is ready:

> Claude has prepared the creative brief. Which service should generate the final image?

Buttons:

- `Nano Banana`
- `ChatGPT`
- `Back to brief`
- `Cancel`

## 7. Review screen

> Your image brief is ready.
>
> Assistant: Claude
> Renderer: Nano Banana
> Purpose: Instagram product launch
> Subject: Premium Colombian coffee bag on dark stone
> Style: Editorial product photography
> Lighting: Warm side light with soft shadows
> Format: 4:5 portrait
>
> Final prompt:
> “Create an editorial product photograph...”
>
> Generate this image?

Buttons:

- `Generate image`
- `Edit details`
- `Refine prompt`
- `Change AI`
- `Cancel`

The callback contains the draft ID and version. `Generate image` is explicit confirmation and must be idempotent.

## 8. Generation status

Immediate response:

> Your image request has been confirmed and queued. I will send the result here when it is ready.

Progress stages:

- queued;
- preparing;
- generating;
- validating;
- storing;
- delivering.

Do not fabricate a percentage when the provider does not expose one.

## 9. Successful result

> Your image is ready.
>
> Assistant: Claude
> Generated with: Nano Banana
> Format: 4:5 portrait
>
> Publishing is not available yet, but Creova will support it in a future version.

Attach the image or provide an authorized temporary link.

## 10. Errors

- Provider unavailable: “That AI service is temporarily unavailable. Choose another service or try again later.”
- Missing credential: authorized administrators may receive a configuration code; regular users receive the neutral provider-unavailable message.
- Policy rejection: “I cannot help create that image.”
- Quota: “You have reached your image limit for now.”
- Internal error: “Something went wrong. Support code: CRV-...”

Never include raw upstream responses, keys, tokens, or model traces.
