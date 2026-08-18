import argparse
import sys
from pathlib import Path

# Add src folder and root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "vector_creation" / "src"))
sys.path.append(str(BASE_DIR / "src"))


# ----------------------------------------------------------------------
# PIPELINE STEP WRAPPERS
# ----------------------------------------------------------------------
def run_full_pipeline(
    docx_lecture_dir: str = "vector_creation/documents/docx_documents/Lecture",
    docx_exercise_dir: str = "vector_creation/documents/docx_documents/Exercise",
    md_lecture_dir: str = "vector_creation/documents/md_documents/Lecture",
    md_exercise_dir: str = "vector_creation/documents/md_documents/Exercise",
    chunks_lecture_dir: str = "vector_creation/documents/chunking_documents/Lecture",
    chunks_exercise_dir: str = "vector_creation/documents/chunking_documents/Exercise",
    chunks_base_dir: str = "vector_creation/documents/chunking_documents",
    embedded_dir: str = "vector_creation/documents/embedded_documents",
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    skip_snowflake: bool = False,
):
    print("=" * 70)
    print("🚀 STARTING COMPLETE VECTOR CREATION & INGESTION PIPELINE")
    print("=" * 70)

    # ------------------------------------------------------------------
    # STEP 1 & 2: CONVERT DOCX TO MARKDOWN (LECTURE & EXERCISE)
    # ------------------------------------------------------------------
    print("\n--- [STEP 1 & 2] CONVERTING DOCX TO MARKDOWN ---")
    try:
        from step_1_docx_to_md_lecture import batch_convert_lecture_documents
        from step_2_docx_to_md_exercise import batch_convert_exercise_documents

        print("\n>> Converting Lecture Documents...")
        batch_convert_lecture_documents(
            input_base=docx_lecture_dir,
            output_base=md_lecture_dir,
        )

        print("\n>> Converting Exercise Documents...")
        batch_convert_exercise_documents(
            input_base=docx_exercise_dir,
            output_base=md_exercise_dir,
        )
    except ImportError as e:
        print(f"✗ Failed to import docx conversion modules: {e}")
        return

    # ------------------------------------------------------------------
    # STEP 3 & 4: CHUNK MARKDOWN INTO STRUCTURED JSON
    # ------------------------------------------------------------------
    print("\n--- [STEP 3 & 4] CHUNKING MARKDOWN DOCUMENTS ---")
    try:
        from step_3_chunking_md_lecture import (
            batch_chunk_documents as chunk_lecture_docs,
        )
        from step_4_chunking_md_exercise import (
            batch_chunk_documents as chunk_exercise_docs,
        )

        print("\n>> Chunking Lecture Documents...")
        chunk_lecture_docs(
            input_base=md_lecture_dir,
            output_base=chunks_lecture_dir,
        )

        print("\n>> Chunking Exercise Documents...")
        chunk_exercise_docs(
            input_base=md_exercise_dir,
            output_base=chunks_exercise_dir,
        )
    except ImportError as e:
        print(f"✗ Failed to import chunking modules: {e}")
        return

    # ------------------------------------------------------------------
    # STEP 5: GENERATE VECTOR EMBEDDINGS
    # ------------------------------------------------------------------
    print("\n--- [STEP 5] GENERATING VECTOR EMBEDDINGS ---")
    try:
        from step_5_embedded_documents import batch_embed_documents

        batch_embed_documents(
            input_base=chunks_base_dir,
            output_base=embedded_dir,
            model_name=embedding_model,
        )
    except ImportError as e:
        print(f"✗ Failed to import embedding module: {e}")
        return

    # ------------------------------------------------------------------
    # STEP 6: LOAD EMBEDDED CHUNKS TO SNOWFLAKE RAW
    # ------------------------------------------------------------------
    if not skip_snowflake:
        print("\n--- [STEP 6] LOADING TO SNOWFLAKE RAW SCHEMA ---")
        try:
            from step_6_insert_data_to_snowflake import load_to_snowflake

            load_to_snowflake(input_base=embedded_dir)
        except ImportError as e:
            print(f"✗ Failed to import Snowflake loading module: {e}")
            return
    else:
        print("\n--- [STEP 6] SKIPPING SNOWFLAKE INGESTION ---")

    print("\n" + "=" * 70)
    print("✅ PIPELINE EXECUTION FINISHED SUCCESSFULLY!")
    print("=" * 70)


# ----------------------------------------------------------------------
# CLI INTERFACE
# ----------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Master orchestration pipeline for vector creation and Snowflake ingestion."
    )
    parser.add_argument(
        "--docx-lecture",
        type=str,
        default="vector_creation/documents/docx_documents/Lecture",
        help="Path to source DOCX Lecture directory",
    )
    parser.add_argument(
        "--docx-exercise",
        type=str,
        default="vector_creation/documents/docx_documents/Exercise",
        help="Path to source DOCX Exercise directory",
    )
    parser.add_argument(
        "--md-lecture",
        type=str,
        default="vector_creation/documents/md_documents/Lecture",
        help="Path to destination Markdown Lecture directory",
    )
    parser.add_argument(
        "--md-exercise",
        type=str,
        default="vector_creation/documents/md_documents/Exercise",
        help="Path to destination Markdown Exercise directory",
    )
    parser.add_argument(
        "--chunks-lecture",
        type=str,
        default="vector_creation/documents/chunking_documents/Lecture",
        help="Path to destination JSON chunks Lecture directory",
    )
    parser.add_argument(
        "--chunks-exercise",
        type=str,
        default="vector_creation/documents/chunking_documents/Exercise",
        help="Path to destination JSON chunks Exercise directory",
    )
    parser.add_argument(
        "--chunks-base",
        type=str,
        default="vector_creation/documents/chunking_documents",
        help="Path to source directory containing all JSON chunks for embedding",
    )
    parser.add_argument(
        "--embedded",
        type=str,
        default="vector_creation/documents/embedded_documents",
        help="Path to destination embedded JSON directory",
    )
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default="embed-multilingual-v3.0",
        help="Cohere model identifier",
    )
    parser.add_argument(
        "--skip-snowflake",
        action="store_true",
        help="Skip Snowflake database ingestion step",
    )

    args = parser.parse_args()

    run_full_pipeline(
        docx_lecture_dir=args.docx_lecture,
        docx_exercise_dir=args.docx_exercise,
        md_lecture_dir=args.md_lecture,
        md_exercise_dir=args.md_exercise,
        chunks_lecture_dir=args.chunks_lecture,
        chunks_exercise_dir=args.chunks_exercise,
        chunks_base_dir=args.chunks_base,
        embedded_dir=args.embedded,
        embedding_model=args.model,
        skip_snowflake=args.skip_snowflake,
    )