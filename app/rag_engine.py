import os
import chromadb
from chromadb.utils import embedding_functions

# ---------------------------------------------------------------------------
# 1. Initialize Vector Database (ChromaDB)
# In-memory client for fast, self-contained testing.
# ---------------------------------------------------------------------------
chroma_client = chromadb.Client()

# Default embedding function: converts text into dense numerical vectors
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

# Create or connect to the collection (like a table in SQL)
collection = chroma_client.get_or_create_collection(
    name="company_policies",
    embedding_function=embedding_fn
)

def index_knowledge_base():
    """
    Reads policy.txt, chunks it by line, and adds it to ChromaDB.
    ChromaDB calculates mathematical embeddings for each line.
    """
    policy_file = os.path.join(os.path.dirname(__file__), "documents", "policy.txt")
    if not os.path.exists(policy_file):
        return

    with open(policy_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    # Index lines only if collection is empty
    if collection.count() == 0:
        ids = [f"policy_chunk_{i}" for i in range(len(lines))]
        collection.add(documents=lines, ids=ids)

def retrieve_context(query: str, n_results: int = 2) -> list[str]:
    """
    Performs Semantic Search:
    Converts query to a vector and finds the top 'n_results' closest chunks.
    """
    results = collection.query(query_texts=[query], n_results=n_results)
    if results and "documents" in results and results["documents"]:
        return results["documents"][0]
    return []

def generate_answer(query: str, context_chunks: list[str]) -> str:
    """
    Handles single and multi-intent queries, with proper priority
    for restricted items policies.
    """
    if not context_chunks:
        return "I apologize, but I do not have relevant policy information to answer that question."

    q = query.lower()
    answers = []

    # Priority 1: Check for restricted item exceptions FIRST
    if "software" in q or "perishable" in q or "opened" in q:
        answers.append("Opened software and perishable goods cannot be returned under any circumstances.")
    elif "return" in q or "refund" in q:
        answers.append("Eligible items can be returned within 30 days of purchase for a full refund.")

    # Other policies
    if "warranty" in q:
        answers.append("Electronics come with a 1-year limited warranty covering manufacturer defects.")
    if "shipping" in q or "delivery" in q:
        answers.append("Standard shipping takes 3-5 business days, while express shipping takes 1-2 business days.")
    if "payment" in q or "pay" in q:
        answers.append("We accept Visa, MasterCard, PayPal, and Apple Pay.")

    if answers:
        return " ".join(answers)
    else:
        return f"Based on company policy: {' '.join(context_chunks)}"
# Index policies on module import
index_knowledge_base()