import json
import os
from pathlib import Path
import re


# ----------------------------------------------------------------------
# 1. CORE EXERCISE MARKDOWN CHUNKING LOGIC
# ----------------------------------------------------------------------
def chunk_exercise_markdown(md_content: str, subject: str, lesson_name: str, file_name: str) -> list:
    """
    Split an exercise Markdown document into discrete question chunks based on '### ' headers.
    Ensures question prompt and choices (A, B, C, D) stay in a single chunk.
    """
    lines = md_content.split("\n")
    chunks = []
    
    current_lines = []
    current_section = "Câu hỏi"
    chunk_index = 1

    def flush_chunk():
        nonlocal current_lines, current_section, chunk_index
        body = "\n".join(current_lines).strip()
        if body:
            # Generate structured payload
            chunk_payload = {
                "chunk_id": f"{lesson_name.replace(' ', '_').lower()}_ex_{chunk_index:04d}",
                "file_name": file_name,
                "subject": subject,
                "lesson_name": lesson_name,
                "content_type": "exercise",
                "section_title": current_section,
                "content": body
            }
            chunks.append(chunk_payload)
            chunk_index += 1
        current_lines = []

    for line in lines:
        stripped = line.strip()
        
        # Detect Level 3 Exercise Heading (### Câu ...)
        if stripped.startswith("### "):
            flush_chunk()
            heading_text = stripped.replace("### ", "").strip()
            
            # Extract clean question label (e.g. 'Câu 1', 'Câu 2')
            match = re.match(r"^(Câu\s*\d+)", heading_text)
            current_section = match.group(1) if match else heading_text
            
            # Append question text (omitting the raw markdown header tag for cleaner embeddings)
            current_lines.append(heading_text)
        elif stripped.startswith("# ") and not current_lines:
            # Skip initial file title
            continue
        else:
            current_lines.append(line)

    # Flush the final question chunk
    flush_chunk()
    return chunks


# ----------------------------------------------------------------------
# 2. FILE PROCESSOR & WRITER
# ----------------------------------------------------------------------
def process_single_exercise_file(input_md_path: Path, output_json_path: Path) -> int:
    """Read a Markdown exercise file, chunk it, and save chunks to a JSON file."""
    with open(input_md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Extract subject and lesson name from directory structure
    subject = input_md_path.parent.name
    lesson_name = input_md_path.stem
    file_name = input_md_path.name

    chunks = chunk_exercise_markdown(
        md_content=md_text,
        subject=subject,
        lesson_name=lesson_name,
        file_name=file_name
    )

    # Ensure target output directory exists
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    return len(chunks)


# ----------------------------------------------------------------------
# 3. BATCH PROCESSING PIPELINE
# ----------------------------------------------------------------------
def batch_chunk_all_exercises(
    input_base: str = "documents/md_documents/Exercise",
    output_base: str = "documents/chunking_documents/Exercise"
):
    """
    Recursively process all Markdown exercise files:
    documents/md_documents/Exercise/{Subject}/*.md
    
    Output mirrored to:
    documents/chunking_documents/Exercise/{Subject}/*.json
    """
    input_path = Path(input_base)
    if not input_path.exists():
        print(f"[WARNING] Input path does not exist: '{input_base}'")
        return

    md_files = [f for f in input_path.rglob("*.md") if not f.name.startswith("~$")]
    if not md_files:
        print(f"[WARNING] No .md files found in '{input_base}'")
        return

    print(f"🚀 Starting exercise chunking for {len(md_files)} files from '{input_base}' to '{output_base}'...\n")

    total_chunks_created = 0
    for md_file in md_files:
        rel_path = md_file.relative_to(input_path)
        output_json_path = Path(output_base) / rel_path.with_suffix(".json")

        try:
            num_chunks = process_single_exercise_file(md_file, output_json_path)
            total_chunks_created += num_chunks
            print(f"  ✓ [{rel_path.parent}] {md_file.name} -> {output_json_path.name} ({num_chunks} chunks)")
        except Exception as err:
            print(f"  ✗ Failed to chunk {md_file.name}: {err}")

    print(f"\n✅ Exercise chunking completed! Created a total of {total_chunks_created} exercise chunks in '{output_base}'.")


if __name__ == "__main__":
    batch_chunk_all_exercises(
        input_base="documents/md_documents/Exercise",
        output_base="documents/chunking_documents/Exercise"
    )