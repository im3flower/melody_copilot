"""Start backend and frontend dev servers with one command.

Usage:
    python main_control.py

Use --help for more options.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parent
BIN_ROOT = PROJECT_ROOT / "bin"
UI_DIR = BIN_ROOT / "UI"
BRIDGE_SCRIPT = BIN_ROOT / "midi_track_ctrl" / "bridge.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Control script to run backend then frontend")
    parser.add_argument("--backend-host", default="0.0.0.0", help="Host binding for uvicorn")
    parser.add_argument("--backend-port", type=int, default=8000, help="Port for uvicorn")
    parser.add_argument(
        "--backend-wait-url",
        default=None,
        help="URL used to detect when the backend is ready. Defaults to http://127.0.0.1:<port>/default",
    )
    parser.add_argument(
        "--backend-timeout",
        type=int,
        default=45,
        help="Seconds to wait for backend readiness before continuing",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Run uvicorn with --reload (development hot reload)",
    )
    parser.add_argument(
        "--frontend-host",
        default="127.0.0.1",
        help="Host passed through to Vite (npm run dev)",
    )
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=5173,
        help="Port passed through to Vite",
    )
    parser.add_argument(
        "--frontend-script",
        default="dev",
        help="Which npm script to run (defaults to 'dev')",
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Only start the backend",
    )
    parser.add_argument(
        "--skip-bridge",
        action="store_true",
        help="Skip starting the Max for Live bridge",
    )
    return parser.parse_args()


def wait_for_backend(url: str, timeout: int) -> bool:
    print(f"Waiting for backend: {url} (timeout {timeout}s)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(url) as response:  # noqa: S310 - trusted URL
                if 200 <= response.status < 500:
                    print("Backend is responding.")
                    return True
        except (URLError, HTTPError):
            time.sleep(1)
    print("Backend did not respond within timeout; continuing anyway.")
    return False


def start_backend(args: argparse.Namespace) -> subprocess.Popen[bytes]:
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        args.backend_host,
        "--port",
        str(args.backend_port),
    ]
    if args.reload:
        cmd.append("--reload")
    print("Launching backend:", " ".join(cmd))
    return subprocess.Popen(cmd, cwd=BIN_ROOT)


def start_bridge() -> subprocess.Popen[bytes]:
    if not BRIDGE_SCRIPT.exists():
        raise FileNotFoundError(f"Bridge script not found: {BRIDGE_SCRIPT}")
    cmd = [sys.executable, str(BRIDGE_SCRIPT)]
    print("Launching Max for Live bridge:", " ".join(cmd))
    return subprocess.Popen(cmd, cwd=PROJECT_ROOT)


def start_frontend(args: argparse.Namespace) -> subprocess.Popen[bytes]:
    default_npm = "npm.cmd" if os.name == "nt" else "npm"
    npm_cmd = os.environ.get("NPM", default_npm)
    npm_path = shutil.which(npm_cmd)
    if not npm_path:
        raise FileNotFoundError(
            f"Cannot find '{npm_cmd}'. Ensure Node.js/npm is installed and on PATH, or set NPM=/full/path/to/npm"
        )

    cmd = [npm_path, "run", args.frontend_script]
    vite_args = []
    if args.frontend_host:
        vite_args.extend(["--host", args.frontend_host])
    if args.frontend_port:
        vite_args.extend(["--port", str(args.frontend_port)])
    if vite_args:
        cmd.extend(["--", *vite_args])
    print("Launching frontend:", " ".join(cmd))
    return subprocess.Popen(cmd, cwd=UI_DIR)


def terminate_process(proc: subprocess.Popen[bytes] | None, name: str) -> None:
    if proc is None or proc.poll() is not None:
        return
    print(f"Stopping {name}...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        print(f"{name} did not exit in time; killing.")
        proc.kill()


def main() -> None:
    args = parse_args()

    wait_url = args.backend_wait_url
    if not wait_url:
        wait_host = "127.0.0.1" if args.backend_host in {"0.0.0.0", "::", "[::]"} else args.backend_host
        wait_url = f"http://{wait_host}:{args.backend_port}/default"

    backend_proc = start_backend(args)

    bridge_proc: subprocess.Popen[bytes] | None = None
    frontend_proc: subprocess.Popen[bytes] | None = None

    try:
        wait_for_backend(wait_url, args.backend_timeout)
        
        if not args.skip_bridge:
            try:
                bridge_proc = start_bridge()
            except FileNotFoundError as e:
                print(f"Warning: {e}")
                print("Continuing without bridge...")
        
        if not args.skip_frontend:
            frontend_proc = start_frontend(args)
        
        services = ["backend"]
        if bridge_proc:
            services.append("bridge")
        if frontend_proc:
            services.append("frontend")
        print(f"Services running: {', '.join(services)}. Press Ctrl+C to stop all.")

        while True:
            backend_return = backend_proc.poll()
            bridge_return = bridge_proc.poll() if bridge_proc else None
            frontend_return = frontend_proc.poll() if frontend_proc else None
            
            if backend_return is not None:
                print(f"Backend exited with code {backend_return}.")
                break
            if bridge_proc and bridge_return is not None:
                print(f"Bridge exited with code {bridge_return}.")
                break
            if frontend_proc and frontend_return is not None:
                print(f"Frontend exited with code {frontend_return}.")
                break
            time.sleep(1)
    except KeyboardInterrupt: 
        print("\nStopping services...")
    finally:
        terminate_process(frontend_proc, "frontend")
        terminate_process(bridge_proc, "bridge")
        terminate_process(backend_proc, "backend")


if __name__ == "__main__":
    main()


