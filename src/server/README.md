# Agent Quick Start

This folder defines a developer-focused product for securely storing LLM credentials and observing their runtime usage. The product spec lives in `src/server/spec.md`.

Use this file when handing the work to a coding agent that should implement the first version quickly.

## Goal

Build the thinnest useful version of:

- secure storage for LLM API keys
- local fingerprinting for LLM API keys
- telemetry events for credential usage
- a small ingestion surface
- basic policy checks for environment drift

## Agent Task

Give a coding agent this objective:

> Implement the MVP described in `src/server/spec.md`. Start with Python support only. Add a minimal secret storage path, an SDK layer for retrieving credentials and instrumenting LLM calls, a small ingestion API for normalized events, and enough persistence and query support to show credential usage by environment, provider, fingerprint, and feature. Never expose raw API keys through telemetry, logs, or query responses.

## MVP Build Order

Implement in this order:

1. Fingerprint utility
2. Secret storage interface
3. Event schema and validators
4. SDK methods for `credential_seen`, `llm_request`, `provider_fallback`, and `policy_violation`
5. Ingestion endpoint
6. Persistence for normalized events and secrets
7. Simple queries for dashboard-ready summaries
8. Default rules for prod-in-non-prod and spend/error spikes

## Required First Interfaces

The first implementation should expose these concepts:

- `fingerprint_secret(secret: str) -> str`
- `store_secret(...)`
- `get_secret(...)`
- `credential_seen(...)`
- `llm_request(...)`
- `provider_fallback(...)`
- `policy_violation(...)`
- `ingest_events(...)`

Keep names flexible if the repo conventions push toward different module boundaries. The important part is stable event semantics, not exact function names.

## Minimal Data Model

The MVP should support these event types:

- `credential_seen`
- `llm_request`
- `provider_fallback`
- `policy_violation`

Use `src/server/spec.md` as the source of truth for fields and meaning.

## Minimal Policy Rules

Ship these first:

- production credential fingerprint seen in non-production environment
- sudden spend spike by key fingerprint
- sudden error spike by key fingerprint

If anomaly detection is too much for the first pass, use threshold-based rules and keep the rule engine replaceable.

## Guardrails

Do not implement:

- prompt or completion capture by default
- full tracing platform behavior
- provider-specific business logic beyond basic normalization

Do implement:

- encrypted secret storage
- secret read/write auditability
- local hashing/fingerprinting before telemetry emission
- explicit environment tagging
- provider and model tagging
- route or feature attribution when available
- safe handling for missing metadata

## Fastest Acceptable MVP

If speed matters more than architecture purity, the first working version can be:

- one Python package for SDK + server models
- one storage path for secrets
- one ingestion route
- one table or collection for events
- one table or collection for secrets
- one table or collection for alert state
- one summary query per dashboard card

That is enough to prove the product and validate the event model.

## What To Verify

Before calling the MVP complete, verify:

- raw API keys can be stored securely
- raw API keys never appear in logs, telemetry payloads, or query responses
- the same key yields the same fingerprint across runs
- different environments are distinguishable in queries
- request events can be grouped by provider, fingerprint, and feature
- policy violations are emitted for prod-in-non-prod usage

## Design Decisions Needed

These need explicit decisions before implementation goes too far:

1. Fingerprint format
Should this be plain `sha256(secret)[:12]`, or salted with a product-specific secret?

2. Secret storage backend
Should secrets be stored directly in the app database with encryption, or backed by an external KMS/secret manager?

3. Persistence model
Should events be stored in a relational table, a document store, or a log-first append model?

4. Cost calculation
Should cost be estimated in the SDK, or computed server-side from normalized pricing metadata?

5. Environment source of truth
Should environment be provided explicitly by the app, inferred from config, or both?

6. Tenant identity handling
Should tenant/workspace identifiers be stored raw, hashed, or disabled by default?

7. SDK ergonomics
Should the first SDK wrap provider clients automatically, or expose explicit instrumentation helpers only?

8. Alerting scope
Should the MVP stop at persisted violations, or also send notifications immediately?

9. Provider scope
Should the first pass support only OpenAI-style clients, or OpenAI plus Anthropic from day one?

## Recommended Defaults

If you want fast progress with low ambiguity, use these defaults:

- fingerprint format: unsalted truncated SHA-256
- secret storage backend: app-managed encrypted storage for MVP
- persistence: relational event table
- cost calculation: server-side when possible
- environment: explicit required field from the app
- tenant identity: hashed by default
- SDK ergonomics: explicit wrappers first
- alerting: persist violations first, notifications second
- provider scope: OpenAI first, Anthropic next

## Handoff Prompt

If you want to hand this to a coding agent directly, use:

```text
Implement the MVP in src/server based on src/server/spec.md and src/server/README.md.
Build only the first thin slice:
- encrypted secret storage
- local key fingerprinting
- normalized telemetry event models
- SDK helpers for credential_seen and llm_request
- ingestion endpoint
- persistence
- one query path for usage by environment/provider/fingerprint
- one policy rule for prod credential use in non-prod

Constraints:
- raw API keys may be stored only in the secret storage path
- never expose raw API keys in telemetry, logs, or query responses
- keep prompt/completion capture disabled
- optimize for a working Python-first MVP
- keep interfaces small and replaceable
```

## Source of Truth

- Product behavior and scope: `src/server/spec.md`
