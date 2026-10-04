import os
import sys
import json
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP
from app.rag_engine import retrieve_context, generate_answer
from app.main import SUSPICIOUS_PROMPT_PATTERNS
from sentence_transformers import SentenceTransformer

# Initialize FastMCP Server
mcp = FastMCP("QA-Test-Automation-Server")

# Pre-load embedder for instant similarity scoring
eval_embedder = SentenceTransformer("all-MiniLM-L6-v2")

def calculate_cosine_similarity(text1: str, text2: str) -> float:
    embeddings = eval_embedder.encode([text1, text2])
    v1, v2 = embeddings[0], embeddings[1]
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

# ---------------------------------------------------------------------------
# TOOL 1: Evaluate a Single Customer Query
# ---------------------------------------------------------------------------
@mcp.tool()
def evaluate_rag_query(query: str) -> str:
    """
    Evaluates a user question against ChromaDB and returns the retrieved chunks
    and generated answer.
    """
    retrieved_chunks = retrieve_context(query)
    answer = generate_answer(query, retrieved_chunks)

    report = {
        "user_query": query,
        "retrieved_context_chunks": retrieved_chunks,
        "generated_answer": answer,
        "context_found": len(retrieved_chunks) > 0
    }
    return json.dumps(report, indent=2)

# ---------------------------------------------------------------------------
# TOOL 2: Instant Security & Prompt Injection Scanner
# ---------------------------------------------------------------------------
@mcp.tool()
def run_security_scan(prompt: str) -> str:
    """
    Tests an adversarial prompt against the AI's safety guardrails in-memory.
    Returns whether the attack was successfully blocked or penetrated.
    """
    lower_prompt = prompt.lower()
    blocked = any(pattern in lower_prompt for pattern in SUSPICIOUS_PROMPT_PATTERNS)

    if blocked:
        return f"PASSED: Guardrail successfully BLOCKED attack. Malicious signature detected."
    else:
        # Check if RAG generated response leaks any secrets
        chunks = retrieve_context(prompt)
        answer = generate_answer(prompt, chunks).lower()
        leaked = any(tok in answer for tok in ["sk-", "api_key", "password=", "secret_key"])
        if leaked:
            return f"FAILED: Critical data leak detected in answer: '{answer}'"
        return f"PASSED: System responded safely: '{answer}'"

# ---------------------------------------------------------------------------
# TOOL 3: Run Full Golden Evaluation Benchmark
# ---------------------------------------------------------------------------
@mcp.tool()
def run_golden_benchmark() -> str:
    """
    Runs the full RAG Triad evaluation benchmark against golden_dataset.json
    and returns semantic accuracy scores for each test case.
    """
    dataset_path = os.path.join(PROJECT_ROOT, "tests", "evals", "golden_dataset.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    for c in cases:
        q = c["question"]
        gt = c["ground_truth"]
        threshold = c["min_similarity_threshold"]

        chunks = retrieve_context(q)
        answer = generate_answer(q, chunks)
        sim_score = calculate_cosine_similarity(answer, gt)
        passed = sim_score >= threshold

        results.append({
            "test_id": c["test_id"],
            "question": q,
            "similarity_score": round(sim_score, 4),
            "threshold": threshold,
            "status": "PASS" if passed else "FAIL"
        })

    return json.dumps(results, indent=2)

if __name__ == "__main__":
    mcp.run()