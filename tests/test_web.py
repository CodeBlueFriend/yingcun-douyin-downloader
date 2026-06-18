from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

from web_app import WebHandler


def _local_server() -> ThreadingHTTPServer:
    try:
        return ThreadingHTTPServer(("127.0.0.1", 0), WebHandler)
    except PermissionError:
        pytest.skip("current sandbox does not allow binding a loopback port")


def test_web_health_endpoint() -> None:
    server = _local_server()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
        connection.request("GET", "/api/health")
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))

        assert response.status == 200
        assert payload == {"status": "ok"}
        assert response.getheader("Cache-Control") == "no-store"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_rejects_empty_parse_request() -> None:
    server = _local_server()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        body = json.dumps({"share_text": ""}).encode("utf-8")
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
        connection.request(
            "POST",
            "/api/parse",
            body=body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(body))},
        )
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))

        assert response.status == 400
        assert "请粘贴" in payload["error"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
