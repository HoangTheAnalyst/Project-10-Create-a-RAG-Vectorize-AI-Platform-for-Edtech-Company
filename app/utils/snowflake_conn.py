import os
from dotenv import load_dotenv
import snowflake.connector
import streamlit as st

load_dotenv()


@st.cache_resource
def get_snowflake_conn():
  """Khởi tạo và cache connection pool tới Snowflake."""
  return snowflake.connector.connect(
      user=os.getenv("SNOWFLAKE_USER"),
      password=os.getenv("SNOWFLAKE_PASSWORD"),
      account=os.getenv("SNOWFLAKE_ACCOUNT"),
      role=os.getenv("SNOWFLAKE_ROLE", "STREAMLIT_ROLE"),
      warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
      database=os.getenv("SNOWFLAKE_DATABASE", "RAG_AI_PLATFORM"),
      schema=os.getenv("SNOWFLAKE_SCHEMA", "MARTS"),
  )