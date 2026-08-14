import os
from pathlib import Path
import re
import docx
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph


# ----------------------------------------------------------------------
# 1. HELPER FUNCTIONS
# ----------------------------------------------------------------------
def iter_block_items(parent):
    """Iterate through document paragraphs and tables in sequential order."""
    parent_elm = (
        parent.element.body
        if isinstance(parent, docx.document.Document)
        else parent._element
    )
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def is_exercise_heading(text: str) -> bool:
    """Check if the text represents an exercise question.

    Matches any string starting with capitalized 'Câu' (e.g. 'Câu 1:', 'Câu
    2.', 'Câu hỏi').
    """
    cleaned = text.strip()
    return bool(re.match(r"^Câu(\s+\d+|\b)", cleaned))


def format_table_to_md(table) -> str:
    """Convert a Word table into standard Markdown format."""
    rows = table.rows
    if not rows:
        return ""
    headers = [cell.text.strip().replace("\n", " ") for cell in rows[0].cells]
    md = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows[1:]:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        md.append("| " + " | ".join(cells) + " |")
    return "\n" + "\n".join(md) + "\n"


# ----------------------------------------------------------------------
# 2. CONVERT EXERCISE DOCX TO MARKDOWN
# ----------------------------------------------------------------------
def convert_exercise_docx_to_md(docx_path: Path, output_md_path: Path):
    """Convert an Exercise .docx document into Markdown (.md):

    - Level 3 Heading (###): Any line starting with capitalized 'Câu'.
    - Preserves tables, answer options (A, B, C, D), and regular text.
    """
    doc = docx.Document(docx_path)
    lines = []

    lesson_name = docx_path.stem
    lines.append(f"# {lesson_name}\n")

    for block in iter_block_items(doc):
        if isinstance(block, Table):
            lines.append(format_table_to_md(block))
            continue

        text = block.text.strip()
        if not text:
            continue

        # Exercise Heading Rule: Capitalized 'Câu' at the beginning
        if is_exercise_heading(text):
            lines.append(f"\n### {text}\n")
        else:
            lines.append(text)

    # Ensure target output directory exists
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ----------------------------------------------------------------------
# 3. BATCH PROCESSING PIPELINE
# ----------------------------------------------------------------------
def convert_all_exercise_docs(
    input_base: str = "documents/docx_documents/Exercise",
    output_base: str = "documents/md_documents/Exercise",
):
    """Recursively process: documents/docx_documents/Exercise/{Subject}/*.docx

    And mirror output to: documents/md_documents/Exercise/{Subject}/*.md
    """
    input_path = Path(input_base)
    if not input_path.exists():
        print(f"[WARNING] Input path does not exist: '{input_base}'")
        return

    docx_files = [
        f for f in input_path.rglob("*.docx") if not f.name.startswith("~$")
    ]
    if not docx_files:
        print(f"[WARNING] No .docx files found in '{input_base}'")
        return

    print(
        f"🚀 Starting exercise conversion for {len(docx_files)} files from"
        f" '{input_base}' to '{output_base}'...\n"
    )

    for docx_file in docx_files:
        rel_path = docx_file.relative_to(input_path)
        output_md_path = Path(output_base) / rel_path.with_suffix(".md")

        try:
            convert_exercise_docx_to_md(docx_file, output_md_path)
            print(f"  ✓ [{rel_path.parent}] {docx_file.name} -> {output_md_path}")
        except Exception as err:
            print(f"  ✗ Failed to process {docx_file.name}: {err}")

    print(
        f"\n✅ Exercise conversion completed! All Markdown files are stored in"
        f" '{output_base}'."
    )


if __name__ == "__main__":
    convert_all_exercise_docs(
        input_base="documents/docx_documents/Exercise",
        output_base="documents/md_documents/Exercise",
    )