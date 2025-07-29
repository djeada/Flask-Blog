"""
End-to-end smoke tests for FastAPI Blog Application
Uses the existing test framework pattern with proper database setup
"""
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
from typing import Optional

# Configuration
APP_PATH = os.path.join(os.path.dirname(__file__), '../src/main.py')
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '../scripts')
DEFAULT_PORT = 8000
STARTUP_TIMEOUT = 15
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
                    
                # Use net_connections() for current psutil versions
                try:
                    connections = proc.net_connections(kind='inet')
                except AttributeError:
                    # Fall back to connections() for older versions
                    connections = proc.connections(kind='inet')
                
                for conn in connections:
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


def setup_database():
    """Set up database using existing scripts."""
    print("[INFO] Setting up database using setup scripts...")
    
    repo_root = os.path.dirname(SCRIPTS_DIR)
    
    # Set up environment for all operations
    env = os.environ.copy()
    env.update({
        'MYSQL_USER': 'root',
        'MYSQL_PASSWORD': 'secret_pass',
        'DB_HOST': 'localhost',
        'DB_PORT': '3306',
        'DB_USER': 'root',
        'DB_PASSWORD': 'secret_pass',
        'DB_NAME': 'blog_db'
    })
    
    # Check if MySQL is already available
    print("[INFO] Checking if MySQL is already available...")
    mysql_available = False
    try:
        result = subprocess.run([
            'mysqladmin', 'ping', '-h', 'localhost', '-P', '3306', 
            '--protocol=TCP', '-u', 'root', '-psecret_pass', '--silent'
        ], capture_output=True, timeout=5, env=env)
        
        if result.returncode == 0:
            mysql_available = True
            print("[INFO] MySQL is already available, skipping Docker setup")
        
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("[INFO] MySQL not available or mysql client not found")
    
    # If MySQL is not available, try to start it with docker-compose
    if not mysql_available:
        print("[INFO] Starting MySQL with docker-compose...")
        docker_result = subprocess.run([
            'docker-compose', 'up', '-d', 'mysql'
        ], cwd=repo_root, capture_output=True, timeout=60)
        
        if docker_result.returncode != 0:
            pytest.skip(f"Could not start MySQL: {docker_result.stderr.decode()}")
        
        # Use the wait script to wait for MySQL
        print("[INFO] Waiting for MySQL to be ready...")
        wait_script = os.path.join(SCRIPTS_DIR, 'wait_for_mysql.sh')
        
        try:
            wait_result = subprocess.run([
                'bash', wait_script
            ], cwd=repo_root, env=env, capture_output=True, timeout=60)
            
            if wait_result.returncode != 0:
                pytest.skip(f"MySQL failed to start: {wait_result.stderr.decode()}")
                
        except subprocess.TimeoutExpired:
            pytest.skip("MySQL startup timed out")
    
    # Install dependencies only if needed
    print("[INFO] Installing dependencies if needed...")
    install_script = os.path.join(SCRIPTS_DIR, 'install_dependencies.sh')
    
    try:
        result = subprocess.run([
            'bash', install_script
        ], cwd=repo_root, env=env, capture_output=True, timeout=120)
        
        if result.returncode != 0:
            print(f"[WARNING] Dependencies installation warning: {result.stderr.decode()}")
            # Continue anyway as dependencies might already be installed
    
    except subprocess.TimeoutExpired:
        print("[WARNING] Dependencies installation timed out, continuing...")
    
    # Prepare database schema using the script
    print("[INFO] Preparing database schema...")
    schema_script = os.path.join(SCRIPTS_DIR, 'prepare_db_schema.sh')
    
    try:
        result = subprocess.run([
            'bash', schema_script
        ], cwd=repo_root, env=env, capture_output=True, timeout=30)
        
        if result.returncode != 0:
            print(f"[ERROR] Schema script stdout: {result.stdout.decode()}")
            print(f"[ERROR] Schema script stderr: {result.stderr.decode()}")
            pytest.skip(f"Database schema preparation failed: {result.stderr.decode()}")
        
        print("[INFO] Database setup completed successfully!")
        
    except subprocess.TimeoutExpired:
        pytest.skip("Database schema preparation timed out")


