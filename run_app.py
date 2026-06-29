import json
import os
# Force disable proxies for local connections to prevent health check timeouts
os.environ['no_proxy'] = 'localhost,127.0.0.1'
import re
import subprocess
import sys
import time
import urllib.request


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_URL = "http://127.0.0.1:8000/api/health"
CONFIG_PATH = os.path.join(ROOT_DIR, "frontend", "config.json")
CLOUDFLARED_PATH = os.path.join(ROOT_DIR, "cloudflared.exe")
CHECK_INTERVAL = 10
FAILURE_LIMIT = 3


def url_is_healthy(url, timeout=8):
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "stock-monitor/1.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except Exception:
        return False


def read_config_api_url():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as file:
            return json.load(file).get("api_url", "")
    except Exception:
        return ""


def write_config(tunnel_url):
    with open(CONFIG_PATH, "w", encoding="utf-8") as file:
        json.dump({"api_url": f"{tunnel_url}/api"}, file, ensure_ascii=False, indent=2)
        file.write("\n")


def start_backend():
    print("[watchdog] Starting backend at http://127.0.0.1:8000")
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["no_proxy"] = "localhost,127.0.0.1"
    return subprocess.Popen(
        [sys.executable, "-u", os.path.join(ROOT_DIR, "backend", "main.py")],
        cwd=ROOT_DIR,
        stdout=open(os.path.join(ROOT_DIR, "backend_run.out.log"), "a", encoding="utf-8"),
        stderr=open(os.path.join(ROOT_DIR, "backend_run.err.log"), "a", encoding="utf-8"),
        env=env,
    )


def wait_for_backend(timeout=45):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if url_is_healthy(BACKEND_URL, timeout=3):
            return True
        time.sleep(1)
    return False


def start_tunnel():
    print("[watchdog] Starting Cloudflare quick tunnel")
    env = os.environ.copy()
    env["no_proxy"] = "localhost,127.0.0.1"
    process = subprocess.Popen(
        [CLOUDFLARED_PATH, "tunnel", "--url", "http://127.0.0.1:8000", "--protocol", "http2"],
        cwd=ROOT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
        bufsize=1,
        env=env,
    )

    deadline = time.time() + 45
    while time.time() < deadline and process.poll() is None:
        line = process.stderr.readline()
        if not line:
            time.sleep(0.1)
            continue
        match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
        if match:
            return process, match.group(0)

    process.terminate()
    return None, ""


def deploy_frontend():
    print("[watchdog] Deploying updated tunnel URL to Firebase")
    result = subprocess.run(
        ["firebase.cmd", "deploy", "--only", "hosting"],
        cwd=ROOT_DIR,
        check=False,
    )
    return result.returncode == 0


def ensure_tunnel(current_process=None):
    configured_api = read_config_api_url()
    if configured_api and url_is_healthy(f"{configured_api}/health", timeout=10):
        print(f"[watchdog] Existing public API is healthy: {configured_api}")
        return current_process, configured_api.removesuffix("/api")

    process, tunnel_url = start_tunnel()
    if not tunnel_url:
        print("[watchdog] Failed to create a public tunnel; waiting 3 minutes to cool down rate limits...", flush=True)
        time.sleep(180)
        return None, ""

    write_config(tunnel_url)
    if deploy_frontend():
        print(f"[watchdog] Public API restored: {tunnel_url}/api")
    else:
        print("[watchdog] Tunnel is online, but Firebase deployment failed")
    return process, tunnel_url


def stop_process(process):
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def run():
    backend_process = None
    tunnel_process = None
    tunnel_url = ""

    if url_is_healthy(BACKEND_URL):
        print("[watchdog] Existing backend is healthy")
    else:
        backend_process = start_backend()
        if not wait_for_backend():
            raise RuntimeError("Backend did not become healthy within 45 seconds")

    tunnel_process, tunnel_url = ensure_tunnel()
    backend_failures = 0
    tunnel_failures = 0

    print("[watchdog] Monitoring backend and tunnel. Press Ctrl+C to stop.")
    try:
        while True:
            if url_is_healthy(BACKEND_URL):
                backend_failures = 0
            else:
                backend_failures += 1

            public_api = f"{tunnel_url}/api/health" if tunnel_url else ""
            if public_api and url_is_healthy(public_api):
                tunnel_failures = 0
            else:
                tunnel_failures += 1

            if backend_failures >= FAILURE_LIMIT:
                print("[watchdog] Backend is offline; restarting")
                stop_process(backend_process)
                backend_process = start_backend()
                wait_for_backend()
                backend_failures = 0

            if tunnel_failures >= FAILURE_LIMIT:
                print("[watchdog] Public tunnel is offline; replacing it")
                stop_process(tunnel_process)
                tunnel_process, tunnel_url = ensure_tunnel()
                tunnel_failures = 0

            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n[watchdog] Shutting down managed processes")
    finally:
        stop_process(backend_process)
        stop_process(tunnel_process)


if __name__ == "__main__":
    run()
