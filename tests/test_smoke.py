
import getpass
import psutil
import subprocess
import time
import requests
import os
import signal
import pytest
import sys

APP_PATH = os.path.join(os.path.dirname(__file__), '../src/app.py')
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), '../credentials.json')
GEN_SCRIPT = os.path.join(os.path.dirname(__file__), '../scripts/generate_credentials.py')

@pytest.fixture(scope="module")
def flask_app():
    # Setup: generate credentials.json using the unified script
    subprocess.run([sys.executable, GEN_SCRIPT], check=True)

    # Clean up port 5000 if used by a process owned by the same user
    current_user = getpass.getuser()
    port = 5000
    killed = False
    for proc in psutil.process_iter(['pid', 'username']):
        try:
            if proc.info['username'] == current_user:
                for conn in proc.net_connections(kind='inet'):
                    if conn.laddr and conn.laddr.port == port:
                        print(f"Killing process {proc.pid} using port {port} (user: {current_user})")
                        proc.kill()
                        killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            print(f"Warning: Could not inspect or kill process {getattr(proc, 'pid', '?')}: {e}")
            continue
    if killed:
        print(f"Waiting for port {port} to be released...")
        for _ in range(10):
            time.sleep(0.5)
            # Check if port is still in use
            port_in_use = False
            for proc in psutil.process_iter(['pid', 'username']):
                try:
                    if proc.info['username'] == current_user:
                        for conn in proc.net_connections(kind='inet'):
                            if conn.laddr and conn.laddr.port == port:
                                port_in_use = True
                except Exception:
                    continue
            if not port_in_use:
                print(f"Port {port} is now free.")
                break
        else:
            print(f"Warning: Port {port} may still be in use.")

    # Start the Flask app in a subprocess
    print(f"[INFO] Starting Flask app on port {port}...")
    proc = subprocess.Popen([
        sys.executable, APP_PATH
    ], preexec_fn=os.setsid)
    time.sleep(2)  # Wait for server to start

    # Print initial logs in case the app exited early
    if proc.poll() is not None:
        print("[ERROR] Flask app exited early.")

    yield

    # Cleanup: stop Flask app and remove credentials.json using the script
    print(f"[INFO] Stopping Flask app (pid: {proc.pid})...")
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except ProcessLookupError:
        print(f"Process {proc.pid} already stopped.")
    # No need to collect logs, they are shown live in the terminal
    subprocess.run([sys.executable, GEN_SCRIPT, '--clean'], check=True)

def test_homepage(flask_app):
    print("[INFO] Verifying Flask app homepage response...")
    resp = requests.get('http://127.0.0.1:5000/')
    print(f"[INFO] Response status: {resp.status_code}")
    print(f"[INFO] Response headers: {resp.headers}")
    print(f"[INFO] Response body (truncated): {resp.text[:200]}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert 'html' in resp.headers['Content-Type'], f"Expected 'html' in Content-Type, got {resp.headers['Content-Type']}"
    assert 'Home' in resp.text or 'Articles' in resp.text, "Expected 'Home' or 'Articles' in response body"
    killed = cleanup_port(port, current_user)
    if killed:
        print(f"Waiting for port {port} to be released...")
        for _ in range(10):
            time.sleep(0.5)
            if not is_port_in_use(port, current_user):
                print(f"Port {port} is now free.")
                break
        else:
            print(f"Warning: Port {port} may still be in use.")
    import socket
    current_user = getpass.getuser()
    port = DEFAULT_PORT
    killed = False
    for proc in psutil.process_iter(['pid', 'username']):
        try:
            if proc.info['username'] == current_user:
                for conn in proc.connections(kind='inet'):
                    if conn.laddr.port == port:
                        print(f"Killing process {proc.pid} using port {port} (user: {current_user})")
                        proc.kill()
                        killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if killed:
        time.sleep(1)  # Give time for port to be released

    # Start the Flask app in a subprocess
    print(f"Starting Flask app on port {port}...")
    proc = subprocess.Popen([
        sys.executable, APP_PATH
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
    time.sleep(2)  # Wait for server to start

    # Print initial logs in case the app exited early
    if proc.poll() is not None:
        stdout, stderr = proc.communicate(timeout=5)
        print("\n--- Flask app stdout (early exit) ---\n", stdout.decode(errors='ignore'))
        print("\n--- Flask app stderr (early exit) ---\n", stderr.decode(errors='ignore'))

    yield

    # Cleanup: stop Flask app and remove credentials.json using the script
    print(f"Stopping Flask app (pid: {proc.pid})...")
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except ProcessLookupError:
        print(f"Process {proc.pid} already stopped.")
    try:
        stdout, stderr = proc.communicate(timeout=5)
        print("\n--- Flask app stdout ---\n", stdout.decode(errors='ignore'))
        print("\n--- Flask app stderr ---\n", stderr.decode(errors='ignore'))
    except Exception as e:
        print(f"Error collecting Flask app logs: {e}")
    subprocess.run([sys.executable, GEN_SCRIPT, '--clean'], check=True)

def test_homepage(flask_app):
    resp = requests.get('http://127.0.0.1:5000/')
    assert resp.status_code == 200
    assert 'html' in resp.headers['Content-Type']
    assert 'Home' in resp.text or 'Articles' in resp.text
