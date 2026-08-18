import os
from typing import List, Union
from dotenv import load_dotenv
from google import genai
from google.genai import types
import snowflake.connector

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

genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


class GeminiEmbedder:
    def __init__(self, output_dimensionality: int = 384):
        self.model = "text-embedding-004"
        self.output_dimensionality = output_dimensionality

    def encode(
        self,
        texts: Union[str, List[str]],
        show_progress_bar: bool = False,
        **kwargs,
    ) -> List[List[float]]:
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


embed_model = GeminiEmbedder(output_dimensionality=384)


def get_snowflake_conn():
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