import pytest
from playwright.sync_api import Page, expect

def test_live_chat_ui_flow(page: Page, base_url):
    """
    E2E Test:
    1. Opens the browser at http://127.0.0.1:8000/
    2. Types a question into #chat-input
    3. Clicks #send-button
    4. Asserts that #response-box populates with the correct answer
    """
    page.goto(base_url)

    # 1. Verify page elements exist
    expect(page.locator("h2")).to_contain_text("Customer Support AI Assistant")
    
    # 2. Interact with the chat UI
    page.fill("#chat-input", "What payment methods do you accept?")
    page.click("#send-button")

    # 3. Assert response is displayed in the UI
    response_box = page.locator("#response-box")
    expect(response_box).to_contain_text("Visa, MasterCard, PayPal, and Apple Pay", timeout=5000)


def test_ui_with_mocked_network_response(page: Page, base_url):
    """
    AI Testing Pattern: Network Mocking.
    Intercepts the /api/chat HTTP request and provides an instant mock answer.
    This allows UI testing without hitting the backend ChromaDB or spending tokens.
    """
    mock_payload = {
        "query": "What is the return policy?",
        "answer": "MOCK_VERIFIED: 100 days no-questions-asked refund policy.",
        "retrieved_chunks": ["Mock Chunk 1"],
        "latency_seconds": 0.01,
        "status": "success"
    }

    # Intercept any POST to /api/chat and return our mock payload
    page.route(
        "**/api/chat",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            json=mock_payload
        )
    )

    page.goto(base_url)
    page.fill("#chat-input", "What is the return policy?")
    page.click("#send-button")

    # Verify the UI renders the mocked answer
    response_box = page.locator("#response-box")
    expect(response_box).to_contain_text("MOCK_VERIFIED: 100 days no-questions-asked refund policy.")


def test_ui_handles_backend_500_error(page: Page, base_url):
    """
    Resilience Test:
    Simulates a backend crash (500 Internal Server Error) to verify
    the UI shows a user-friendly error message instead of hanging on 'loading'.
    """
    # Force /api/chat to fail with HTTP 500
    page.route(
        "**/api/chat",
        lambda route: route.fulfill(
            status=500,
            content_type="application/json",
            json={"detail": "ChromaDB memory index corrupted."}
        )
    )

    page.goto(base_url)
    page.fill("#chat-input", "Any question")
    page.click("#send-button")

    # Verify error is surfaced to the user
    response_box = page.locator("#response-box")
    expect(response_box).to_contain_text("ChromaDB memory index corrupted.", timeout=5000)
    
    # Verify the loading indicator is hidden
    expect(page.locator("#loading")).not_to_be_visible()