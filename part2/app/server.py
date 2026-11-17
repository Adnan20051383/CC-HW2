"""HTTP API for the lab queue."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app.queue import join, take


def serve(host: str, port: int, data_dir: str) -> None:
    """Listen until the process is stopped. Use join and take from app.queue."""

    queue_path = Path(data_dir) / "queue.txt"
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    class QueueHandler(BaseHTTPRequestHandler):

        def send_text(self, status: int, body: str) -> None:
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:
            if self.path == "/health":
                self.send_text(200, "ok")
            else:
                self.send_text(404, "not found")

        def do_POST(self) -> None:
            if self.path == "/join":
                length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(length)

                try:
                    data = json.loads(raw_body.decode("utf-8"))

                    if not isinstance(data, dict):
                        raise ValueError("Invalid request")

                    name = data.get("name")

                    if not isinstance(name, str):
                        raise ValueError("Invalid name")

                    ticket = join(queue_path, name)

                except (ValueError, UnicodeDecodeError):
                    self.send_text(400, "invalid name")
                    return

                self.send_text(200, str(ticket))
                return

            if self.path == "/next":
                try:
                    name = take(queue_path)
                except LookupError:
                    self.send_text(404, "empty")
                    return

                self.send_text(200, name)
                return

            self.send_text(404, "not found")

        def log_message(self, format: str, *args) -> None:
            pass

    with ThreadingHTTPServer((host, port), QueueHandler) as server:
        server.serve_forever()


def main() -> None:
    import os

    port = int(os.environ.get("PORT", "8000"))
    data_dir = os.environ.get("DATA_DIR", "/data")
    serve("0.0.0.0", port, data_dir)


if __name__ == "__main__":
    main()# Compose rebuild verification
