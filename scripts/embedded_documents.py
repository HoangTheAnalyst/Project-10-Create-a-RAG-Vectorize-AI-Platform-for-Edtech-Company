import argparse
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer


# ----------------------------------------------------------------------
# 1. HELPER / MODEL INITIALIZATION
# ----------------------------------------------------------------------
def load_embedding_model(
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
) -> SentenceTransformer:
    """Load and return the sentence transformer embedding model."""
    print(f"⏳ Loading embedding model: '{model_name}'...")
    return SentenceTransformer(model_name)


# ----------------------------------------------------------------------
# 2. SINGLE FILE PROCESSOR
# ----------------------------------------------------------------------
def process_file_embedding(
    input_json_path: Path,
    output_json_path: Path,
    embed_model: SentenceTransformer,
) -> int:
    """Read a JSON chunk file, compute embeddings, and save the updated chunks."""
    with open(input_json_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if not chunks:
        return 0

    # Prepare embedding text: combine section_title and content
    texts = [
        f"{c.get('section_title', '')}: {c.get('content', '')}" for c in chunks
    ]

    # Generate vectors
    vectors = embed_model.encode(texts, show_progress_bar=False)

    # Attach vectors to chunks
    for chunk, vec in zip(chunks, vectors):
        chunk["chunk_vector"] = vec.tolist()

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
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
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

    embed_model = load_embedding_model(model_name)

    print(
        f"🚀 Vectorizing {len(json_files)} files: '{input_path}' ->"
        f" '{output_path}'...\n"
    )

    total_embedded = 0
    for jf in json_files:
        rel_path = jf.relative_to(input_path)
        out_path = output_path / rel_path

        try:
            num_chunks = process_file_embedding(jf, out_path, embed_model)
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
        description="CLI Tool to generate vector embeddings for chunked JSON documents."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="documents/chunking_documents",
        help="Path to source chunking JSON directory (Default: documents/chunking_documents)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="documents/embedded_documents",
        help="Path to destination embedded JSON directory (Default: documents/embedded_documents)",
    )
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        help="HuggingFace model identifier for sentence embeddings (Default: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)",
    )

    args = parser.parse_args()

    batch_embed_documents(
        input_base=args.input,
        output_base=args.output,
        model_name=args.model,
    )