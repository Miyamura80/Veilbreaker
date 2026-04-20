from collections import defaultdict
from typing import Any

from pydantic import TypeAdapter

from .fingerprint import fingerprint_secret
from .models import (
    CredentialSeenEvent,
    LlmRequestEvent,
    PolicyViolationEvent,
    ProviderFallbackEvent,
    SecretRecord,
    TelemetryEvent,
    UsageSummary,
)
from .storage import InMemorySecretStore, InMemoryTelemetryStore

telemetry_event_adapter = TypeAdapter(TelemetryEvent)


class TelemetryService:
    def __init__(
        self,
        *,
        secret_store: InMemorySecretStore | None = None,
        telemetry_store: InMemoryTelemetryStore | None = None,
    ) -> None:
        self.secret_store = secret_store or InMemorySecretStore()
        self.telemetry_store = telemetry_store or InMemoryTelemetryStore()

    def store_secret(
        self,
        *,
        provider: str,
        environment: str,
        service_name: str,
        secret_name: str,
        raw_secret: str,
    ) -> SecretRecord:
        fingerprint = fingerprint_secret(raw_secret)
        secret_payload = {
            "provider": provider,
            "environment": environment,
            "service_name": service_name,
            "secret_name": secret_name,
            "raw_secret": raw_secret,
        }
        record = self.secret_store.store_secret(
            **secret_payload,
            key_fingerprint=fingerprint,
        )
        self.credential_seen(
            provider=provider,
            key_fingerprint=fingerprint,
            environment=environment,
            service_name=service_name,
            source="stored_secret",
        )
        return record

    def get_secret(
        self,
        *,
        provider: str,
        environment: str,
        service_name: str,
        secret_name: str,
    ) -> SecretRecord:
        return self.secret_store.get_secret(
            provider=provider,
            environment=environment,
            service_name=service_name,
            secret_name=secret_name,
        )

    def list_secrets(self) -> list[SecretRecord]:
        return self.secret_store.list_secrets()

    def credential_seen(self, **event_data: Any) -> CredentialSeenEvent:
        event = CredentialSeenEvent(**event_data)
        self.telemetry_store.append(event)
        return event

    def llm_request(self, **event_data: Any) -> LlmRequestEvent:
        event = LlmRequestEvent(**event_data)
        self.telemetry_store.append(event)
        violation = self._maybe_emit_prod_credential_violation(event)
        if violation is not None:
            self.telemetry_store.append(violation)
        return event

    def provider_fallback(self, **event_data: Any) -> ProviderFallbackEvent:
        event = ProviderFallbackEvent(**event_data)
        self.telemetry_store.append(event)
        return event

    def policy_violation(self, **event_data: Any) -> PolicyViolationEvent:
        event = PolicyViolationEvent(**event_data)
        self.telemetry_store.append(event)
        return event

    def ingest_events(
        self, events: list[TelemetryEvent | dict[str, Any]]
    ) -> list[TelemetryEvent]:
        validated_events = [
            telemetry_event_adapter.validate_python(event) for event in events
        ]
        ingested: list[TelemetryEvent] = []
        for event in validated_events:
            if isinstance(event, PolicyViolationEvent):
                ingested.append(self.policy_violation(**event.model_dump()))
            elif isinstance(event, ProviderFallbackEvent):
                ingested.append(self.provider_fallback(**event.model_dump()))
            elif isinstance(event, LlmRequestEvent):
                ingested.append(self.llm_request(**event.model_dump()))
            else:
                ingested.append(self.credential_seen(**event.model_dump()))
        return ingested

    def usage_summary(self) -> list[UsageSummary]:
        grouped: dict[tuple[str, str, str, str, str | None], dict[str, Any]] = (
            defaultdict(lambda: {"requests": 0, "errors": 0, "total_cost_usd": 0.0})
        )

        for event in self.telemetry_store.list_events():
            if not isinstance(event, LlmRequestEvent):
                continue

            key = (
                event.provider,
                event.environment,
                event.service_name,
                event.key_fingerprint,
                event.feature_name,
            )
            grouped[key]["requests"] += 1
            grouped[key]["errors"] += 1 if event.status == "error" else 0
            grouped[key]["total_cost_usd"] += event.estimated_cost_usd or 0.0

        return [
            UsageSummary(
                provider=provider,
                environment=environment,
                service_name=service_name,
                key_fingerprint=key_fingerprint,
                feature_name=feature_name,
                requests=data["requests"],
                errors=data["errors"],
                total_cost_usd=round(data["total_cost_usd"], 6),
            )
            for (
                provider,
                environment,
                service_name,
                key_fingerprint,
                feature_name,
            ), data in grouped.items()
        ]

    def list_events(self) -> list[TelemetryEvent]:
        return self.telemetry_store.list_events()

    def _maybe_emit_prod_credential_violation(
        self, event: LlmRequestEvent
    ) -> PolicyViolationEvent | None:
        if event.environment == "prod":
            return None

        prod_fingerprints = {
            record.key_fingerprint
            for record in self.secret_store.list_secrets()
            if record.environment == "prod" and record.active
        }
        if event.key_fingerprint not in prod_fingerprints:
            return None

        return PolicyViolationEvent(
            policy_name="prod_credential_used_in_non_prod",
            severity="critical",
            provider=event.provider,
            key_fingerprint=event.key_fingerprint,
            environment=event.environment,
            service_name=event.service_name,
            details=(
                "A production credential fingerprint was used outside production."
            ),
        )
