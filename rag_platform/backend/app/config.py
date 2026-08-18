import os
from dotenv import load_dotenv
from google import genai
from sentence_transformers import SentenceTransformer
import snowflake.connector

# Resolve absolute paths to load .env configuration
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(backend_dir)

env_backend = os.path.join(backend_dir, ".env")
env_root = os.path.join(root_dir, ".env")

if os.path.exists(env_backend):
    load_dotenv(dotenv_path=env_backend)
elif os.path.exists(env_root):
    load_dotenv(dotenv_path=env_root)
else:
    load_dotenv()

# Initialize 1024-dimensional embedding model in memory
embed_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Initialize Google GenAI client
genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# Connect to Snowflake (Least-privilege: SELECT on MARTS and INSERT on QUERY_LOGS)
def get_snowflake_conn():
    """Establish and return an active Snowflake database connection."""
    user = os.getenv("SNOWFLAKE_USER")
    password = os.getenv("SNOWFLAKE_PASSWORD")
    account = os.getenv("SNOWFLAKE_ACCOUNT")

    if not all([user, password, account]):
        raise ValueError(
            "Missing Snowflake connection credentials in .env file! "
            f"(USER: {bool(user)}, PWD: {bool(password)}, ACC: {bool(account)})"
        )

    return snowflake.connector.connect(
        user=user,
        password=password,
        account=account,
        role=os.getenv("SNOWFLAKE_ROLE", "STREAMLIT_ROLE"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "RAG_AI_PLATFORM"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "MARTS"),
    )