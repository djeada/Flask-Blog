import subprocess
import time
import requests
import os
import signal
import pytest

APP_PATH = os.path.join(os.path.dirname(__file__), '../src/app.py')

@pytest.fixture(scope="module")
def flask_app():
    # Start the Flask app in a subprocess
    proc = subprocess.Popen([
        'python', APP_PATH
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
    time.sleep(2)  # Wait for server to start
    yield
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)


def test_homepage(flask_app):
    resp = requests.get('http://127.0.0.1:5000/')
    assert resp.status_code == 200
    assert 'html' in resp.headers['Content-Type']
    assert 'Home' in resp.text or 'Articles' in resp.text
