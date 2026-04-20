# REST API

This document describes the current HTTP surface exposed by `src/server/app.py`. It is an API reference for the local MVP, not a long-term compatibility guarantee.

## Entrypoint

Run locally:

```bash
uv run python -m src.server.app
```

Base URL:

```text
http://127.0.0.1:8000
```

## Endpoints

### `GET /health`

Returns a basic liveliness response.

Example response:

```json
{"status": "ok"}
```

### `POST /v1/secrets`

Stores a secret record, computes its fingerprint, and emits a `credential_seen` event.

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

Response shape:

- stored secret record
- includes `key_fingerprint`
- currently includes `raw_secret`

### `GET /v1/secrets`

Lists all current secret records.

Response shape:

```json
{
  "items": []
}
```

### `GET /v1/secrets/{provider}/{environment}/{service_name}?name=...`

Fetches a single secret record by composite identity.

Required query parameter:

- `name`

Example:

```bash
curl "http://127.0.0.1:8000/v1/secrets/openai/staging/web?name=OPENAI_API_KEY"
```

### `POST /v1/events/ingest`

Accepts a JSON object containing an `events` list. Each item is validated against the typed event models before storage.

Supported event types:

- `credential_seen`
- `llm_request`
- `provider_fallback`
- `policy_violation`

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

Response shape:

```json
{
  "items": []
}
```

Derived events may be added during ingest.

### `GET /v1/events`

Returns the in-memory event log.

Response shape:

```json
{
  "items": []
}
```

This can include both directly ingested events and derived policy events.

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

Response shape:

```json
{
  "items": []
}
```

## Derived Policy Behavior

The current automatic policy is:

- `prod_credential_used_in_non_prod`

If an `llm_request` event arrives from a non-`prod` environment and its fingerprint matches an active secret stored in `prod`, the service emits a `policy_violation` event automatically.

## Validation Behavior

The HTTP layer:

- requires JSON object bodies for POST routes
- requires `events` to be a list for `/v1/events/ingest`
- returns `400` for malformed JSON or invalid payloads
- returns `400` when the secret lookup is missing the `name` query parameter
- returns `404` when a requested secret does not exist

## Demo Constraints

Current limitations are intentional:

- plaintext secret storage
- no persistence across restarts
- no auth
- no access control
- secret responses currently include `raw_secret`

## Source of Truth

- HTTP handler: `src/server/app.py`
- service logic: `src/server/service.py`
- tests: `tests/server/test_server_mvp.py`
