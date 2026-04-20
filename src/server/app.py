import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import unquote, urlparse

from pydantic import ValidationError

from .service import TelemetryService


class TelemetryRequestHandler(BaseHTTPRequestHandler):
    service = TelemetryService()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path_parts = self._path_parts(parsed.path)

        if parsed.path == "/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return

        if parsed.path == "/v1/secrets":
            secrets = [
                secret.model_dump(mode="json") for secret in self.service.list_secrets()
            ]
            self._send_json(HTTPStatus.OK, {"items": secrets})
            return

        if (
            len(path_parts) == 5
            and path_parts[0] == "v1"
            and path_parts[1] == "secrets"
        ):
            _, _, provider, environment, service_name = path_parts[:5]
            secret_name = parsed.query.removeprefix("name=") if parsed.query else None
            if not secret_name:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "missing required query parameter: name"},
                )
                return

            try:
                secret = self.service.get_secret(
                    provider=provider,
                    environment=environment,
                    service_name=service_name,
                    secret_name=unquote(secret_name),
                )
            except KeyError:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "secret not found"})
                return
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            self._send_json(HTTPStatus.OK, secret.model_dump(mode="json"))
            return

        if parsed.path == "/v1/events":
            events = [
                event.model_dump(mode="json") for event in self.service.list_events()
            ]
            self._send_json(HTTPStatus.OK, {"items": events})
            return

        if parsed.path == "/v1/usage-summary":
            items = [
                summary.model_dump(mode="json")
                for summary in self.service.usage_summary()
            ]
            self._send_json(HTTPStatus.OK, {"items": items})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/v1/secrets":
            payload = self._read_json_body()
            if payload is None:
                return

            try:
                record = self.service.store_secret(**payload)
            except TypeError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            self._send_json(HTTPStatus.CREATED, record.model_dump(mode="json"))
            return

        if self.path == "/v1/events/ingest":
            payload = self._read_json_body()
            if payload is None:
                return

            events = payload.get("events")
            if not isinstance(events, list):
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "body must include an events list"},
                )
                return

            try:
                ingested = self.service.ingest_events(events)
            except ValidationError as exc:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "invalid event payload", "details": exc.errors()},
                )
                return

            self._send_json(
                HTTPStatus.CREATED,
                {"items": [event.model_dump(mode="json") for event in ingested]},
            )
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json_body(self) -> dict[str, Any] | None:
        content_length = self.headers.get("Content-Length")
        if content_length is None:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "missing Content-Length header"},
            )
            return None

        try:
            body = self.rfile.read(int(content_length))
            payload = json.loads(body.decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON body"})
            return None

        if not isinstance(payload, dict):
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "JSON body must be an object"},
            )
            return None
        return payload

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    @staticmethod
    def _path_parts(path: str) -> list[str]:
        return [part for part in path.strip("/").split("/") if part]


def build_server(*, host: str = "0.0.0.0", port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), TelemetryRequestHandler)


def main() -> None:
    port = int(os.getenv("PORT", "8000"))
    server = build_server(port=port)
    print(f"Telemetry HTTP service listening on 0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
