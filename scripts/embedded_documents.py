import json
from pathlib import Path
from sentence_transformers import SentenceTransformer

# Load embedding model
print("⏳ Loading embedding model...")
embed_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

def process_file_embedding(input_json_path: Path, output_json_path: Path):
    with open(input_json_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    
    if not chunks:
        return 0

    # Chuẩn bị text: section_title + content
    texts = [f"{c.get('section_title', '')}: {c.get('content', '')}" for c in chunks]
    
    # Sinh vector
    vectors = embed_model.encode(texts, show_progress_bar=False)
    
    # Gán vector vào từng chunk
    for chunk, vec in zip(chunks, vectors):
        chunk["chunk_vector"] = vec.tolist()
        
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
        
    return len(chunks)

def batch_embed_all(
    input_base: str = "documents/chunking_documents",
    output_base: str = "documents/embedded_documents"
):
    input_path = Path(input_base)
    json_files = list(input_path.rglob("*.json"))
    
    if not json_files:
        print(f"[WARNING] No files found in {input_base}")
        return
        
    print(f"🚀 Vectorizing {len(json_files)} files to '{output_base}'...\n")
    total_embedded = 0
    for jf in json_files:
        rel = jf.relative_to(input_path)
        out_path = Path(output_base) / rel
        n = process_file_embedding(jf, out_path)
        total_embedded += n
        print(f"  ✓ Embedded {jf.name} ({n} chunks)")
        
    print(f"\n✅ Finished generating embeddings for {total_embedded} chunks!")

if __name__ == "__main__":
    batch_embed_all()