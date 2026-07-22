import pytest

from creova.domain.enums import ContentKind, CreativeProvider, ImageRenderer, JobStatus
from creova.domain.errors import InvalidStateTransition
from creova.domain.models import GenerationSpec, ProviderSelection, ensure_job_transition


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
