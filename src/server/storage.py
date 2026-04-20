from pydantic import TypeAdapter

from .models import SecretAccessAudit, SecretRecord, TelemetryEvent

telemetry_event_adapter = TypeAdapter(TelemetryEvent)


class InMemorySecretStore:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str, str], SecretRecord] = {}
        self._audit_log: list[SecretAccessAudit] = []

    def store_secret(
        self,
        *,
        provider: str,
        environment: str,
        service_name: str,
        secret_name: str,
        raw_secret: str,
        key_fingerprint: str,
    ) -> SecretRecord:
        record = SecretRecord(
            provider=provider,
            environment=environment,
            service_name=service_name,
            secret_name=secret_name,
            raw_secret=raw_secret,
            key_fingerprint=key_fingerprint,
        )
        key = (provider, environment, service_name, secret_name)
        self._records[key] = record
        self._audit_log.append(
            SecretAccessAudit(
                provider=provider,
                environment=environment,
                service_name=service_name,
                secret_name=secret_name,
                action="create",
            )
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
        key = (provider, environment, service_name, secret_name)
        if key not in self._records:
            raise KeyError("secret not found")

        record = self._records[key]
        if not record.active:
            raise ValueError("secret is inactive")

        self._audit_log.append(
            SecretAccessAudit(
                provider=provider,
                environment=environment,
                service_name=service_name,
                secret_name=secret_name,
                action="read",
            )
        )
        return record

    def list_secrets(self) -> list[SecretRecord]:
        return list(self._records.values())

    def list_audit_events(self) -> list[SecretAccessAudit]:
        return list(self._audit_log)


class InMemoryTelemetryStore:
    def __init__(self) -> None:
        self._events: list[TelemetryEvent] = []

    def append(self, event: TelemetryEvent) -> TelemetryEvent:
        validated = telemetry_event_adapter.validate_python(event)
        self._events.append(validated)
        return validated

    def list_events(self) -> list[TelemetryEvent]:
        return list(self._events)
