import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import snowflake.connector

# Resolve absolute paths to load .env configuration
current_dir = Path(__file__).resolve().parent  
module_dir = current_dir.parent              
root_dir = module_dir.parent                 

env_local = module_dir / ".env"
env_root = root_dir / ".env"

if env_local.exists():
    load_dotenv(dotenv_path=env_local)
elif env_root.exists():
    load_dotenv(dotenv_path=env_root)
else:
    load_dotenv()


# ----------------------------------------------------------------------
# 1. DATABASE CONNECTION
# ----------------------------------------------------------------------
def get_snowflake_connection():
    """Establish and return an active Snowflake database connection."""
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "RAG_AI_PLATFORM"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "RAW"),
    )
# (Use account with ACCOUNTADMIN role or any account having write access to RAW schema)

# ----------------------------------------------------------------------
# 2. INGESTION PIPELINE
# ----------------------------------------------------------------------
def load_to_snowflake(input_base: str = "vector_creation/documents/embedded_documents"):
    """
    Read all embedded JSON documents from the target directory
    and bulk ingest them into Snowflake RAW.RAW_CHUNKS table.
    """
    base_path = Path(input_base)
    json_files = list(base_path.rglob("*.json"))

    if not json_files:
        print(f"[WARNING] No embedded JSON files found in '{input_base}'.")
        return

    # 1. Collect all chunk payloads from JSON files
    all_records = []
    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                all_records.extend(data)
            elif isinstance(data, dict):
                all_records.append(data)

    print(
        f"🚀 Loaded {len(all_records)} chunks from {len(json_files)} JSON files."
    )
    print("🚀 Connecting to Snowflake...")

    conn = get_snowflake_connection()
    cur = conn.cursor()

    try:
        # 2. Ensure target RAW schema exists
        cur.execute("CREATE SCHEMA IF NOT EXISTS RAW;")

        # 3. Create RAW_CHUNKS table
        create_table_sql = """
        CREATE TABLE RAW_CHUNKS IF NOT EXISTS (
            chunk_id VARCHAR(255),
            file_name VARCHAR(255),
            subject VARCHAR(100),
            lesson_name VARCHAR(255),
            content_type VARCHAR(50),
            section_title VARCHAR(255),
            chunk_type VARCHAR(50),
            content VARCHAR,
            chunk_vector ARRAY,
            raw_metadata VARIANT,
            ingested_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        );
        """
        cur.execute(create_table_sql)
        print("✓ Created/Replaced table RAW.RAW_CHUNKS successfully.")

        # 4. Prepare batch insert query
        insert_sql = """
        INSERT INTO RAW_CHUNKS (
            chunk_id,
            file_name,
            subject,
            lesson_name,
            content_type,
            section_title,
            chunk_type,
            content,
            chunk_vector,
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
            column8, 
            PARSE_JSON(column9), 
            PARSE_JSON(column10)
        FROM VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # 5. Format chunk payloads into tuple rows
        rows = [
            (
                c.get("chunk_id"),
                c.get("file_name"),
                c.get("subject"),
                c.get("lesson_name"),
                c.get("content_type"),
                c.get("section_title"),
                c.get("chunk_type"),
                c.get("content"),
                json.dumps(c.get("chunk_vector", [])),
                json.dumps(c),
            )
            for c in all_records
        ]

        # 6. Execute bulk insert
        print(f"🚀 Ingesting {len(rows)} records into RAW.RAW_CHUNKS...")
        cur.executemany(insert_sql, rows)
        conn.commit()

        print(
            f"✅ Successfully ingested {len(rows)} records into Snowflake RAW.RAW_CHUNKS!"
        )

    except Exception as e:
        conn.rollback()
        print(f"✗ Load to Snowflake failed: {e}")
    finally:
        cur.close()
        conn.close()


# ----------------------------------------------------------------------
# 3. CLI INTERFACE
# ----------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CLI Tool to bulk ingest embedded JSON chunks into Snowflake RAW schema."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="vector_creation/documents/embedded_documents",
        help="Path to source embedded JSON directory (Default: vector_creation/documents/embedded_documents)",
    )

    args = parser.parse_args()

    load_to_snowflake(input_base=args.input)