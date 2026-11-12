"""Start a hardened test container, exercise its public HTTP API, then remove it."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smoke import check


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="cadrixai:ci")
    args = parser.parse_args()
    container = subprocess.check_output(["docker", "run", "--detach", "--read-only", "--tmpfs", "/tmp:rw,nosuid,size=256m", "--tmpfs", "/app/data:rw,uid=10001,gid=10001,size=128m", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--publish", "127.0.0.1::8000", args.image], text=True).strip()
    try:
        deadline = time.monotonic() + 90
        while True:
            state = json.loads(subprocess.check_output(["docker", "inspect", container], text=True))[0]
            if not state["State"]["Running"]:
                raise RuntimeError("Container exited during startup")
            if state["State"].get("Health", {}).get("Status") == "healthy":
                break
            if time.monotonic() > deadline:
                raise RuntimeError("Container did not become healthy")
            time.sleep(0.5)
        assert state["Config"]["User"] == "10001:10001", "Container must run without root"
        port = state["NetworkSettings"]["Ports"]["8000/tcp"][0]["HostPort"]
        check(f"http://127.0.0.1:{port}")
    finally:
        subprocess.run(["docker", "logs", container], check=False)
        subprocess.run(["docker", "rm", "--force", container], check=True)


if __name__ == "__main__":
    main()
