import os
from typing import List, Union
from dotenv import load_dotenv
from google import genai
from google.genai import types
import snowflake.connector

# Load environment variables from .env files in the backend or root directory
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
genai_client = genai.Client()


class GeminiEmbedder:
    """Lightweight API-based embedder compatible with Google AI Studio SDK standards."""

    def __init__(self, output_dimensionality: int = 1024):
        self.model = "gemini-embedding-001"
        self.output_dimensionality = output_dimensionality

    def encode(
        self,
        texts: Union[str, List[str]],
        task_type: str = "RETRIEVAL_QUERY",
        show_progress_bar: bool = False,
        **kwargs,
    ) -> Union[List[float], List[List[float]]]:
        """Compute dense embeddings with task-specific optimization.
        
        """
        is_single_text = isinstance(texts, str)
        content_list = [texts] if is_single_text else texts

        if not content_list:
            return [] if is_single_text else []

        response = genai_client.models.embed_content(
            model=self.model,
            contents=content_list,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self.output_dimensionality,
            ),
        )

        vectors = [[float(val) for val in emb.values] for emb in response.embeddings]

        if is_single_text:
            return vectors[0]

        return vectors


# Initialize a global embedder instance with 1024 dimensions for retrieval tasks
embed_model = GeminiEmbedder(output_dimensionality=384)


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