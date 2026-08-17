import argparse
import json
from pathlib import Path
import re
import unicodedata


# ----------------------------------------------------------------------
# 1. HELPER FUNCTIONS
# ----------------------------------------------------------------------
def sanitize_id(text: str) -> str:
    """Normalize and convert special characters/Vietnamese text into a safe ASCII snake_case string."""
    text = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("utf-8")
    )
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)


# ----------------------------------------------------------------------
# 2. CORE CHUNKING LOGIC
# ----------------------------------------------------------------------
def chunk_exercise_markdown(
    md_content: str,
    subject: str,
    lesson_name: str,
    file_name: str,
) -> list:
    """Splits an exercise Markdown document into standalone chunks based on '### ' headers."""
    lines = md_content.split("\n")
    chunks = []

    current_lines = []
    current_section = "Introduction"
    chunk_index = 1
    sanitized_lesson = sanitize_id(lesson_name)

    def flush_chunk():
        nonlocal current_lines, current_section, chunk_index
        body = "\n".join(current_lines).strip()
        if body:
            is_answer = bool(
                re.search(
                    r"^Câu\s*\d+[\s:.\-_]*(\n\s*|\s+)[\*_]*đáp\s*án",
                    body,
                    re.IGNORECASE,
                )
            )
            chunk_type = "Answer" if is_answer else "Question"

            chunk_payload = {
                "chunk_id": f"{sanitized_lesson}_ex_{chunk_index:04d}",
                "file_name": file_name,
                "subject": subject,
                "lesson_name": lesson_name,
                "content_type": "exercise",
                "section_title": current_section,
                "chunk_type": chunk_type,
                "content": body,
            }
            chunks.append(chunk_payload)
            chunk_index += 1
        current_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip document-level H1 headers (# ...) at the top
        if stripped.startswith("# ") and not chunks and not current_lines:
            continue

        # Detect question/answer H3 headers (### ...)
        if stripped.startswith("### "):
            flush_chunk()
            heading_text = stripped.replace("### ", "").strip()

            match_prefix = re.match(r"^(Câu\s*\d+)", heading_text, re.IGNORECASE)
            current_section = (
                match_prefix.group(1) if match_prefix else heading_text
            )

            current_lines.append(heading_text)
        else:
            current_lines.append(line)

    flush_chunk()
    return chunks


# ----------------------------------------------------------------------
# 3. SINGLE FILE PROCESSOR
# ----------------------------------------------------------------------
def process_single_file(
    input_file: Path,
    output_file: Path,
    subject: str,
) -> int:
    """Reads a Markdown file, chunks its contents, and persists the result as a JSON file."""
    with open(input_file, "r", encoding="utf-8") as f:
        md_text = f.read()

    chunks = chunk_exercise_markdown(
        md_content=md_text,
        subject=subject,
        lesson_name=input_file.stem,
        file_name=input_file.name,
    )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    return len(chunks)


# ----------------------------------------------------------------------
# 4. BATCH PROCESSING PIPELINE
# ----------------------------------------------------------------------
def batch_chunk_documents(
    input_base: str,
    output_base: str,
):
    """Recursively scans the input directory and mirrors the chunked JSON files into the output directory."""
    input_path = Path(input_base)
    output_path = Path(output_base)

    if not input_path.exists():
        print(f"[WARNING] Input path does not exist: '{input_base}'")
        return

    md_files = [
        f for f in input_path.rglob("*.md") if not f.name.startswith("~$")
    ]
    if not md_files:
        print(f"[WARNING] No .md files found in '{input_base}'")
        return

    print(
        f"🚀 Starting chunking pipeline for {len(md_files)} files: '{input_path}'"
        f" -> '{output_path}'...\n"
    )

    total_chunks = 0
    for md_file in md_files:
        rel_path = md_file.relative_to(input_path)
        output_json_path = output_path / rel_path.with_suffix(".json")

        subject = rel_path.parts[0] if len(rel_path.parts) > 1 else "General"

        try:
            num_chunks = process_single_file(
                input_file=md_file,
                output_file=output_json_path,
                subject=subject,
            )
            total_chunks += num_chunks
            print(
                f"  ✓ [{subject}] {md_file.name} -> {output_json_path.name}"
                f" ({num_chunks} chunks)"
            )
        except Exception as err:
            print(f"  ✗ Error processing {md_file.name}: {err}")

    print(
        f"\n✅ Chunking completed! Total created: {total_chunks} chunks in"
        f" '{output_base}'."
    )


# ----------------------------------------------------------------------
# 5. CLI INTERFACE
# ----------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "CLI Tool to parse and split Markdown exercise documents into"
            " structured JSON chunks."
        )
    )
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="vector_creation/documents/md_documents/Exercise",
        help=(
            "Path to source Markdown directory (Default:"
            " vector_creation/documents/md_documents/Exercise)"
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="vector_creation/documents/chunking_documents/Exercise",
        help=(
            "Path to destination JSON directory (Default:"
            " vector_creation/documents/chunking_documents/Exercise)"
        ),
    )

    args = parser.parse_args()

    batch_chunk_documents(
        input_base=args.input,
        output_base=args.output,
    )