import pytest
import subprocess
import time
import requests
import sys

@pytest.fixture(scope="session", autouse=True)
def run_app_server():
    """
    Starts FastAPI backend once before tests run,
    using DEVNULL so Windows pipe buffers never deadlock.
    """
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Health check: Wait up to 10 seconds for the server to respond
    server_ready = False
    for _ in range(20):
        try:
            res = requests.get("http://127.0.0.1:8000/")
            if res.status_code == 200:
                server_ready = True
                break
        except requests.ConnectionError:
            time.sleep(0.5)

    yield server_process

    # Clean shutdown
    server_process.terminate()
    server_process.wait()

@pytest.fixture(scope="session")
def base_url():
    return "http://127.0.0.1:8000"