from pathlib import Path
from huggingface_hub import hf_hub_download
from llama_cpp import Llama
from sentence_transformers import SentenceTransformer
import chromadb

# Directories
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = WORKSPACE_DIR / "db"
MODELS_DIR = WORKSPACE_DIR / "models"

MODELS_DIR.mkdir(exist_ok=True)

# Global lazy-loaded models
_EMBED_MODEL = None
_LLM_MODEL = None
_CHROMA_COLLECTION = None


def get_embeddings_model():
    """Lazily load the embedding model."""
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        print("Loading embedding model (all-MiniLM-L6-v2)...")
        _EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBED_MODEL


def get_chroma_collection():
    """Lazily load ChromaDB collection."""
    global _CHROMA_COLLECTION
    if _CHROMA_COLLECTION is None:
        if not DB_DIR.exists():
            raise FileNotFoundError(
                f"Database directory {DB_DIR} does not exist. Please run ingestion first."
            )

        chroma_client = chromadb.PersistentClient(path=str(DB_DIR))
        _CHROMA_COLLECTION = chroma_client.get_or_create_collection(
            name="rag_knowledge_base"
        )
    return _CHROMA_COLLECTION


def get_llm(
    repo_id="Qwen/Qwen2.5-1.5B-Instruct-GGUF",
    filename="qwen2.5-1.5b-instruct-q4_k_m.gguf",
):
    """Lazily download and load the local GGUF model via llama-cpp-python."""
    global _LLM_MODEL
    if _LLM_MODEL is None:
        print(f"Checking for model {filename}...")
        model_path = hf_hub_download(
            repo_id=repo_id, filename=filename, cache_dir=str(MODELS_DIR)
        )
        print(f"Loading local LLM from {model_path} on CPU...")

        # Load the llama model
        # n_ctx=4096 is optimal for RAG context and doesn't overload CPU.
        # n_threads=4 matches physical cores.
        _LLM_MODEL = Llama(
            model_path=model_path, n_ctx=4096, n_threads=4, verbose=False
        )
    return _LLM_MODEL


def format_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS string."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def retrieve_context(query: str, n_results=5):
    """Retrieve relevant chunks from ChromaDB for a given query."""
    embed_model = get_embeddings_model()
    collection = get_chroma_collection()

    # Compute query embedding
    query_embedding = embed_model.encode(query).tolist()

    # Query Chroma
    results = collection.query(query_embeddings=[query_embedding], n_results=n_results)

    if not results or not results["documents"] or not results["documents"][0]:
        return []

    retrieved_chunks = []
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = (
        results["distances"][0] if "distances" in results else [0.0] * len(documents)
    )

    for doc, meta, dist in zip(documents, metadatas, distances):
        # Format citation label
        source = meta.get("source", "Unknown")
        doc_type = meta.get("type", "unknown")

        if doc_type == "pdf":
            citation = f"{source}, Page {meta.get('page', '?')}"
        elif doc_type == "video":
            start_str = format_timestamp(meta.get("start_time", 0.0))
            end_str = format_timestamp(meta.get("end_time", 0.0))
            citation = f"{source}, Timestamp {start_str} - {end_str}"
        else:
            citation = source

        retrieved_chunks.append(
            {"text": doc, "metadata": meta, "citation": citation, "distance": dist}
        )

    return retrieved_chunks


def answer_question_stream(query: str, n_results=5, temperature=0.1):
    """
    Retrieve context and yield chunks of the LLM's streamed response.
    Returns: Yields dicts with either:
      - {"type": "sources", "data": list_of_sources} at the start.
      - {"type": "content", "data": token_text} during generation.
    """
    # 1. Retrieve relevant chunks
    try:
        sources = retrieve_context(query, n_results=n_results)
    except Exception as e:
        yield {"type": "error", "data": f"Failed to retrieve context: {e}"}
        return

    yield {"type": "sources", "data": sources}

    # 2. Build prompt context
    context_str = ""
    for idx, src in enumerate(sources):
        context_str += (
            f"[{idx + 1}] Source: {src['citation']}\nContent: {src['text']}\n\n"
        )

    system_prompt = (
        "You are a helpful, professional assistant answering questions about the 'Databases for GenAI' and 'Productized Enterprise RAG' lectures.\n"
        "Your task is to answer the user's question using ONLY the provided contexts. If the context does not contain the answer, "
        "say 'I cannot find the answer in the provided lecture materials.' Do not invent facts or make up details.\n"
        "Always cite the source numbers (e.g. [1], [2], [1, 3]) in your explanation when referring to information from them.\n"
        "Keep your response concise, factual, and directly related to the question."
    )

    user_prompt = f"Context materials:\n{context_str}\nQuestion: {query}\nAnswer:"

    # 3. Load LLM and generate
    try:
        llm = get_llm()
    except Exception as e:
        yield {"type": "error", "data": f"Failed to load local LLM: {e}"}
        return

    try:
        response_stream = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
            max_tokens=768,
            temperature=temperature,
        )

        for chunk in response_stream:
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield {"type": "content", "data": content}

    except Exception as e:
        yield {"type": "error", "data": f"Failed to generate answer: {e}"}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Query the RAG chatbot")
    parser.add_argument("query", help="The question to ask")
    args = parser.parse_args()

    print(f"Query: {args.query}\n")
    print("Retrieving and generating answer...")

    sources_shown = False
    for chunk in answer_question_stream(args.query):
        if chunk["type"] == "sources" and not sources_shown:
            print("\n--- Retrieved Sources ---")
            for idx, src in enumerate(chunk["data"]):
                print(
                    f"[{idx + 1}] {src['citation']} (distance: {src['distance']:.4f})"
                )
            print("-------------------------\nAnswer: ", end="", flush=True)
            sources_shown = True
        elif chunk["type"] == "content":
            print(chunk["data"], end="", flush=True)
        elif chunk["type"] == "error":
            print(f"\nError: {chunk['data']}", flush=True)
    print("\n")
