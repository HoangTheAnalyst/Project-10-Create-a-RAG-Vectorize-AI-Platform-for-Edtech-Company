import json
import os
from pathlib import Path
from dotenv import load_dotenv
import snowflake.connector

# Load environment variables from .env file
load_dotenv()


def get_snowflake_connection():
    """Establish and return a connection to Snowflake."""
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "RAG_PORTFOLIO_DB"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "RAW"),
    )


def initialize_raw_table(cursor):
    """Create the destination RAW table if it does not exist."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS RAW_CHUNKS (
        chunk_id VARCHAR(100),
        file_name VARCHAR(255),
        subject VARCHAR(100),
        lesson_name VARCHAR(255),
        content_type VARCHAR(50),
        section_title VARCHAR(255),
        content VARCHAR,
        raw_metadata VARIANT,
        ingested_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    );
    """
    cursor.execute(create_table_sql)
    print("✓ Initialized RAW.RAW_CHUNKS table.")


def collect_all_chunks(base_dir: str = "documents/chunking_documents") -> list:
    """Read all JSON chunk files recursively from the chunking directory."""
    base_path = Path(base_dir)
    json_files = list(base_path.rglob("*.json"))

    if not json_files:
        print(f"[WARNING] No JSON files found in '{base_dir}'")
        return []

    all_records = []
    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                all_records.extend(data)
            elif isinstance(data, dict):
                all_records.append(data)

    print(
        f"✓ Collected {len(all_records)} chunks from {len(json_files)} files."
    )
    return all_records


def load_chunks_to_snowflake():
    """Main execution pipeline to batch ingest data into Snowflake."""
    chunks = collect_all_chunks("documents/chunking_documents")
    if not chunks:
        print("No data to load. Exiting.")
        return

    print("🚀 Connecting to Snowflake...")
    conn = get_snowflake_connection()
    cur = conn.cursor()

    try:
        # 1. Setup table
        initialize_raw_table(cur)

        # 2. Prepare batch insert query
        insert_sql = """
        INSERT INTO RAW_CHUNKS (
            chunk_id,
            file_name,
            subject,
            lesson_name,
            content_type,
            section_title,
            content,
            raw_metadata
        )
        SELECT 
            column1, 
            column2, 
            column3, 
            column4, 
            column5, 
            column6, 
            column7, 
            PARSE_JSON(column8)
        FROM VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        # 3. Format records as tuples
        rows_to_insert = [
            (
                c.get("chunk_id"),
                c.get("file_name"),
                c.get("subject"),
                c.get("lesson_name"),
                c.get("content_type"),
                c.get("section_title"),
                c.get("content"),
                json.dumps(
                    c
                ),  # Preserve full JSON payload inside VARIANT column
            )
            for c in chunks
        ]

        print(f"🚀 Ingesting {len(rows_to_insert)} rows into RAW.RAW_CHUNKS...")
        cur.executemany(insert_sql, rows_to_insert)
        conn.commit()

        print(
            f"✅ Successfully loaded {len(rows_to_insert)} chunks into Snowflake RAW.RAW_CHUNKS!"
        )

    except Exception as e:
        conn.rollback()
        print(f"✗ Ingestion failed: {e}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    load_chunks_to_snowflake()