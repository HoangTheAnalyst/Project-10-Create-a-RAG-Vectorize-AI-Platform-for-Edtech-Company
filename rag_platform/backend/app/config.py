import os
from typing import List, Union
import cohere
from dotenv import load_dotenv
from groq import Groq
import snowflake.connector


# Resolve absolute paths to load .env configuration from backend or root directory
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


#2. Cohere embedding client (1024 Dimensions)
cohere_api_key = os.getenv("COHERE_API_KEY")
if not cohere_api_key:
    raise ValueError("Missing 'COHERE_API_KEY' in .env file!")

cohere_client = cohere.ClientV2(api_key=cohere_api_key)


class CohereEmbedder:
    """Lightweight API-based embedder using Cohere (1024 dimensions)."""

    def __init__(self, model: str = "embed-multilingual-v3.0"):
        self.model = model

    def encode(
        self,
        texts: Union[str, List[str]],
        input_type: str = "search_query",
        show_progress_bar: bool = False,
        **kwargs,
    ) -> Union[List[float], List[List[float]]]:
        """Compute dense vector embeddings via Cohere API."""
        is_single_text = isinstance(texts, str)
        content_list = [texts] if is_single_text else texts

        if not content_list:
            return [] if is_single_text else []

        response = cohere_client.embed(
            texts=content_list,
            model=self.model,
            input_type=input_type,
            embedding_types=["float"],
        )

        vectors = [[float(val) for val in vec] for vec in response.embeddings.float]

        if is_single_text:
            return vectors[0]

        return vectors


# Global embedding model instance for retrieval tasks
embed_model = CohereEmbedder(model="embed-multilingual-v3.0")


# Grok API client for advanced vector search and reasoning
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("Missing 'GROQ_API_KEY' in .env file!")

grok_client = Groq(api_key=groq_api_key)


# Snowflake database connection utility
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