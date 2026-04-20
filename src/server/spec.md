# Credential Storage and Observability for LLM API Keys

This document defines a developer-focused product for securely storing and observing how LLM API credentials are used across local development, CI, preview deployments, staging, and production.

## Summary

The product combines **secure credential storage** with **runtime usage telemetry** for AI provider credentials. It helps developers, platform teams, and security teams answer:

- Which API key is being used by which service and environment?
- Which route, feature, or workflow is driving token spend?
- Are production credentials being used from the wrong environment?
- Did a fallback provider or rotated key silently take over?
- Which key fingerprints are associated with failures, latency spikes, or abnormal usage?

## Problem

Developers commonly store LLM credentials in `.env` files:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- provider-specific Azure or hosted inference keys

Once those values are injected into an app, visibility is usually poor. Teams often lack a clean way to observe:

- environment-to-key mapping
- usage by feature or route
- credential drift between local, preview, staging, and prod
- abnormal or suspicious usage
- spend and reliability by provider, model, and key fingerprint

Existing logging or APM products can show request traces, but they usually do not provide a first-class model for credential identity, environment hygiene, or LLM cost governance.

## Product Goal

Provide a system that securely stores LLM credentials and makes their usage observable and governable at runtime.

## Non-Goals

- Vault replacement
- Full prompt/response observability
- Full agent trace visualization
- DLP or secret scanning of source code
- Enforcement of provider-side IAM policies

## Primary Users

- Developers building AI features into web apps
- Platform teams managing shared LLM infrastructure
- Security teams verifying environment isolation
- Engineering managers tracking spend and reliability

## Core Use Cases

### 1. Environment Hygiene

Detect when a production credential is used from:

- local development
- preview deployments
- CI jobs
- staging services

### 2. Cost Attribution

Break down spend by:

- provider
- model
- environment
- service
- route
- feature
- tenant or workspace

### 3. Reliability Investigation

Correlate errors, rate limits, latency spikes, and fallback events with:

- key fingerprint
- provider
- model
- environment

### 4. Credential Rotation Visibility

Show when traffic moved from one key fingerprint to another and whether the new key changed:

- latency
- success rate
- spend
- rate limit behavior

### 5. Suspicious Usage Detection

Alert when:

- a key fingerprint appears in a new environment
- a dormant key becomes active again
- request volume spikes unexpectedly
- a low-trust surface starts using a production credential

## Product Shape

The product has four parts:

1. A credential storage layer for securely storing provider secrets.
2. An SDK that retrieves credentials and wraps or annotates LLM client initialization and request execution.
3. A telemetry ingestion API that receives normalized credential-usage events.
4. A dashboard and alerting layer for usage, anomalies, and policy violations.

## Key Constraints

The system must support storing raw secrets securely, but must never expose them through telemetry, logs, or query surfaces.

Allowed derived data:

- provider name
- key fingerprint derived from a one-way hash
- environment label
- service name
- route or feature name
- model name
- token counts
- estimated cost
- latency
- status and error category
- deployment metadata

Disallowed data by default:

- full prompts
- full completions
- `.env` contents
- request headers containing secrets

Raw secrets are allowed only inside the credential storage system and in the runtime path that needs them to make provider calls.

## Secret Storage Requirements

The storage layer should support:

- secure storage of provider API keys
- environment scoping
- service or project scoping
- key rotation
- key activation and deactivation
- audit history for reads and writes

The storage layer should not require `.env` files as the long-term source of truth. `.env` loading can remain a bootstrap path for local development and migration.

## Identity Model

Credential identity in telemetry is based on a stable fingerprint derived locally in the app process.

Example:

```text
fingerprint = sha256(api_key)[:12]
```

The exact truncation policy can vary, but the design goal is:

- stable within the product
- irreversible in practice
- short enough for dashboards

## Event Model

### `credential_seen`

Emitted when the app initializes or first uses a credential in a process.

Fields:

- `timestamp`
- `provider`
- `key_fingerprint`
- `environment`
- `service_name`
- `deployment_id`
- `runtime`
- `source`

`source` examples:

- `.env`
- `stored_secret`
- `injected_secret`
- `platform_env`

### `llm_request`

Emitted for each provider request.

Fields:

- `timestamp`
- `provider`
- `key_fingerprint`
- `environment`
- `service_name`
- `feature_name`
- `route_name`
- `workflow_name`
- `tenant_id` or `workspace_id`
- `model`
- `status`
- `error_category`
- `latency_ms`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `estimated_cost_usd`
- `request_id`
- `trace_id`

### `provider_fallback`

Emitted when one provider/model/key path fails and another path is used.

Fields:

