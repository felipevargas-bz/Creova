from datetime import UTC, datetime, timedelta

import pytest

from creova.domain.enums import (
    BriefProvenance,
    ContentKind,
    ConversationStage,
    CreativeProvider,
    ImageRenderer,
    JobStatus,
)
from creova.domain.errors import InvalidStateTransition
from creova.domain.models import (
    CreativeBrief,
    GenerationSpec,
    ImageConversation,
    ProviderSelection,
    ensure_job_transition,
)

NOW = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)


def test_normalizes_prompt() -> None:
    spec = GenerationSpec(ContentKind.IMAGE, "  a mountain  ", {})
    assert spec.prompt == "a mountain"


def test_rejects_empty_prompt() -> None:
    with pytest.raises(ValueError):
        GenerationSpec(ContentKind.IMAGE, "   ", {})


def test_nano_banana_defaults_to_matching_renderer() -> None:
    selection = ProviderSelection(CreativeProvider.NANO_BANANA)
    assert selection.renderer is ImageRenderer.NANO_BANANA


def test_chatgpt_defaults_to_matching_renderer() -> None:
    selection = ProviderSelection(CreativeProvider.CHATGPT)
    assert selection.renderer is ImageRenderer.CHATGPT


def test_claude_requires_separate_renderer() -> None:
    selection = ProviderSelection(CreativeProvider.CLAUDE)
    assert not selection.is_ready_for_confirmation
    with pytest.raises(ValueError, match="renderer"):
        GenerationSpec(ContentKind.IMAGE, "a mountain", {}, provider=selection)


def test_claude_can_handoff_to_nano_banana() -> None:
    selection = ProviderSelection(CreativeProvider.CLAUDE, ImageRenderer.NANO_BANANA)
    spec = GenerationSpec(ContentKind.IMAGE, "a mountain", {}, provider=selection)
    assert spec.provider.renderer is ImageRenderer.NANO_BANANA


def test_accepts_valid_job_transition() -> None:
    ensure_job_transition(JobStatus.QUEUED, JobStatus.LEASED)


def test_rejects_invalid_job_transition() -> None:
    with pytest.raises(InvalidStateTransition):
        ensure_job_transition(JobStatus.SUCCEEDED, JobStatus.RUNNING)


def test_creative_brief_preserves_user_values_over_assistant_suggestions() -> None:
    brief = CreativeBrief().with_user_value("subject", "coffee bag")
    updated = brief.with_assistant_patch({"subject": "tea box", "style": "editorial"})

    assert updated.subject == "coffee bag"
    assert updated.style == "editorial"
    assert updated.provenance["subject"] is BriefProvenance.USER
    assert updated.provenance["style"] is BriefProvenance.ASSISTANT
    assert updated.assistant_suggestions["subject"] == "tea box"


def test_conversation_follows_provider_prompt_question_confirmation_path() -> None:
    conversation = ImageConversation.start(
        owner_telegram_user_id=123,
        chat_id=456,
        now=NOW,
        ttl_minutes=60,
    )
    assert conversation.stage is ConversationStage.AWAITING_PROVIDER

    conversation = conversation.select_assistant(
        CreativeProvider.NANO_BANANA,
        now=NOW,
        ttl_minutes=60,
    )
    assert conversation.stage is ConversationStage.COLLECTING_INITIAL_PROMPT
    assert conversation.renderer_provider is ImageRenderer.NANO_BANANA

    conversation = conversation.submit_initial_prompt(
        "  a coffee launch image  ",
        now=NOW,
        ttl_minutes=60,
    )
    assert conversation.stage is ConversationStage.REFINING_BRIEF
    assert conversation.original_prompt == "a coffee launch image"

    conversation = conversation.apply_assessment(
        brief_patch={"subject": "coffee bag"},
        next_question="Who is the audience?",
        answer_options=("Consumers", "Retailers"),
        is_ready_for_review=False,
        optimized_prompt=None,
        max_questions=6,
        now=NOW,
        ttl_minutes=60,
    )
    assert conversation.active_question is not None
    assert conversation.question_count == 1
    assert conversation.stage is ConversationStage.REFINING_BRIEF

    conversation = conversation.answer_question(
        "premium coffee buyers",
        field_name="audience",
        now=NOW,
        ttl_minutes=60,
    )
    assert conversation.active_question is None
    assert conversation.brief.audience == "premium coffee buyers"

    conversation = conversation.apply_assessment(
        brief_patch={"style": "editorial product photography"},
        next_question=None,
        answer_options=(),
        is_ready_for_review=True,
        optimized_prompt="Final renderer prompt",
        max_questions=6,
        now=NOW,
        ttl_minutes=60,
    )
    assert conversation.stage is ConversationStage.AWAITING_CONFIRMATION
    assert conversation.optimized_prompt == "Final renderer prompt"


