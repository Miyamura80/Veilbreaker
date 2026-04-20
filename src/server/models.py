from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class SecretRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    environment: str
    service_name: str
    secret_name: str
    raw_secret: str
    key_fingerprint: str
    active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SecretAccessAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    environment: str
    service_name: str
    secret_name: str
    action: Literal["create", "read", "deactivate"]
    timestamp: datetime = Field(default_factory=utc_now)


class CredentialSeenEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_type: Literal["credential_seen"] = "credential_seen"
    timestamp: datetime = Field(default_factory=utc_now)
    provider: str
    key_fingerprint: str
    environment: str
    service_name: str
    deployment_id: str | None = None
    runtime: str | None = None
    source: str


class LlmRequestEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_type: Literal["llm_request"] = "llm_request"
    timestamp: datetime = Field(default_factory=utc_now)
    provider: str
    key_fingerprint: str
    environment: str
    service_name: str
    feature_name: str | None = None
    route_name: str | None = None
    workflow_name: str | None = None
    tenant_id: str | None = None
    model: str
    status: Literal["success", "error"]
    error_category: str | None = None
    latency_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None
    request_id: str | None = None
    trace_id: str | None = None


class ProviderFallbackEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_type: Literal["provider_fallback"] = "provider_fallback"
    timestamp: datetime = Field(default_factory=utc_now)
    from_provider: str
    from_key_fingerprint: str
    from_model: str
    to_provider: str
    to_key_fingerprint: str
    to_model: str
    reason: str
    service_name: str
    feature_name: str | None = None
    trace_id: str | None = None


class PolicyViolationEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_type: Literal["policy_violation"] = "policy_violation"
    timestamp: datetime = Field(default_factory=utc_now)
    policy_name: str
    severity: Literal["low", "medium", "high", "critical"]
    provider: str
    key_fingerprint: str
    environment: str
    service_name: str
    details: str


TelemetryEvent = Annotated[
    CredentialSeenEvent
    | LlmRequestEvent
    | ProviderFallbackEvent
    | PolicyViolationEvent,
    Field(discriminator="event_type"),
]


class UsageSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    environment: str
    service_name: str
    key_fingerprint: str
    feature_name: str | None = None
    requests: int
    errors: int
    total_cost_usd: float
