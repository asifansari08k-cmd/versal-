import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler


# GitHub raw file containing the current Ngrok URL
BACKEND_URL_FILE = (
    "https://raw.githubusercontent.com/"
    "themagmalord333-oss/MAGMA-API/main/backend-url.json"
)


def get_backend_url():
    url = f"{BACKEND_URL_FILE}?t={time.time_ns()}"

    request = urllib.request.Request(
        url,
        headers={
            "Cache-Control": "no-cache",
            "User-Agent": "MAGMA-API-Proxy"
        }
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))

    backend = data.get("url", "").strip().rstrip("/")

    if not backend.startswith("https://"):
        raise ValueError("Invalid backend URL")

    return backend


class handler(BaseHTTPRequestHandler):

    def _proxy(self):
        try:
            backend = get_backend_url()

            # Forward the complete request path and query string
            target_url = backend + self.path

            body = None

            content_length = self.headers.get("Content-Length")

            if content_length:
                body = self.rfile.read(int(content_length))

            headers = {}

            for key, value in self.headers.items():
                if key.lower() not in {
                    "host",
                    "content-length",
                    "connection",
                }:
                    headers[key] = value

            request = urllib.request.Request(
                target_url,
                data=body,
                headers=headers,
                method=self.command,
            )

            with urllib.request.urlopen(request, timeout=50) as response:

                response_body = response.read()

                self.send_response(response.status)

                content_type = response.headers.get(
                    "Content-Type",
                    "application/json"
                )

                self.send_header(
                    "Content-Type",
                    content_type
                )

                self.send_header(
                    "Access-Control-Allow-Origin",
                    "*"
                )

                self.send_header(
                    "Access-Control-Allow-Methods",
                    "GET,POST,PUT,PATCH,DELETE,OPTIONS"
                )

                self.send_header(
                    "Access-Control-Allow-Headers",
                    "*"
                )

                self.end_headers()

                self.wfile.write(response_body)

        except urllib.error.HTTPError as e:

            error_body = e.read()

            self.send_response(e.code)

            self.send_header(
                "Content-Type",
                e.headers.get(
                    "Content-Type",
                    "application/json"
                )
            )

            self.send_header(
                "Access-Control-Allow-Origin",
                "*"
            )

            self.end_headers()

            self.wfile.write(error_body)

        except Exception as e:

            self.send_response(502)

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.send_header(
                "Access-Control-Allow-Origin",
                "*"
            )

            self.end_headers()

            response = {
                "status": False,
                "error": "Backend unavailable",
                "message": str(e),
            }

            self.wfile.write(
                json.dumps(response).encode("utf-8")
            )

    def do_GET(self):
        self._proxy()

    def do_POST(self):
        self._proxy()

    def do_PUT(self):
        self._proxy()

    def do_PATCH(self):
        self._proxy()

    def do_DELETE(self):
        self._proxy()

    def do_OPTIONS(self):
        self.send_response(204)

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET,POST,PUT,PATCH,DELETE,OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "*"
        )

        self.end_headers()