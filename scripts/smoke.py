"""Exercise a production-style app over HTTP, locally or in a running container."""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]


def request(origin, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(urljoin(origin + "/", path), data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as response:
        return response.read(), response.headers


def check(origin):
    health = json.loads(request(origin, "/healthz")[0])
    assert health["status"] == "ok" and health["models"] >= 32, health
    html = request(origin, "/")[0].decode()
    assert "<div id=\"root\">" in html, "The built frontend was not served"
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
    assert assets, "Frontend assets are missing"
    for asset in assets:
        content = request(origin, asset)[0]
        assert content
        if asset.endswith(".js"):
            assert b"http://localhost:8000/v2" not in content, "The production bundle contains a localhost API URL"
    capabilities = json.loads(request(origin, "/v2/capabilities")[0])
    assert len(capabilities["supported"]) == health["models"]
    generated = json.loads(request(origin, "/v2/generate", {"prompt": "Box with lid 120x80x60 mm with 0.4mm clearance."})[0])
    assert generated["success"], generated.get("errors")
    assert generated["metadata"]["estimated_dimensions_mm"] == {"x": 120, "y": 80, "z": 60}
    files = generated["files"]
    links = [files["stl"], files["step"], files["glb"], *(item["url"] for item in files["extra_downloads"])]
    assert len(links) >= 5, "Separate lid exports are missing"
    for link in links:
        assert urlparse(link).netloc == urlparse(origin).netloc, f"Export points to another origin: {link}"
        assert request(origin, link)[0], f"Empty export: {link}"
    for path in ("/v2/does-not-exist", "/files/not_a_model.txt"):
        try:
            request(origin, path)
            raise AssertionError(f"Unexpected success: {path}")
        except urllib.error.HTTPError as error:
            assert error.code in (400, 404), error.code
    print(json.dumps({"origin": origin, "models": health["models"], "frontend_assets": len(assets), "export_downloads": len(links), "status": "passed"}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="Test an already-running container/server")
    parser.add_argument("--frontend-dir", type=Path, default=ROOT / "frontend" / "dist")
    args = parser.parse_args()
    if args.url:
        check(args.url.rstrip("/"))
        return
    reports = ROOT / ".reports"
    reports.mkdir(exist_ok=True)
    # Keep generated smoke-test models isolated from the user's library.
    os.environ["CADRIX_OUTPUT_DIR"] = str(reports / "smoke-models")
    os.environ["CADRIX_FRONTEND_DIR"] = str(args.frontend_dir.resolve())
    sys.path.insert(0, str(ROOT / "backend"))
    import uvicorn
    from main import app

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", host="127.0.0.1", port=port))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 30
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("Smoke-test server did not start")
            time.sleep(0.05)
        check(f"http://127.0.0.1:{port}")
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()


if __name__ == "__main__":
    main()
