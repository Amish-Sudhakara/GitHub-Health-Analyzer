"""
Local Development Server for GitHub Student Health Analyzer.
Uses Python's built-in http.server to execute the exact same lambda_handler logic.
No third-party packages or AWS credentials required.
"""

import http.server
import json
import os
import sys
import urllib.parse
from lambda_function import lambda_handler

PORT = int(os.environ.get("PORT", 8000))


def load_local_env_file():
    """
    Optional lightweight .env loader using standard library only.
    Looks for .env in current directory or project root.
    """
    search_paths = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(__file__), "..", ".env"),
    ]
    for env_path in search_paths:
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip("'\"")
                            if key and key not in os.environ:
                                os.environ[key] = val
                print(f"[Local Server] Loaded environment variables from {os.path.abspath(env_path)}")
                break
            except Exception as e:
                print(f"[Local Server] Warning: Could not read {env_path}: {e}")


class LambdaHttpHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self._handle_request("OPTIONS")

    def do_GET(self):
        self._handle_request("GET")

    def do_POST(self):
        self._handle_request("POST")

    def _handle_request(self, method):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        raw_query = parsed_url.query
        parsed_qs = urllib.parse.parse_qs(raw_query)
        query_params = {k: v[0] for k, v in parsed_qs.items() if v}

        # Convert headers
        headers_dict = {k.lower(): v for k, v in self.headers.items()}

        # Build Lambda Function URL payload
        lambda_event = {
            "version": "2.0",
            "rawPath": path,
            "rawQueryString": raw_query,
            "headers": headers_dict,
            "queryStringParameters": query_params,
            "requestContext": {
                "http": {
                    "method": method,
                    "path": path,
                    "protocol": self.request_version,
                    "sourceIp": self.client_address[0],
                }
            },
        }

        # Invoke the exact Lambda handler
        response = lambda_handler(lambda_event, None)

        status_code = response.get("statusCode", 200)
        resp_headers = response.get("headers", {})
        body = response.get("body", "")

        self.send_response(status_code)
        for h_name, h_val in resp_headers.items():
            self.send_header(h_name, h_val)
        self.end_headers()

        if body:
            self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):
        # Clean logging
        sys.stderr.write(f"[Local Server] {self.address_string()} - {format % args}\n")


def run():
    load_local_env_file()
    token = os.environ.get("GITHUB_TOKEN")
    token_status = "Configured (Authenticated)" if token and not token.startswith("PASTE_") else "Not configured (Rate limited to 60 req/hr, GraphQL disabled)"

    server_address = ("127.0.0.1", PORT)
    httpd = http.server.HTTPServer(server_address, LambdaHttpHandler)
    print("=" * 65)
    print(f" GitHub Student Health Analyzer - Local Backend Server")
    print(f" Listening on http://localhost:{PORT}")
    print(f" GitHub Token: {token_status}")
    print(f" Test endpoint: http://localhost:{PORT}/analyze?username=octocat")
    print("=" * 65)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Local Server] Server stopped.")
        httpd.server_close()


if __name__ == "__main__":
    run()
