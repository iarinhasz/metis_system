"""Provedor HTTP local: exercita as SDKs reais sem credenciais nem chamadas externas."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import Empty, Queue
from threading import Thread
from time import sleep
from typing import Any


@dataclass(frozen=True)
class Response:
    payload: dict[str, Any]
    status: int = 200
    delay: float = 0


class ProviderServer:
    def __init__(self) -> None:
        self.responses: Queue[Response] = Queue()
        self.requests: list[dict[str, Any]] = []
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.url = f"http://127.0.0.1:{self.httpd.server_port}"

    def queue(self, *responses: Response) -> None:
        for response in responses:
            self.responses.put(response)

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                server.requests.append(json.loads(body))
                try:
                    response = server.responses.get_nowait()
                except Empty:
                    response = Response({"error": {"message": "Fila de respostas vazia"}}, 500)
                sleep(response.delay)
                body = json.dumps(response.payload).encode()
                self.send_response(response.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except BrokenPipeError, ConnectionResetError, ConnectionAbortedError:
                    pass  # Esperado quando a SDK encerra a conexão por timeout.

            def log_message(self, format: str, *args: object) -> None:
                del format, args

        return Handler


@contextmanager
def provider_server() -> Iterator[ProviderServer]:
    server = ProviderServer()
    thread = Thread(target=server.httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.httpd.shutdown()
        server.httpd.server_close()
        thread.join(timeout=5)
