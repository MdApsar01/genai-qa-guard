import pytest
import subprocess
import time
import requests
import sys

@pytest.fixture(scope="session", autouse=True)
def run_app_server():
    """
    Session fixture: Starts FastAPI backend once before any test runs,
    and terminates it after all tests finish.
    """
    # Start the server process using the current Python executable
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Health check: Wait up to 10 seconds for the server to be responsive
    server_ready = False
    for _ in range(20):
        try:
            res = requests.get("http://127.0.0.1:8000/")
            if res.status_code == 200:
                server_ready = True
                break
        except requests.ConnectionError:
            time.sleep(0.5)

    if not server_ready:
        server_process.terminate()
        raise RuntimeError("Failed to start FastAPI server for testing.")

    yield server_process

    # Teardown: Safely kill the server after tests complete
    server_process.terminate()
    server_process.wait()

@pytest.fixture(scope="session")
def base_url():
    """Provides the base URL to all test functions."""
    return "http://127.0.0.1:8000"