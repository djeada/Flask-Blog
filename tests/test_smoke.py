import getpass
import psutil
import subprocess
import time
import requests
import os
import signal
import pytest
import sys
import socket
from contextlib import contextmanager
from typing import Generator, Optional

# Configuration
APP_PATH = os.path.join(os.path.dirname(__file__), '../src/app.py')
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), '../credentials.json')
GEN_SCRIPT = os.path.join(os.path.dirname(__file__), '../scripts/generate_credentials.py')
DEFAULT_PORT = 5000
STARTUP_TIMEOUT = 10
SHUTDOWN_TIMEOUT = 5


class PortManager:
    """Utility class for managing port operations."""
    
    @staticmethod
    def is_port_in_use(port: int) -> bool:
        """Check if a port is currently in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(('127.0.0.1', port))
            return result == 0
    
    @staticmethod
    def kill_processes_on_port(port: int, current_user: str) -> bool:
        """Kill processes owned by current user that are using the specified port."""
        killed = False
        for proc in psutil.process_iter(['pid', 'username']):
            try:
                if proc.info['username'] != current_user:
                    continue
                    
                for conn in proc.net_connections(kind='inet'):
                    if conn.laddr and conn.laddr.port == port:
                        print(f"Killing process {proc.pid} using port {port} (user: {current_user})")
                        proc.kill()
                        killed = True
                        break
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                print(f"Warning: Could not inspect or kill process {getattr(proc, 'pid', '?')}: {e}")
                continue
        return killed
    
    @staticmethod
    def wait_for_port_release(port: int, timeout: int = 10) -> bool:
        """Wait for a port to be released."""
        print(f"Waiting for port {port} to be released...")
        for _ in range(timeout * 2):  # Check every 0.5 seconds
            time.sleep(0.5)
            if not PortManager.is_port_in_use(port):
                print(f"Port {port} is now free.")
                return True
        print(f"Warning: Port {port} may still be in use after {timeout} seconds.")
        return False


class FlaskAppManager:
    """Manager for Flask application lifecycle in tests."""
    
    def __init__(self, app_path: str, port: int = DEFAULT_PORT):
        self.app_path = app_path
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self.current_user = getpass.getuser()
    
    def cleanup_port(self) -> None:
        """Clean up any existing processes on the target port."""
        if PortManager.kill_processes_on_port(self.port, self.current_user):
            PortManager.wait_for_port_release(self.port)
    
    def start(self) -> None:
        """Start the Flask application."""
        print(f"[INFO] Starting Flask app on port {self.port}...")
        
        self.process = subprocess.Popen([
            sys.executable, self.app_path
        ], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        preexec_fn=os.setsid
        )
        
        # Wait for the server to start with timeout
        start_time = time.time()
        while time.time() - start_time < STARTUP_TIMEOUT:
            if self.process.poll() is not None:
                # Process exited early
                stdout, stderr = self.process.communicate(timeout=5)
                print("[ERROR] Flask app exited early.")
                print(f"stdout: {stdout.decode(errors='ignore')}")
                print(f"stderr: {stderr.decode(errors='ignore')}")
                raise RuntimeError("Flask app failed to start")
            
            if PortManager.is_port_in_use(self.port):
                print(f"[INFO] Flask app started successfully on port {self.port}")
                return
            
            time.sleep(0.5)
        
        raise TimeoutError(f"Flask app failed to start within {STARTUP_TIMEOUT} seconds")
    
    def stop(self) -> None:
        """Stop the Flask application and collect logs."""
        if self.process is None:
            return
        
        print(f"[INFO] Stopping Flask app (pid: {self.process.pid})...")
        
        try:
            # Try graceful shutdown first
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            
            # Wait for graceful shutdown
            try:
                stdout, stderr = self.process.communicate(timeout=SHUTDOWN_TIMEOUT)
                print(f"[INFO] Flask app stopped gracefully")
                if stdout:
                    print(f"stdout: {stdout.decode(errors='ignore')}")
                if stderr:
                    print(f"stderr: {stderr.decode(errors='ignore')}")
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown fails
                print("[WARNING] Graceful shutdown timed out, forcing kill...")
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                stdout, stderr = self.process.communicate()
                
        except ProcessLookupError:
            print(f"[INFO] Process {self.process.pid} already stopped.")
        except Exception as e:
            print(f"[ERROR] Error stopping Flask app: {e}")


@contextmanager
def credentials_manager() -> Generator[None, None, None]:
    """Context manager for handling credentials setup and cleanup."""
    try:
        # Setup: generate credentials.json
        print("[INFO] Generating credentials...")
        subprocess.run([sys.executable, GEN_SCRIPT], check=True)
        yield
    finally:
        # Cleanup: remove credentials.json
        print("[INFO] Cleaning up credentials...")
        try:
            subprocess.run([sys.executable, GEN_SCRIPT, '--clean'], check=True)
        except subprocess.CalledProcessError as e:
            print(f"[WARNING] Failed to clean up credentials: {e}")


@pytest.fixture(scope="module")
def flask_app():
    """Pytest fixture that manages Flask app lifecycle for tests."""
    with credentials_manager():
        app_manager = FlaskAppManager(APP_PATH, DEFAULT_PORT)
        
        # Clean up any existing processes on the port
        app_manager.cleanup_port()
        
        # Start the Flask app
        app_manager.start()
        
        try:
            yield app_manager
        finally:
            # Stop the Flask app
            app_manager.stop()


def test_homepage(flask_app):
    """Test that the Flask app homepage responds correctly."""
    print("[INFO] Testing Flask app homepage...")
    
    try:
        response = requests.get(f'http://127.0.0.1:{DEFAULT_PORT}/', timeout=10)
        
        print(f"[INFO] Response status: {response.status_code}")
        print(f"[INFO] Response headers: {dict(response.headers)}")
        print(f"[INFO] Response body (truncated): {response.text[:200]}")
        
        # Assertions
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        content_type = response.headers.get('Content-Type', '')
        assert 'html' in content_type.lower(), f"Expected 'html' in Content-Type, got {content_type}"
        
        response_text = response.text.lower()
        assert 'home' in response_text or 'articles' in response_text, \
            "Expected 'Home' or 'Articles' in response body"
        
        print("[INFO] Homepage test passed successfully!")
        
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Failed to connect to Flask app: {e}")
    except AssertionError as e:
        print(f"[ERROR] Test assertion failed: {e}")
        raise


def test_app_health(flask_app):
    """Additional test to verify app health and basic functionality."""
    print("[INFO] Testing Flask app health...")
    
    try:
        # Test that the app responds within reasonable time
        start_time = time.time()
        response = requests.get(f'http://127.0.0.1:{DEFAULT_PORT}/', timeout=5)
        response_time = time.time() - start_time
        
        assert response_time < 2.0, f"Response time too slow: {response_time:.2f}s"
        assert len(response.text) > 0, "Response body is empty"
        
        print(f"[INFO] App health check passed (response time: {response_time:.2f}s)")
        
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Health check failed: {e}")


if __name__ == "__main__":
    # Allow running the test directly for debugging
    pytest.main([__file__, "-v"])
