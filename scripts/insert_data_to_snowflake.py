import json
import os
from pathlib import Path
from dotenv import load_dotenv
import snowflake.connector

load_dotenv()


def get_snowflake_connection():
    """Establish and return a Snowflake connection."""
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "RAG_PORTFOLIO_DB"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "RAW"),
    )


def load_to_snowflake(input_base: str = "documents/embedded_documents"):
    base_path = Path(input_base)
    json_files = list(base_path.rglob("*.json"))

    if not json_files:
        print(
            f"[WARNING] No embedded JSON files found in '{input_base}'. Please run step 5 first."
        )
        return

    # 1. Thu thập toàn bộ chunks từ tất cả các file JSON
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
        # 2. Đảm bảo Schema RAW tồn tại
        cur.execute("CREATE SCHEMA IF NOT EXISTS RAW;")

        # 3. Tạo mới (hoặc làm sạch hoàn toàn) bảng RAW_CHUNKS
        create_table_sql = """
        CREATE OR REPLACE TABLE RAW_CHUNKS (
            chunk_id VARCHAR(255),
            file_name VARCHAR(255),
            subject VARCHAR(100),
            lesson_name VARCHAR(255),
            content_type VARCHAR(50),
            section_title VARCHAR(255),
            content VARCHAR,
            chunk_vector ARRAY,
            raw_metadata VARIANT,
            ingested_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        );
        """
        cur.execute(create_table_sql)
        print("✓ Created/Replaced table RAW.RAW_CHUNKS successfully.")

        # 4. Chuẩn bị câu lệnh chèn dữ liệu theo Batch
        insert_sql = """
        INSERT INTO RAW_CHUNKS (
            chunk_id,
            file_name,
            subject,
            lesson_name,
            content_type,
            section_title,
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
            PARSE_JSON(column8), 
            PARSE_JSON(column9)
        FROM VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # 5. Format dữ liệu thành danh sách Tuples
        rows = [
            (
                c.get("chunk_id"),
                c.get("file_name"),
                c.get("subject"),
                c.get("lesson_name"),
                c.get("content_type"),
                c.get("section_title"),
                c.get("content"),
                json.dumps(c.get("chunk_vector", [])),
                json.dumps(c),
            )
            for c in all_records
        ]

        # 6. Thực thi Insert toàn bộ dữ liệu
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


if __name__ == "__main__":
    load_to_snowflake()