from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from web_app import WebHandler, resolve_output_dir


def test_resolve_absolute_output_directory(tmp_path: Path) -> None:
    target = tmp_path / "custom-downloads"

    assert resolve_output_dir(str(target)) == target
    assert target.is_dir()


def test_output_directory_rejects_file(tmp_path: Path) -> None:
    target = tmp_path / "not-a-directory"
    target.write_text("content", encoding="utf-8")

    with pytest.raises(ValueError, match="指向了文件"):
        resolve_output_dir(str(target))


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
