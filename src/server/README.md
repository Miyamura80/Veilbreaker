# Server README

This folder contains the current HTTP MVP for credential storage and telemetry. Product direction lives in `src/server/spec.md`. Concrete endpoint behavior lives in `src/server/REST_API.md`.

## Current Shape

The server currently provides:

- plaintext in-memory secret storage for demo use
- stable secret fingerprinting
- typed telemetry event validation
- one JSON HTTP service
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

The server listens on `PORT` if set, otherwise `8000`.

Quick check:

```bash
curl http://127.0.0.1:8000/health
```

## Runtime Notes

- secrets are stored in plaintext
- all state is in memory only
- secrets and events are lost on restart
- there is no auth or access control
- secret list/get responses currently include `raw_secret`

## Verification

```bash
uv run pytest tests/server/test_server_mvp.py
make ci
```

## Source of Truth

- product direction: `src/server/spec.md`
- REST API contract: `src/server/REST_API.md`
- runtime behavior: `src/server/app.py`
- domain logic: `src/server/service.py`
- tests: `tests/server/test_server_mvp.py`
