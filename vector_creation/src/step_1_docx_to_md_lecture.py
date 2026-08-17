import argparse
from collections import Counter
from pathlib import Path
import docx
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph


# ----------------------------------------------------------------------
# 1. HELPER FUNCTIONS
# ----------------------------------------------------------------------
def iter_block_items(parent):
    """Iterate through document paragraphs and tables in sequential document order."""
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


def get_font_size(paragraph, default_size: float = 12.0) -> float:
    """Retrieve the maximum font size (in points) within a paragraph."""
    sizes = [
        run.font.size.pt for run in paragraph.runs if run.font and run.font.size
    ]
    if sizes:
        return max(sizes)
    if paragraph.style and paragraph.style.font and paragraph.style.font.size:
        return paragraph.style.font.size.pt
    return default_size


def is_bold(paragraph) -> bool:
    """Check whether the paragraph contains bold text."""
    return any(run.bold for run in paragraph.runs if run.bold is not None)


def format_table_to_md(table: Table) -> str:
    """Convert a Word table into a standard Markdown table."""
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
# 2. CONVERT DOCX TO MARKDOWN (THEORY RULES)
# ----------------------------------------------------------------------
def convert_theory_docx_to_md(docx_path: Path, output_md_path: Path):
    """Convert a theory .docx document into Markdown (.md):

    - Level 3 Heading (###): Font size 12.5pt - 13.5pt AND Bold (or larger than base font).
    - Preserves tables and normal body paragraphs seamlessly.
    """
    doc = docx.Document(docx_path)
    body_sizes = [get_font_size(p) for p in doc.paragraphs if p.text.strip()]
    base_size = (
        Counter(body_sizes).most_common(1)[0][0] if body_sizes else 12.0
    )

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

        size = get_font_size(block, base_size)
        bold = is_bold(block)

        # Heading rule: 13pt font + bold
        is_theory_heading = (12.5 <= size <= 13.5 and bold) or (
            size > base_size and bold
        )

        if is_theory_heading:
            lines.append(f"\n### {text}\n")
        else:
            lines.append(text)

    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ----------------------------------------------------------------------
# 3. BATCH PROCESSING PIPELINE
# ----------------------------------------------------------------------
def batch_convert_lecture_documents(
    input_base: str,
    output_base: str,
):
    """Recursively scans the input directory and mirrors converted Markdown files into the output directory."""
    input_path = Path(input_base)
    output_path = Path(output_base)

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
        f"🚀 Starting lecture conversion for {len(docx_files)} files: '{input_path}'"
        f" -> '{output_path}'...\n"
    )

    for docx_file in docx_files:
        rel_path = docx_file.relative_to(input_path)
        output_md_path = output_path / rel_path.with_suffix(".md")
        subject = rel_path.parts[0] if len(rel_path.parts) > 1 else "General"

        try:
            convert_theory_docx_to_md(docx_file, output_md_path)
            print(f"  ✓ [{subject}] {docx_file.name} -> {output_md_path.name}")
        except Exception as err:
            print(f"  ✗ Error processing {docx_file.name}: {err}")

    print(
        f"\n✅ Lecture conversion completed! All Markdown files are stored in"
        f" '{output_base}'."
    )


# ----------------------------------------------------------------------
# 4. CLI INTERFACE
# ----------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CLI Tool to convert Lecture .docx documents into Markdown format."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="vector_creation/documents/docx_documents/Lecture",
        help=(
            "Path to source DOCX directory (Default:"
            " vector_creation/documents/docx_documents/Lecture)"
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="vector_creation/documents/md_documents/Lecture",
        help=(
            "Path to destination Markdown directory (Default:"
            " vector_creation/documents/md_documents/Lecture)"
        ),
    )

    args = parser.parse_args()

    batch_convert_lecture_documents(
        input_base=args.input,
        output_base=args.output,
    )