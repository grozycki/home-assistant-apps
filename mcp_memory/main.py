import os
from mcp.server.fastmcp import FastMCP
import chromadb
from sentence_transformers import SentenceTransformer

# Retrieve default category injected by run.sh via bashio
DEFAULT_CATEGORY = os.getenv("DEFAULT_CATEGORY", "general")

mcp = FastMCP("Local HA Memory")

DATA_PATH = "/data/chroma_db"
os.makedirs(DATA_PATH, exist_ok=True)

chroma_client = chromadb.PersistentClient(path=DATA_PATH)
collection = chroma_client.get_or_create_collection(name="assist_memory")

embedder = SentenceTransformer("all-MiniLM-L6-v2")


@mcp.tool()
def remember_fact(fact: str, category: str = DEFAULT_CATEGORY) -> str:
    """Store important facts, preferences, or details into the local vector database."""
    embedding = embedder.encode(fact).tolist()
    doc_id = f"mem_{collection.count() + 1}"

    collection.add(
        documents=[fact],
        embeddings=[embedding],
        metadatas=[{"category": category}],
        ids=[doc_id]
    )
    return f"Successfully memorized with ID: {doc_id}"


@mcp.tool()
def search_memory(query: str, n_results: int = 3) -> str:
    """Perform semantic search over stored memories to retrieve context."""
    query_embedding = embedder.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )

    if not results["documents"] or not results["documents"][0]:
        return "No matching memories found."

    return str(results["documents"][0])


if __name__ == "__main__":
    mcp.settings.port = 8000
    mcp.settings.host = "0.0.0.0"
    mcp.run(transport="sse")