- `timestamp`
- `from_provider`
- `from_key_fingerprint`
- `from_model`
- `to_provider`
- `to_key_fingerprint`
- `to_model`
- `reason`
- `service_name`
- `feature_name`
- `trace_id`

### `policy_violation`

Emitted when an app-side rule or backend rule detects unsafe usage.

Fields:

- `timestamp`
- `policy_name`
- `severity`
- `provider`
- `key_fingerprint`
- `environment`
- `service_name`
- `details`

### `credential_rotation`

Emitted when traffic shifts from one key fingerprint to another.

Fields:

- `timestamp`
- `provider`
- `old_key_fingerprint`
- `new_key_fingerprint`
- `environment`
- `service_name`
- `rotation_trigger`

## SDK Instrumentation Points

Minimal developer instrumentation should happen in these places:

1. LLM client creation
2. Request wrapper around each provider call
3. Fallback or retry path
4. App boot or worker boot
5. Optional route or feature annotation middleware

### Python Example

```python
from hashlib import sha256
import os


def fingerprint(key: str) -> str:
    return sha256(key.encode()).hexdigest()[:12]


provider = "openai"
api_key = os.getenv("OPENAI_API_KEY", "")
key_fingerprint = fingerprint(api_key)

telemetry.credential_seen(
    provider=provider,
    key_fingerprint=key_fingerprint,
    environment="staging",
    service_name="web",
    source=".env",
)

result = llm_client.responses.create(...)

telemetry.llm_request(
    provider=provider,
    key_fingerprint=key_fingerprint,
    environment="staging",
    service_name="web",
    feature_name="code_review",
    route_name="/api/review",
    model="gpt-5.2",
    status="success",
    latency_ms=912,
    prompt_tokens=2100,
    completion_tokens=480,
    total_tokens=2580,
    estimated_cost_usd=0.019,
)
```

## Detection Rules

Initial product rules should support:

- prod fingerprint used in non-prod environment
- fingerprint first seen in a new service
- request volume anomaly by fingerprint
- spend anomaly by fingerprint or feature
- error-rate anomaly by fingerprint, provider, or model
- repeated provider fallback from one credential path
- dormant fingerprint reactivated after long inactivity

## Dashboard Views

The first release should include:

- Credential inventory by provider and environment
- Spend by key fingerprint, service, feature, and model
- Error and latency by key fingerprint
- Recent policy violations
- Credential rotation timeline
- Environment mismatch table

## Alerting

Alerts should support:

- Slack or email delivery
- threshold-based triggers
- anomaly-based triggers
- per-environment policies
- suppression windows during migrations or planned rotations

## Security and Privacy Requirements

- Never include raw secrets in telemetry events
- Never log full request headers containing credentials
- Hash or fingerprint locally before telemetry emission
- Redact freeform error payloads that may contain secrets
- Allow tenant identifiers to be hashed or disabled
- Provide a strict mode that disables prompt/completion capture entirely
- Encrypt stored secrets at rest
- Restrict secret reads to the services or principals that need them
- Record audit events for secret creation, update, access, and deactivation

## Open Design Decisions

- Whether fingerprinting should include a product-specific salt
- Whether secret storage is built in directly or backed by an external KMS/secret store
- Whether tenant identifiers are raw, hashed, or customer-defined
- Whether cost is estimated client-side or normalized server-side
- Whether the SDK auto-wraps popular clients or requires explicit wrappers
- Whether local development events are batched or streamed immediately

## MVP Scope

The MVP should deliver:

- one credential storage path for Python apps
- one SDK path for Python web apps
- support for OpenAI and Anthropic style API calls
- local fingerprint generation
- request event ingestion
- basic dashboard views
- three default alerts

Suggested default alerts:

- prod credential in non-prod
- spend spike by fingerprint
- error spike by fingerprint

## Success Metrics

- Time to first usable dashboard under 30 minutes
- At least 90% of LLM requests mapped to a key fingerprint
- Clear environment attribution for each fingerprint
- Alert precision high enough to avoid routine suppression
- Teams can identify the top cost-driving features without raw log inspection

## Acceptance Criteria

- A developer can install the SDK and see credential usage by environment
- A developer can store and retrieve an LLM credential securely through the product
- A developer can attribute spend and failures to a key fingerprint
- A security or platform user can detect prod/non-prod credential drift
- No raw API keys are stored in telemetry events
- Fallback and rotation events are visible on a timeline

## Positioning

Working positioning statement:

> Secure storage and observability for LLM credentials: store API keys safely and see which ones are used where, by what code path, and at what cost.

Shorter version:

> Credential vault plus observability for LLM apps.
