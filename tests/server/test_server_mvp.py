import json
import threading
from collections.abc import Generator
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pytest
from pydantic import ValidationError

from src.server import (
    PolicyViolationEvent,
    TelemetryService,
    build_server,
    fingerprint_secret,
)
from src.server.app import TelemetryRequestHandler


def test_fingerprint_secret_is_stable() -> None:
    first = fingerprint_secret("sk-test-secret")
    second = fingerprint_secret("sk-test-secret")

    assert first == second
    assert len(first) == 12


def test_fingerprint_secret_rejects_empty_values() -> None:
    with pytest.raises(ValueError, match="secret must be non-empty"):
        fingerprint_secret("")


def test_store_and_read_secret_records_audit_events() -> None:
    service = TelemetryService()

    record = service.store_secret(
        provider="openai",
        environment="staging",
        service_name="web",
        secret_name="OPENAI_API_KEY",
        raw_secret="sk-live-123",
    )
    loaded = service.get_secret(
        provider="openai",
        environment="staging",
        service_name="web",
        secret_name="OPENAI_API_KEY",
    )

    assert record.key_fingerprint == loaded.key_fingerprint
    assert loaded.raw_secret == "sk-live-123"

    actions = [event.action for event in service.secret_store.list_audit_events()]
    assert actions == ["create", "read"]


def test_llm_request_requires_status_and_model() -> None:
    service = TelemetryService()

    with pytest.raises(ValidationError):
        service.llm_request(
            provider="openai",
            key_fingerprint="abc123",
            environment="staging",
            service_name="web",
        )


def test_prod_credential_used_in_non_prod_emits_policy_violation() -> None:
    service = TelemetryService()
    prod_record = service.store_secret(
        provider="openai",
        environment="prod",
        service_name="web",
        secret_name="OPENAI_API_KEY",
        raw_secret="sk-prod-secret",
    )

    service.llm_request(
        provider="openai",
        key_fingerprint=prod_record.key_fingerprint,
        environment="staging",
        service_name="web",
        feature_name="code_review",
        model="gpt-5.2",
        status="success",
        estimated_cost_usd=0.1,
    )

    policy_events = [
        event
        for event in service.list_events()
        if isinstance(event, PolicyViolationEvent)
    ]
    assert len(policy_events) == 1
    assert policy_events[0].policy_name == "prod_credential_used_in_non_prod"


def test_usage_summary_groups_requests_by_fingerprint_and_feature() -> None:
    service = TelemetryService()
    fingerprint = fingerprint_secret("sk-shared-secret")

    service.llm_request(
        provider="openai",
        key_fingerprint=fingerprint,
        environment="staging",
        service_name="web",
        feature_name="review",
        model="gpt-5.2",
        status="success",
        estimated_cost_usd=0.25,
    )
    service.llm_request(
        provider="openai",
        key_fingerprint=fingerprint,
        environment="staging",
        service_name="web",
        feature_name="review",
        model="gpt-5.2",
        status="error",
        estimated_cost_usd=0.15,
    )

    summaries = service.usage_summary()

    assert len(summaries) == 1
    assert summaries[0].requests == 2
    assert summaries[0].errors == 1
    assert summaries[0].total_cost_usd == 0.4


def test_ingest_events_accepts_dict_payloads() -> None:
    service = TelemetryService()

    ingested = service.ingest_events(
        [
            {
                "event_type": "credential_seen",
                "provider": "openai",
                "key_fingerprint": "abc123def456",
                "environment": "local",
                "service_name": "web",
                "source": ".env",
            }
        ]
    )

    assert len(ingested) == 1
    assert ingested[0].event_type == "credential_seen"


@pytest.fixture
def http_server() -> Generator[tuple[object, str], None, None]:
    TelemetryRequestHandler.service = TelemetryService()
    server = build_server(host="127.0.0.1", port=0)
    host = str(server.server_address[0])
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, f"http://{host}:{port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_http_healthcheck(http_server: tuple[object, str]) -> None:
    _, base_url = http_server

    with urlopen(f"{base_url}/health") as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload == {"status": "ok"}


def test_http_secret_round_trip_and_usage_summary(
    http_server: tuple[object, str],
) -> None:
    _, base_url = http_server

    create_secret_request = Request(
        url=f"{base_url}/v1/secrets",
        data=json.dumps(
            {
                "provider": "openai",
                "environment": "staging",
                "service_name": "web",
                "secret_name": "OPENAI_API_KEY",
                "raw_secret": "sk-demo-123",
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(create_secret_request) as response:  # noqa: S310
        secret_payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 201
    assert secret_payload["raw_secret"] == "sk-demo-123"

    secret_name = quote("OPENAI_API_KEY")
    with urlopen(  # noqa: S310
        f"{base_url}/v1/secrets/openai/staging/web?name={secret_name}"
    ) as response:
        fetched_secret = json.loads(response.read().decode("utf-8"))

    assert fetched_secret["key_fingerprint"] == secret_payload["key_fingerprint"]

    ingest_request = Request(
        url=f"{base_url}/v1/events/ingest",
        data=json.dumps(
            {
                "events": [
                    {
                        "event_type": "llm_request",
                        "provider": "openai",
                        "key_fingerprint": secret_payload["key_fingerprint"],
                        "environment": "staging",
                        "service_name": "web",
                        "feature_name": "review",
                        "model": "gpt-5.2",
                        "status": "success",
                        "estimated_cost_usd": 0.3,
                    }
                ]
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(ingest_request) as response:  # noqa: S310
        ingest_payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 201
    assert ingest_payload["items"][0]["event_type"] == "llm_request"

    with urlopen(f"{base_url}/v1/usage-summary") as response:  # noqa: S310
        summary_payload = json.loads(response.read().decode("utf-8"))

    assert summary_payload["items"][0]["requests"] == 1
    assert summary_payload["items"][0]["total_cost_usd"] == 0.3


def test_http_returns_400_for_invalid_event_payload(
    http_server: tuple[object, str],
) -> None:
    _, base_url = http_server

    request = Request(
        url=f"{base_url}/v1/events/ingest",
        data=json.dumps({"events": [{"event_type": "llm_request"}]}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with pytest.raises(HTTPError) as exc_info:
        urlopen(request)  # noqa: S310

    assert exc_info.value.code == 400
