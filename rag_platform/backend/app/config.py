import os
from dotenv import load_dotenv
from google import genai
import requests
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

# Hugging Face Inference API Configuration (1024-dim BAAI/bge-m3)
HF_TOKEN = os.getenv("HF_TOKEN")
HF_API_URL = "https://router.huggingface.co/hf-inference/models/BAAI/bge-m3"


class HuggingFaceEmbedder:
  """Lightweight client calling Hugging Face Serverless API to generate embeddings.

  Keeps RAM usage under 100MB by avoiding local PyTorch / model weights loading.
  """

  def __init__(self, token: str, api_url: str):
    self.token = token
    self.api_url = api_url

  def encode(self, text: str) -> list[float]:
    headers = {
        "Authorization": f"Bearer {self.token}",
        "Content-Type": "application/json",
    }
    payload = {"inputs": text, "options": {"wait_for_model": True}}

    response = requests.post(
        self.api_url, headers=headers, json=payload, timeout=60
    )
    if response.status_code != 200:
      raise RuntimeError(
          f"Hugging Face API Error ({response.status_code}): {response.text}"
      )

    data = response.json()

    # BAAI/bge-m3 API returns nested list or direct list depending on payload structure
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
      return data[0]
    return data


# Initialize lightweight embedder instance (same variable name 'embed_model')
embed_model = HuggingFaceEmbedder(token=HF_TOKEN, api_url=HF_API_URL)

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