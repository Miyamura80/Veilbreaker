# Server README

This folder contains the current HTTP MVP for credential storage and telemetry. Product direction and longer-term decisions live in `src/server/spec.md`.

## Current Shape

The service is a small Python HTTP server with:

- plaintext in-memory secret storage
- stable secret fingerprinting
- typed telemetry event validation
- a small JSON API for secrets, event ingest, event listing, and usage summaries
- one derived policy rule for production-credential use in non-production

This is intentionally a fast-iteration baseline, not a production-ready service.

## Entrypoints

- HTTP server: `src/server/app.py`
- service logic: `src/server/service.py`
- typed models: `src/server/models.py`
- in-memory stores: `src/server/storage.py`
- fingerprint utility: `src/server/fingerprint.py`
- tests: `tests/server/test_server_mvp.py`

## Run Locally

```bash
uv run python -m src.server.app
```

The server listens on:

- `PORT` if set
- otherwise `8000`

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## HTTP API

### `GET /health`

Returns a basic liveliness response.

Example response:

```json
{"status": "ok"}
```

### `POST /v1/secrets`

Stores a secret record, computes a fingerprint, and emits a `credential_seen` event.

Request body:

```json
{
  "provider": "openai",
  "environment": "staging",
  "service_name": "web",
  "secret_name": "OPENAI_API_KEY",
  "raw_secret": "sk-demo"
}
```

### `GET /v1/secrets`

Lists all current secret records.

### `GET /v1/secrets/{provider}/{environment}/{service_name}?name=...`

Fetches one secret record by composite identity.

Example:

```bash
curl "http://127.0.0.1:8000/v1/secrets/openai/staging/web?name=OPENAI_API_KEY"
```

### `POST /v1/events/ingest`

Accepts a JSON object with an `events` list. Payloads are validated through the Pydantic event models before storage.

Example request:

```json
{
  "events": [
    {
      "event_type": "llm_request",
      "provider": "openai",
      "key_fingerprint": "abc123def456",
      "environment": "staging",
      "service_name": "web",
      "feature_name": "review",
      "model": "gpt-5.2",
      "status": "success",
      "estimated_cost_usd": 0.42
    }
  ]
}
```

### `GET /v1/events`

Returns the in-memory event log, including derived policy events.

### `GET /v1/usage-summary`

Returns grouped summaries derived from `llm_request` events.

Current grouping dimensions:

- provider
- environment
- service name
- key fingerprint
- feature name

Current metrics:

- request count
- error count
- total cost

## Event Types

The server currently supports:

- `credential_seen`
- `llm_request`
- `provider_fallback`
- `policy_violation`

## Derived Policy

The current automatic policy is:

- `prod_credential_used_in_non_prod`

If an `llm_request` event arrives from a non-`prod` environment and its fingerprint matches an active secret stored in `prod`, the service emits a `policy_violation` event automatically.

## Validation Behavior

The server currently:

- requires JSON object bodies for POST routes
- requires `events` to be a list for `/v1/events/ingest`
- returns `400` for malformed JSON or invalid event payloads
- returns `404` when a requested secret does not exist

## Demo Constraints

Current limitations are intentional:

- secrets are stored in plaintext
- all data is in memory only
- secrets and events are lost on restart
- no auth or access control
- secret list/get responses currently include `raw_secret`
- no dashboard UI yet

## Verification

Relevant checks:

```bash
uv run pytest tests/server/test_server_mvp.py
make ci
```

## Source of Truth

- product direction: `src/server/spec.md`
- runtime behavior: `src/server/app.py`
- domain logic: `src/server/service.py`
- tests: `tests/server/test_server_mvp.py`
