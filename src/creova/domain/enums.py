from enum import StrEnum


class AccessRole(StrEnum):
    USER = "user"
    ADMIN = "admin"
    OPERATOR = "operator"


class AccessStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ContentKind(StrEnum):
    IMAGE = "image"


class CreativeProvider(StrEnum):
    NANO_BANANA = "nano_banana"
    CHATGPT = "chatgpt"
    CLAUDE = "claude"


class ImageRenderer(StrEnum):
    NANO_BANANA = "nano_banana"
    CHATGPT = "chatgpt"


class ConversationStage(StrEnum):
    AWAITING_PROVIDER = "awaiting_provider"
    COLLECTING_INITIAL_PROMPT = "collecting_initial_prompt"
    REFINING_BRIEF = "refining_brief"
    AWAITING_RENDERER = "awaiting_renderer"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    QUEUED = "queued"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class BriefProvenance(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    INFERRED = "inferred"
    DEFAULT = "default"


class RequestStatus(StrEnum):
    DRAFT = "draft"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    ACCEPTED = "accepted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class JobStatus(StrEnum):
    QUEUED = "queued"
    LEASED = "leased"
    SUBMITTED = "submitted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ProviderErrorCategory(StrEnum):
    UNAVAILABLE_PROVIDER = "unavailable_provider"
    INVALID_PROVIDER_CONFIGURATION = "invalid_provider_configuration"
    RATE_LIMITED = "rate_limited"
    TRANSIENT_UPSTREAM_FAILURE = "transient_upstream_failure"
    POLICY_REJECTION = "policy_rejection"
    INVALID_GENERATED_OUTPUT = "invalid_generated_output"
    AMBIGUOUS_EXTERNAL_EFFECT = "ambiguous_external_effect"
    PERMANENT_PROVIDER_FAILURE = "permanent_provider_failure"
