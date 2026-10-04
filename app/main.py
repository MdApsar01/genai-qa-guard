import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from app.rag_engine import retrieve_context, generate_answer

app = FastAPI(title="Support RAG Assistant", version="1.0.0")

# Request Contract
class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User's query")

# Response Contract
class ChatResponse(BaseModel):
    query: str
    answer: str
    retrieved_chunks: list[str]
    latency_seconds: float
    status: str

@app.get("/", response_class=HTMLResponse)
def get_chat_ui():
    """Minimal Chat interface used for our Playwright automation tests."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>AI Support Portal</title>
        <style>
            body { font-family: sans-serif; margin: 40px; }
            #response-box { margin-top: 15px; padding: 12px; border: 1px solid #ccc; min-height: 40px; background: #fafafa; }
            #loading { color: #0066cc; display: none; font-weight: bold; }
        </style>
    </head>
    <body>
        <h2>Customer Support AI Assistant</h2>
        <input id="chat-input" style="width: 320px; padding: 8px;" placeholder="Ask a question about our policies..." />
        <button id="send-button" style="padding: 8px 16px;" onclick="sendQuery()">Ask</button>
        <p id="loading">AI Assistant is searching knowledge base...</p>
        <div id="response-box">Awaiting your question...</div>

        <script>
        async function sendQuery() {
            const input = document.getElementById("chat-input").value;
            if (!input.trim()) return;

            document.getElementById("loading").style.display = "block";
            document.getElementById("response-box").innerText = "";

            try {
                const res = await fetch("/api/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ query: input })
                });

                const data = await res.json();
                document.getElementById("loading").style.display = "none";
                document.getElementById("response-box").innerText = data.answer || data.detail;
            } catch (err) {
                document.getElementById("loading").style.display = "none";
                document.getElementById("response-box").innerText = "Network Error: Failed to reach AI service.";
            }
        }
        </script>
    </body>
    </html>
    """

# List of known jailbreak trigger phrases
SUSPICIOUS_PROMPT_PATTERNS = [
    "ignore all previous",
    "unrestricted assistant",
    "developer_mode",
    "print your system prompt",
    "secret_key",
    "openai_api_key",
    "database_url"
]

@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    start_time = time.time()

    # Input validation
    clean_query = request.query.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Query cannot be blank.")

    # -----------------------------------------------------------------------
    # AI SAFETY GUARDRAIL: Detect & Deflect Malicious Injections
    # -----------------------------------------------------------------------
    lower_query = clean_query.lower()
    for pattern in SUSPICIOUS_PROMPT_PATTERNS:
        if pattern in lower_query:
            # Safely deflect without crashing or revealing secrets
            return ChatResponse(
                query=request.query,
                answer="I cannot fulfill this request. I am a customer support assistant operating strictly under verified store policies.",
                retrieved_chunks=[],
                latency_seconds=round(time.time() - start_time, 4),
                status="blocked_by_guardrail"
            )

    # 1. Retrieval Layer (ChromaDB)
    chunks = retrieve_context(clean_query)

    # 2. Generation Layer
    answer = generate_answer(clean_query, chunks)

    latency = round(time.time() - start_time, 4)

    return ChatResponse(
        query=request.query,
        answer=answer,
        retrieved_chunks=chunks,
        latency_seconds=latency,
        status="success"
    )
