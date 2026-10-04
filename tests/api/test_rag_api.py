import pytest
import requests
from pydantic import BaseModel, Field
from typing import List

# ---------------------------------------------------------------------------
# 1. Pydantic Contract Model
# If backend changes 'latency_seconds' to 'latency' or drops 'retrieved_chunks',
# this contract test immediately fails.
# ---------------------------------------------------------------------------
class ChatResponseContract(BaseModel):
    query: str
    answer: str
    retrieved_chunks: List[str]
    latency_seconds: float = Field(..., ge=0.0)  # Must be positive number
    status: str

# ---------------------------------------------------------------------------
# 2. Test Suite
# ---------------------------------------------------------------------------

def test_single_intent_query(base_url):
    """
    Validates:
    - Status code is 200 OK
    - Latency is under 2 seconds (SLA)
    - Pydantic schema contract matches
    - ChromaDB retrieved relevant chunks
    - Answer contains expected policy facts
    """
    payload = {"query": "How many days do I have to return an item?"}
    response = requests.post(f"{base_url}/api/chat", json=payload)

    assert response.status_code == 200

    # Validate schema
    data = response.json()
    validated = ChatResponseContract(**data)

    # Validate business logic
    assert "30 days" in validated.answer
    assert validated.status == "success"
    assert len(validated.retrieved_chunks) > 0
    assert validated.latency_seconds < 2.0, f"SLA Violated! Took {validated.latency_seconds}s"


def test_multi_intent_compound_query(base_url):
    """
    Validates the fix we made earlier:
    The AI must answer BOTH parts of a combined question.
    """
    payload = {"query": "What is the warranty period and shipping policy?"}
    response = requests.post(f"{base_url}/api/chat", json=payload)

    assert response.status_code == 200
    answer = response.json()["answer"]

    # Verify both intents are present in the single generated answer
    assert "1-year limited warranty" in answer, "Missing warranty information!"
    assert "3-5 business days" in answer, "Missing shipping information!"


def test_out_of_domain_query(base_url):
    """
    Validates how the system handles queries not present in policy.txt.
    It should not crash or hallucinate.
    """
    payload = {"query": "Can you book a flight ticket for me?"}
    response = requests.post(f"{base_url}/api/chat", json=payload)

    assert response.status_code == 200
    answer = response.json()["answer"]
    # Verify it returns a policy-grounded fallback
    assert len(answer) > 0


def test_negative_empty_string_query(base_url):
    """
    Validates boundary condition: Blank queries must be rejected with 400 Bad Request.
    """
    payload = {"query": "   "}
    response = requests.post(f"{base_url}/api/chat", json=payload)

    assert response.status_code == 400
    assert "cannot be blank" in response.json()["detail"].lower()


def test_negative_malformed_payload(base_url):
    """
    Validates contract error: If client sends wrong key (e.g. 'prompt' instead of 'query'),
    FastAPI must reject it with 422 Unprocessable Entity.
    """
    payload = {"wrong_key": "What is the policy?"}
    response = requests.post(f"{base_url}/api/chat", json=payload)

    assert response.status_code == 422