def test_claude_ready_brief_moves_to_renderer_handoff() -> None:
    conversation = ImageConversation.start(
        owner_telegram_user_id=123,
        chat_id=456,
        now=NOW,
        ttl_minutes=60,
    ).select_assistant(CreativeProvider.CLAUDE, now=NOW, ttl_minutes=60)
    conversation = conversation.submit_initial_prompt("a launch image", now=NOW, ttl_minutes=60)

    conversation = conversation.apply_assessment(
        brief_patch={"subject": "coffee bag"},
        next_question=None,
        answer_options=(),
        is_ready_for_review=True,
        optimized_prompt="Final renderer prompt",
        max_questions=6,
        now=NOW,
        ttl_minutes=60,
    )

    assert conversation.stage is ConversationStage.AWAITING_RENDERER
    assert conversation.renderer_provider is None
    conversation = conversation.select_renderer(ImageRenderer.CHATGPT, now=NOW, ttl_minutes=60)
    assert conversation.stage is ConversationStage.AWAITING_CONFIRMATION


def test_conversation_allows_one_active_question() -> None:
    conversation = _refining_conversation().apply_assessment(
        brief_patch={},
        next_question="What style?",
        answer_options=(),
        is_ready_for_review=False,
        optimized_prompt=None,
        max_questions=6,
        now=NOW,
        ttl_minutes=60,
    )

    with pytest.raises(InvalidStateTransition, match="active question"):
        conversation.apply_assessment(
            brief_patch={},
            next_question="What lighting?",
            answer_options=(),
            is_ready_for_review=False,
            optimized_prompt=None,
            max_questions=6,
            now=NOW,
            ttl_minutes=60,
        )


def test_conversation_caps_and_deduplicates_questions() -> None:
    conversation = _refining_conversation()

    conversation = conversation.apply_assessment(
        brief_patch={},
        next_question="What style?",
        answer_options=(),
        is_ready_for_review=False,
        optimized_prompt="Prompt",
        max_questions=0,
        now=NOW,
        ttl_minutes=60,
    )
    assert conversation.stage is ConversationStage.AWAITING_CONFIRMATION
    assert conversation.question_count == 0

    duplicate = _refining_conversation().apply_assessment(
        brief_patch={},
        next_question="What style?",
        answer_options=(),
        is_ready_for_review=False,
        optimized_prompt=None,
        max_questions=6,
        now=NOW,
        ttl_minutes=60,
    )
    duplicate = duplicate.answer_question("Editorial", now=NOW, ttl_minutes=60)
    duplicate = duplicate.apply_assessment(
        brief_patch={},
        next_question=" what   STYLE? ",
        answer_options=(),
        is_ready_for_review=False,
        optimized_prompt="Prompt",
        max_questions=6,
        now=NOW,
        ttl_minutes=60,
    )
    assert duplicate.stage is ConversationStage.AWAITING_CONFIRMATION
    assert duplicate.question_count == 1


def test_review_edit_start_over_cancel_and_stale_callbacks() -> None:
    conversation = _refining_conversation()
    version = conversation.version

    with pytest.raises(InvalidStateTransition, match="Stale"):
        conversation.apply_callback_version(version - 1)

    conversation.apply_callback_version(version)
    reviewed = conversation.review_now(now=NOW, ttl_minutes=60)
    assert reviewed.stage is ConversationStage.AWAITING_CONFIRMATION

    edited = reviewed.edit_details("style", "minimal", now=NOW, ttl_minutes=60)
    assert edited.stage is ConversationStage.REFINING_BRIEF
    assert edited.brief.style == "minimal"

    restarted = edited.start_over(now=NOW, ttl_minutes=60)
    assert restarted.stage is ConversationStage.AWAITING_PROVIDER
    assert restarted.original_prompt is None
    assert restarted.version == 1

    cancelled = edited.cancel(now=NOW)
    assert cancelled.stage is ConversationStage.CANCELLED


def test_use_best_judgment_and_expiration() -> None:
    conversation = _refining_conversation().apply_assessment(
        brief_patch={},
        next_question="What lighting?",
        answer_options=(),
        is_ready_for_review=False,
        optimized_prompt=None,
        max_questions=6,
        now=NOW,
        ttl_minutes=60,
    )
    skipped = conversation.use_best_judgment(now=NOW, ttl_minutes=60)
    assert skipped.active_question is None
    assert skipped.turns[-1].metadata["kind"] == "use_best_judgment"

    expired = skipped.expire_if_abandoned(NOW + timedelta(minutes=61))
    assert expired.stage is ConversationStage.EXPIRED


def _refining_conversation() -> ImageConversation:
    return (
        ImageConversation.start(
            owner_telegram_user_id=123,
            chat_id=456,
            now=NOW,
            ttl_minutes=60,
        )
        .select_assistant(CreativeProvider.NANO_BANANA, now=NOW, ttl_minutes=60)
        .submit_initial_prompt("a launch image", now=NOW, ttl_minutes=60)
    )
