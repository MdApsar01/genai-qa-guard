import pytest
import requests
import time
from pydantic import BaseModel, ValidationError

# ---------------------------------------------------------------------------
# CONCEPT 1: Contract Testing with Pydantic
# A "Contract" defines the exact structure you expect the API to return.
# If the backend developer changes "title" to "post_title" or "id" to a string,
# this Pydantic model will fail immediately, catching the bug.
# ---------------------------------------------------------------------------
class PostContract(BaseModel):
    userId: int
    id: int
    title: str
    body: str

BASE_URL = "https://jsonplaceholder.typicode.com"

# ---------------------------------------------------------------------------
# TEST 1: Positive GET Request + Latency / SLA Check
# ---------------------------------------------------------------------------
def test_get_post_success_and_latency():
    # 1. Record start time to measure performance
    start_time = time.time()
    
    # 2. Make the HTTP GET request
    response = requests.get(f"{BASE_URL}/posts/1", timeout=5)
    
    # 3. Calculate latency (how long the API took in seconds)
    latency = time.time() - start_time

    # ASSERTION 1: Status code must be 200 OK
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # ASSERTION 2: SLA (Service Level Agreement) - Must respond within 1.5 seconds
    assert latency < 1.5, f"API too slow! Latency was {latency:.2f}s"

    # ASSERTION 3: Content-Type header must be application/json
    assert "application/json" in response.headers.get("Content-Type", "")

    # ASSERTION 4: Validate against the Pydantic schema contract
    data = response.json()
    validated_data = PostContract(**data)
    assert validated_data.id == 1
    assert len(validated_data.title) > 0


# ---------------------------------------------------------------------------
# TEST 2: Positive POST Request (Sending a JSON Payload)
# ---------------------------------------------------------------------------
def test_create_post_payload():
    # 1. Define payload to send
    new_post = {
        "title": "AI Testing Mastery",
        "body": "Step by step learning path for QA Automation to AI QA.",
        "userId": 42
    }
    headers = {"Content-Type": "application/json; charset=UTF-8"}

    # 2. Send POST request with JSON
    response = requests.post(f"{BASE_URL}/posts", json=new_post, headers=headers, timeout=5)

    # 3. Assert status is 201 Created
    assert response.status_code == 201

    # 4. Assert response echoes back what we sent
    response_body = response.json()
    assert response_body["title"] == new_post["title"]
    assert response_body["userId"] == new_post["userId"]
    assert "id" in response_body  # Server generated ID


# ---------------------------------------------------------------------------
# TEST 3: Negative Testing (Handling Non-Existent Resources)
# ---------------------------------------------------------------------------
def test_get_non_existent_post():
    # Request an ID that does not exist
    response = requests.get(f"{BASE_URL}/posts/999999", timeout=5)

    # Assert the server gracefully returns 404 Not Found instead of crashing with 500
    assert response.status_code == 404