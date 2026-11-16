"""Servidor HTTP local para testar clientes sem chamar provedores externos."""

import threading
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@dataclass(frozen=True)
class StubResponse:
    body: bytes
    status: int = 200
    headers: dict[str, str] | None = None


@dataclass(frozen=True)
class RecordedRequest:
    method: str
    path: str
    headers: dict[str, str]


class APIStub:
    def __init__(self) -> None:
        self.responses: deque[StubResponse] = deque()
        self.requests: list[RecordedRequest] = []
        self.lock = threading.Lock()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def queue(self, *responses: StubResponse) -> None:
        with self.lock:
            self.responses.extend(responses)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        api = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                with api.lock:
                    api.requests.append(
                        RecordedRequest("GET", self.path, dict(self.headers.items()))
                    )
                    response = api.responses.popleft() if api.responses else StubResponse(b"", 500)
                self.send_response(response.status)
                for name, value in (response.headers or {}).items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(response.body)))
                self.end_headers()
                self.wfile.write(response.body)

            def log_message(self, format: str, *args: object) -> None:
                del format, args

        return Handler


@contextmanager
def api_stub() -> Iterator[APIStub]:
    api = APIStub()
    api.start()
    try:
        yield api
    finally:
        api.stop()
