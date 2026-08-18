import os
from typing import List, Union
from dotenv import load_dotenv
from google import genai
from google.genai import types
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

# Initialize Google GenAI client
genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# Wrapper class mimicking SentenceTransformer interface for backward compatibility
class GeminiEmbedder:
    """Lightweight API-based embedder using Gemini text-embedding-004 (384 dimensions)."""

    def __init__(self, output_dimensionality: int = 384):
        self.model = "gemini-embedding-001"
        self.output_dimensionality = output_dimensionality

    def encode(
        self,
        texts: Union[str, List[str]],
        show_progress_bar: bool = False,
        **kwargs,
    ) -> List[List[float]]:
        """Compute 384-dimensional dense vector embeddings via Gemini API."""
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return []

        response = genai_client.models.embed_content(
            model=self.model,
            contents=texts,
            config=types.EmbedContentConfig(
                output_dimensionality=self.output_dimensionality
            ),
        )

        return [emb.values for emb in response.embeddings]


# Export embed_model instance with identical .encode() interface
embed_model = GeminiEmbedder(output_dimensionality=384)


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