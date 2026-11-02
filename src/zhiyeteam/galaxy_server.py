"""Loopback-only static UI + authenticated same-origin JSON adapter."""

import json
import mimetypes
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


def serve(api, assets):
    assets = Path(assets).resolve()
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                f"default-src 'self'; script-src 'self' 'nonce-{token}'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; worker-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.valid_host():
                return self.reply(403, b"Forbidden", "text/plain")
            path = unquote(urlsplit(self.path).path)
            file = (assets / (path.lstrip("/") or "index.html")).resolve()
            if not file.is_relative_to(assets) or not file.is_file():
                return self.reply(404, b"Not found", "text/plain")
            body = file.read_bytes()
            if file.name == "index.html":
                body = body.replace(
                    b"<head>",
                    (
                        f'<head><script nonce="{token}">window.ZHIYE_TOKEN={json.dumps(token)};</script>'
                    ).encode(),
                )
            mime = (
                "text/javascript"
                if file.suffix == ".js"
                else mimetypes.guess_type(file.name)[0] or "application/octet-stream"
            )
            self.reply(
                200,
                body,
                mime + ("; charset=utf-8" if mime.startswith("text/") else ""),
            )

        def do_POST(self):
            origin = self.headers.get("Origin")
            if (
                not self.valid_host()
                or self.headers.get("X-Zhiye-Token") != token
                or (
                    origin is not None
                    and origin != f"http://127.0.0.1:{self.server.server_port}"
                )
            ):
                return self.reply(403, b"Forbidden", "text/plain")
            if not self.path.startswith("/api/"):
                return self.reply(404, b"Not found", "text/plain")
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 2 * 1024 * 1024:
                    raise ValueError("请求过大或为空")
                payload = json.loads(self.rfile.read(length))
                result = api.invoke(self.path.removeprefix("/api/"), payload)
                body = json.dumps(result, ensure_ascii=False).encode("utf-8")
                self.reply(200, body, "application/json; charset=utf-8")
            except (ValueError, UnicodeError) as exc:
                self.reply(
                    400,
                    json.dumps({"ok": False, "error": str(exc)}).encode(),
                    "application/json",
                )

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}"
