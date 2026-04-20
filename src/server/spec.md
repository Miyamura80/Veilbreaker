# Credential Storage and Observability for LLM API Keys

This document defines the product direction for storing LLM credentials and making their usage observable and governable at runtime. The current local baseline lives in `src/server/README.md`, `src/server/app.py`, `src/server/service.py`, `src/server/models.py`, and `tests/server/test_server_mvp.py`.

## Implemented Baseline

Already implemented in `src/server/`:

- plaintext in-memory secret storage for demo use
- stable key fingerprinting
- typed event models for:
  - `credential_seen`
  - `llm_request`
  - `provider_fallback`
  - `policy_violation`
- HTTP endpoints for:
  - health
  - secret create/list/get
  - event ingest/list
  - usage summary
- one derived policy rule:
  - `prod_credential_used_in_non_prod`

This spec intentionally does **not** restate those mechanics in detail.

## Product Goal

Evolve the current demo server into a production-viable system for storing LLM credentials and making their usage observable and governable at runtime.

## Non-Goals

- Vault replacement
- Full prompt/response observability
- Full agent trace visualization
- DLP or source-code secret scanning
- Provider-side IAM enforcement

## Primary Users

- developers building AI features into web apps
- platform teams managing shared LLM infrastructure
- security teams verifying environment isolation
- engineering managers tracking spend and reliability

## Core Use Cases

- environment hygiene
- cost attribution
- reliability investigation
- credential rotation visibility
- suspicious usage detection

## Key Constraint

Raw secrets may exist only in the credential storage path and the runtime path that needs them. They must never appear in telemetry events, logs, or general query surfaces.

## Identity Model

Telemetry identity should continue to be based on a stable, short fingerprint derived locally from the secret.

Example:

```text
fingerprint = sha256(api_key)[:12]
```

## Event Model Direction

The existing event types remain the right baseline:

- `credential_seen`
- `llm_request`
- `provider_fallback`
- `policy_violation`

Likely next addition:

- `credential_rotation`

## Open Design Decisions

- Whether fingerprinting should include a product-specific salt
- Whether secret storage should be app-managed or backed by external KMS/secret storage
- Whether tenant identifiers should be raw, hashed, or customer-defined
- Whether cost should be estimated client-side or normalized server-side
- Whether the SDK should auto-wrap common clients or stay explicit
- Whether local development events should be batched or streamed immediately
- Whether secret reads should ever return raw values after the demo phase

## Positioning

Working positioning statement:

> Secure storage and observability for LLM credentials: store API keys safely and see which ones are used where, by what code path, and at what cost.

Shorter version:

> Credential vault plus observability for LLM apps.
