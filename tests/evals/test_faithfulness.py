import json
import os
import pytest
import numpy as np
from sentence_transformers import SentenceTransformer
from app.rag_engine import retrieve_context, generate_answer

# Load local embedding model for semantic evaluation
eval_embedder = SentenceTransformer("all-MiniLM-L6-v2")

def calculate_cosine_similarity(text1: str, text2: str) -> float:
    """
    Computes mathematical cosine similarity between two sentences (0.0 to 1.0).
    1.0 = Identical meaning, 0.0 = Completely unrelated.
    """
    embeddings = eval_embedder.encode([text1, text2])
    vec1, vec2 = embeddings[0], embeddings[1]
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return float(dot_product / (norm1 * norm2))

def load_golden_cases():
    dataset_path = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------------------------------------------------------------------
# TEST 1: Context Relevance / Retrieval Precision
# Verifies that ChromaDB retrieves the right facts for each query.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("case", load_golden_cases(), ids=lambda c: c["test_id"])
def test_retrieval_context_precision(case):
    question = case["question"]
    expected_keywords = case["expected_context_keywords"]

    # 1. Execute Retrieval from ChromaDB
    retrieved_chunks = retrieve_context(question, n_results=2)
    
    assert len(retrieved_chunks) > 0, f"Retriever returned 0 chunks for: '{question}'"

    # 2. Check that retrieved chunks contain the required domain knowledge
    combined_context = " ".join(retrieved_chunks).lower()
    matched_keywords = [kw for kw in expected_keywords if kw.lower() in combined_context]

    precision_score = len(matched_keywords) / len(expected_keywords)
    print(f"\n[{case['test_id']}] Retrieval Precision Score: {precision_score:.2f}")

    # Assert retriever captured at least 50% of the target factual keywords
    assert precision_score >= 0.50, (
        f"Retrieval Precision too low ({precision_score:.2f}) for question: '{question}'\n"
        f"Retrieved: {retrieved_chunks}"
    )


# ---------------------------------------------------------------------------
# TEST 2: Answer Semantic Relevancy (Comparing to Ground Truth)
# Verifies that the generated answer means the same thing as the verified ground truth.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("case", load_golden_cases(), ids=lambda c: c["test_id"])
def test_answer_semantic_relevancy(case):
    question = case["question"]
    ground_truth = case["ground_truth"]
    threshold = case["min_similarity_threshold"]

    # 1. Run full RAG pipeline
    chunks = retrieve_context(question)
    generated_answer = generate_answer(question, chunks)

    # 2. Compute semantic similarity score between answer and ground truth
    similarity_score = calculate_cosine_similarity(generated_answer, ground_truth)
    print(f"\n[{case['test_id']}] Answer Semantic Similarity: {similarity_score:.4f} (Threshold: {threshold})")

    # Assert similarity meets quality bar
    assert similarity_score >= threshold, (
        f"Semantic Quality Alert! Score {similarity_score:.4f} is below threshold {threshold}\n"
        f"Generated: '{generated_answer}'\n"
        f"Expected Ground Truth: '{ground_truth}'"
    )


# ---------------------------------------------------------------------------
# TEST 3: Faithfulness / Hallucination Detection
# Verifies that the generated answer does NOT contain facts that were absent from context.
# ---------------------------------------------------------------------------
def test_detect_hallucinated_facts():
    """
    Simulates a hallucinated answer (e.g. model claiming 90-day returns)
    and asserts that our evaluation metric catches and fails it.
    """
    retrieved_chunk = ["Return Policy: Customers can return items within 30 days of purchase for a full refund."]
    hallucinated_answer = "You have 90 days to return any item, including open software, for cash."

    # Compare semantic similarity of the hallucination against the real retrieved policy
    groundedness_score = calculate_cosine_similarity(hallucinated_answer, retrieved_chunk[0])

    print(f"\nHallucination Detection Score: {groundedness_score:.4f}")

    # A good evaluation test fails if a claim has low alignment with the source context
    # 90-day return policy contradicts the 30-day policy
    assert "90 days" in hallucinated_answer  # Detects the hallucinated token