class FastAPIAppManager:
    """Manager for FastAPI application lifecycle in tests."""
    
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
        """Start the FastAPI application."""
        print(f"[INFO] Starting FastAPI app on port {self.port}...")
        
        # Change to src directory and start uvicorn
        src_dir = os.path.dirname(self.app_path)
        
        # Set environment variables for database connection
        env = os.environ.copy()
        env.update({
            'DB_HOST': 'localhost',
            'DB_PORT': '3306',
            'DB_USER': 'root',
            'DB_PASSWORD': 'secret_pass',
            'DB_NAME': 'blog_db',
            'SECRET_KEY': 'test-secret-key',
            'DEBUG': 'True'
        })
        
        self.process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "main:app", 
            "--host", "127.0.0.1", "--port", str(self.port)
        ], 
        cwd=src_dir,
        env=env,
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        start_new_session=True
        )
        
        # Wait for the server to start
        start_time = time.time()
        while time.time() - start_time < STARTUP_TIMEOUT:
            if self.process.poll() is not None:
                # Process exited early
                stdout, stderr = self.process.communicate(timeout=5)
                print("[ERROR] FastAPI app exited early.")
                print(f"stdout: {stdout.decode(errors='ignore')}")
                print(f"stderr: {stderr.decode(errors='ignore')}")
                raise RuntimeError("FastAPI app failed to start")
            
            # Check if server is responding
            try:
                response = requests.get(f'http://127.0.0.1:{self.port}/health', timeout=2)
                if response.status_code == 200:
                    print(f"[INFO] FastAPI app started successfully on port {self.port}")
                    return
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(0.5)
        
        raise TimeoutError(f"FastAPI app failed to start within {STARTUP_TIMEOUT} seconds")
    
    def stop(self) -> None:
        """Stop the FastAPI application."""
        if self.process is None:
            return
        
        print(f"[INFO] Stopping FastAPI app (pid: {self.process.pid})...")
        
        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            try:
                stdout, stderr = self.process.communicate(timeout=SHUTDOWN_TIMEOUT)
                print(f"[INFO] FastAPI app stopped gracefully")
                if stdout:
                    print(f"[DEBUG] App stdout: {stdout.decode(errors='ignore')}")
                if stderr:
                    print(f"[DEBUG] App stderr: {stderr.decode(errors='ignore')}")
            except subprocess.TimeoutExpired:
                print("[WARNING] Graceful shutdown timed out, forcing kill...")
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                stdout, stderr = self.process.communicate()
                if stdout:
                    print(f"[DEBUG] App stdout: {stdout.decode(errors='ignore')}")
                if stderr:
                    print(f"[DEBUG] App stderr: {stderr.decode(errors='ignore')}")
                
        except ProcessLookupError:
            print(f"[INFO] Process {self.process.pid} already stopped.")
        except Exception as e:
            print(f"[ERROR] Error stopping FastAPI app: {e}")


@pytest.fixture(scope="module")
def fastapi_app():
    """Pytest fixture that manages FastAPI app lifecycle for tests."""
    # Set up database first
    setup_database()
    
    app_manager = FastAPIAppManager(APP_PATH, DEFAULT_PORT)
    
    # Clean up any existing processes on the port
    app_manager.cleanup_port()
    
    # Start the FastAPI app
    app_manager.start()
    
    try:
        yield app_manager
    finally:
        # Stop the FastAPI app
        app_manager.stop()


def test_health_endpoint(fastapi_app):
    """Test that the FastAPI app health endpoint responds correctly."""
    print("[INFO] Testing FastAPI app health endpoint...")
    
    response = requests.get(f'http://127.0.0.1:{DEFAULT_PORT}/health', timeout=10)
    
    print(f"[INFO] Health response status: {response.status_code}")
    print(f"[INFO] Health response: {response.json()}")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    
    print("[INFO] Health endpoint test passed!")


def test_homepage(fastapi_app):
    """Test that the FastAPI app homepage responds correctly."""
    print("[INFO] Testing FastAPI app homepage...")
    
    response = requests.get(f'http://127.0.0.1:{DEFAULT_PORT}/', timeout=10)
    
    print(f"[INFO] Response status: {response.status_code}")
    print(f"[INFO] Response body (truncated): {response.text[:200]}")
    
    assert response.status_code == 200
    content_type = response.headers.get('Content-Type', '')
    assert 'html' in content_type.lower()
    
    print("[INFO] Homepage test passed!")


def test_api_docs(fastapi_app):
    """Test that FastAPI automatic API documentation is accessible."""
    print("[INFO] Testing FastAPI API documentation...")
    
    response = requests.get(f'http://127.0.0.1:{DEFAULT_PORT}/docs', timeout=10)
    
    print(f"[INFO] API docs response status: {response.status_code}")
    
    assert response.status_code == 200
    content_type = response.headers.get('Content-Type', '')
    assert 'html' in content_type.lower()
    
    # Check for Swagger UI elements
    response_text = response.text.lower()
    assert 'swagger' in response_text or 'openapi' in response_text
    
    print("[INFO] API docs test passed!")


def test_database_interaction(fastapi_app):
    """Test that the application can interact with the database."""
    print("[INFO] Testing database interaction through API...")
    
    # Test that we can get articles page (HTML response)
    response = requests.get(f'http://127.0.0.1:{DEFAULT_PORT}/api/articles/', timeout=10)
    
    print(f"[INFO] Articles API response status: {response.status_code}")
    
    assert response.status_code == 200
    
    # Check that it's HTML content
    content_type = response.headers.get('Content-Type', '')
    assert 'html' in content_type.lower()
    
    # Check that the page contains expected content
    response_text = response.text.lower()
    assert 'articles' in response_text or 'blog' in response_text
    
    print(f"[INFO] Successfully accessed articles page with HTML content")
    print("[INFO] Database interaction test passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
