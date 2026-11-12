"""Servidor HTTP local para os testes do cliente: responde o que o teste mandar e guarda os pedidos.

É um servidor de verdade, na porta que o sistema der, para o cliente passar pela rede como faria
com o provedor; nada no cliente é trocado por mock.
"""

import json
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


@dataclass(frozen=True)
class StubResponse:
    status: int = 200
    body: bytes = b""
    content_type: str = "application/json"

    @classmethod
    def json(cls, payload: Any, status: int = 200) -> StubResponse:
        return cls(status=status, body=json.dumps(payload).encode())


@dataclass(frozen=True)
class RecordedRequest:
    method: str
    path: str
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body)


class StubServer:
    def __init__(self) -> None:
        self.responses: list[StubResponse] = []
        self.requests: list[RecordedRequest] = []
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._handler_class())
        self.url = f"http://127.0.0.1:{self._httpd.server_port}"
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def queue(self, *responses: StubResponse) -> None:
        """Respostas na ordem dos pedidos; sem resposta na fila, o servidor devolve 500."""
        self.responses.extend(responses)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()

    def _handler_class(self) -> type[BaseHTTPRequestHandler]:
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self._reply("GET")

            def do_POST(self) -> None:
                self._reply("POST")

            def do_DELETE(self) -> None:
                self._reply("DELETE")

            def _reply(self, method: str) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                stub.requests.append(RecordedRequest(method, self.path, self.rfile.read(length)))
                response = stub.responses.pop(0) if stub.responses else StubResponse(status=500)
                self.send_response(response.status)
                self.send_header("Content-Type", response.content_type)
                self.send_header("Content-Length", str(len(response.body)))
                self.end_headers()
                self.wfile.write(response.body)

            def log_message(self, format: str, *args: object) -> None:
                del format, args

        return Handler
