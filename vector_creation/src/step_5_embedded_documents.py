import argparse
import json
import os
import time
from pathlib import Path
import cohere
from dotenv import load_dotenv

# ----------------------------------------------------------------------
# 1. HELPER / MODEL INITIALIZATION
# ----------------------------------------------------------------------
def load_cohere_client() -> cohere.ClientV2:
    """Load environment variables and return Cohere API Client."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)

    env_local = os.path.join(current_dir, ".env")
    env_root = os.path.join(root_dir, ".env")

    if os.path.exists(env_local):
        load_dotenv(dotenv_path=env_local)
    elif os.path.exists(env_root):
        load_dotenv(dotenv_path=env_root)
    else:
        load_dotenv()

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise ValueError("Missing 'COHERE_API_KEY' in .env file!")

    print("⏳ Initializing Cohere API Client...")
    return cohere.ClientV2(api_key=api_key)


# ----------------------------------------------------------------------
# 2. SINGLE FILE PROCESSOR
# ----------------------------------------------------------------------
def process_file_embedding(
    input_json_path: Path,
    output_json_path: Path,
    client: cohere.ClientV2,
    model_name: str = "embed-multilingual-v3.0",
    batch_size: int = 48,
) -> int:
    """Read a JSON chunk file, compute embeddings via Cohere API (1024 dims), and save."""
    with open(input_json_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if not chunks:
        return 0

    texts = [
        f"{c.get('section_title', '')}: {c.get('content', '')}" for c in chunks
    ]

    all_vectors = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        
        # Cohere API call for Document Ingestion (1024-dimensional vector)
        response = client.embed(
            texts=batch,
            model=model_name,
            input_type="search_document",
            embedding_types=["float"],
        )
        
        for vec in response.embeddings.float:
            all_vectors.append([float(val) for val in vec])

        # Rate-limit safety pause for trial key
        time.sleep(0.3)

    for chunk, vec in zip(chunks, all_vectors):
        chunk["chunk_vector"] = vec

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    return len(chunks)


# ----------------------------------------------------------------------
# 3. BATCH PROCESSING PIPELINE
# ----------------------------------------------------------------------
def batch_embed_documents(
    input_base: str,
    output_base: str,
    model_name: str = "embed-multilingual-v3.0",
):
    """Recursively scan input directory, generate embeddings, and mirror output structure."""
    input_path = Path(input_base)
    output_path = Path(output_base)

    if not input_path.exists():
        print(f"[WARNING] Input path does not exist: '{input_base}'")
        return

    json_files = [
        f for f in input_path.rglob("*.json") if not f.name.startswith("~$")
    ]
    if not json_files:
        print(f"[WARNING] No .json files found in '{input_base}'")
        return

    client = load_cohere_client()

    print(
        f"🚀 Vectorizing {len(json_files)} files via Cohere API ({model_name}):\n"
        f"   '{input_path}' -> '{output_path}'...\n"
    )

    total_embedded = 0
    for jf in json_files:
        rel_path = jf.relative_to(input_path)
        out_path = output_path / rel_path

        try:
            num_chunks = process_file_embedding(
                input_json_path=jf,
                output_json_path=out_path,
                client=client,
                model_name=model_name,
            )
            total_embedded += num_chunks
            print(f"  ✓ [{rel_path.parent}] {jf.name} ({num_chunks} chunks)")
        except Exception as err:
            print(f"  ✗ Error embedding {jf.name}: {err}")

    print(
        f"\n✅ Finished generating embeddings! Total chunks: {total_embedded} in"
        f" '{output_base}'."
    )


# ----------------------------------------------------------------------
# 4. CLI INTERFACE
# ----------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CLI Tool to generate vector embeddings for chunked JSON documents via Cohere API."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="vector_creation/documents/chunking_documents",
        help="Path to source chunking JSON directory (Default: vector_creation/documents/chunking_documents)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="vector_creation/documents/embedded_documents",
        help="Path to destination embedded JSON directory (Default: vector_creation/documents/embedded_documents)",
    )
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default="embed-multilingual-v3.0",
        help="Cohere embedding model identifier (Default: embed-multilingual-v3.0 - 1024 dimensions)",
    )

    args = parser.parse_args()

    batch_embed_documents(
        input_base=args.input,
        output_base=args.output,
        model_name=args.model,
    )