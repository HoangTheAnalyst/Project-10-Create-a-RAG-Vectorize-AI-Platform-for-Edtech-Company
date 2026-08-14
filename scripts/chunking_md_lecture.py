import json
import os
from pathlib import Path
import re


# ----------------------------------------------------------------------
# 1. CORE MARKDOWN CHUNKING LOGIC
# ----------------------------------------------------------------------
def chunk_lecture_markdown(md_content: str, subject: str, lesson_name: str, file_name: str) -> list:
    """Split a lecture Markdown document into structured chunks based on '### ' headers."""
    lines = md_content.split("\n")
    chunks = []
    
    current_lines = []
    current_section = lesson_name  # Default fallback title before any '### ' header
    chunk_index = 1

    def flush_chunk():
        nonlocal current_lines, current_section, chunk_index
        body = "\n".join(current_lines).strip()
        if body:
            # Generate structured payload
            chunk_payload = {
                "chunk_id": f"{lesson_name.replace(' ', '_').lower()}_chk_{chunk_index:04d}",
                "file_name": file_name,
                "subject": subject,
                "lesson_name": lesson_name,
                "content_type": "theory",
                "section_title": current_section,
                "content": body
            }
            chunks.append(chunk_payload)
            chunk_index += 1
        current_lines = []

    for line in lines:
        stripped = line.strip()
        
        # Detect Level 3 Markdown Heading (### )
        if stripped.startswith("### "):
            flush_chunk()
            # Extract section title without the '### ' prefix
            current_section = stripped.replace("### ", "").strip()
            current_lines.append(line)
        # Skip top-level '# ' title if it duplicates lesson_name, or append it to body
        elif stripped.startswith("# ") and not current_lines:
            continue
        else:
            current_lines.append(line)

    # Flush any remaining text in the document
    flush_chunk()
    return chunks


# ----------------------------------------------------------------------
# 2. FILE PROCESSOR & WRITER
# ----------------------------------------------------------------------
def process_single_lecture_file(input_md_path: Path, output_json_path: Path):
    """Read a Markdown file, chunk it, and save the chunks to a JSON file."""
    with open(input_md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Extract hierarchy from path structure: Lecture/{Subject}/{Lesson}.md
    subject = input_md_path.parent.name
    lesson_name = input_md_path.stem
    file_name = input_md_path.name

    chunks = chunk_lecture_markdown(
        md_content=md_text,
        subject=subject,
        lesson_name=lesson_name,
        file_name=file_name
    )

    # Ensure output directory exists
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    return len(chunks)


# ----------------------------------------------------------------------
# 3. BATCH PROCESSING PIPELINE
# ----------------------------------------------------------------------
def batch_chunk_all_lectures(
    input_base: str = "documents/md_documents/Lecture",
    output_base: str = "documents/chunking_documents/Lecture"
):
    """
    Recursively process all Markdown lecture files:
    documents/md_documents/Lecture/{Subject}/*.md
    
    Output mirrored to:
    documents/chunking_documents/Lecture/{Subject}/*.json
    """
    input_path = Path(input_base)
    if not input_path.exists():
        print(f"[WARNING] Input path does not exist: '{input_base}'")
        return

    md_files = [f for f in input_path.rglob("*.md") if not f.name.startswith("~$")]
    if not md_files:
        print(f"[WARNING] No .md files found in '{input_base}'")
        return

    print(f"🚀 Starting theory chunking for {len(md_files)} files from '{input_base}' to '{output_base}'...\n")

    total_chunks_created = 0
    for md_file in md_files:
        rel_path = md_file.relative_to(input_path)
        output_json_path = Path(output_base) / rel_path.with_suffix(".json")

        try:
            num_chunks = process_single_lecture_file(md_file, output_json_path)
            total_chunks_created += num_chunks
            print(f"  ✓ [{rel_path.parent}] {md_file.name} -> {output_json_path.name} ({num_chunks} chunks)")
        except Exception as err:
            print(f"  ✗ Failed to chunk {md_file.name}: {err}")

    print(f"\n✅ Lecture chunking completed! Created a total of {total_chunks_created} chunks in '{output_base}'.")


if __name__ == "__main__":
    batch_chunk_all_lectures(
        input_base="documents/md_documents/Lecture",
        output_base="documents/chunking_documents/Lecture"
    )