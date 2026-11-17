"""
End-to-End Local Server Integration Test.
Starts local_server.py on an ephemeral port, executes real HTTP requests, and verifies responses.
"""

import http.client
import json
import socket
import threading
import time
import urllib.parse
from http.server import HTTPServer
from local_server import LambdaHttpHandler


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def run_e2e_tests():
    port = get_free_port()
    server = HTTPServer(('127.0.0.1', port), LambdaHttpHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.3)

    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)

    print(f"Testing local HTTP server on port {port}...")

    # 1. Test OPTIONS Preflight
    conn.request('OPTIONS', '/analyze')
    res = conn.getresponse()
    assert res.status == 204, f"Expected 204, got {res.status}"
    cors_origin = res.getheader('Access-Control-Allow-Origin')
    assert cors_origin is not None, "Missing Access-Control-Allow-Origin header"
    res.read()
    print("✓ OPTIONS preflight returned 204 with CORS headers")

    # 2. Test Root Health Check
    conn.request('GET', '/')
    res = conn.getresponse()
    assert res.status == 200, f"Expected 200, got {res.status}"
    body = json.loads(res.read().decode('utf-8'))
    assert body.get('status') == 'ok', "Health check body missing status: ok"
    print("✓ GET / returned 200 health check")

    # 3. Test Invalid Username Validation
    conn.request('GET', '/analyze?username=-invalid')
    res = conn.getresponse()
    assert res.status == 400, f"Expected 400, got {res.status}"
    body = json.loads(res.read().decode('utf-8'))
    assert body.get('code') == 'INVALID_USERNAME', f"Unexpected code: {body.get('code')}"
    print("✓ GET /analyze with invalid username returned 400 INVALID_USERNAME")

    # 4. Test Method Not Allowed
    conn.request('POST', '/analyze?username=octocat', body='{}')
    res = conn.getresponse()
    assert res.status == 405, f"Expected 405, got {res.status}"
    res.read()
    print("✓ POST /analyze returned 405 Method Not Allowed")

    conn.close()
    server.shutdown()
    print("All E2E Local Server tests passed successfully!")


if __name__ == '__main__':
    run_e2e_tests()
