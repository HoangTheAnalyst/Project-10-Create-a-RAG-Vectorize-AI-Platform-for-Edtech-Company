from sentence_transformers import SentenceTransformer
import streamlit as st


@st.cache_resource
def load_embedding_model():
  """Tải mô hình embedding 1024 chiều vào RAM (chỉ load 1 lần)."""
  return SentenceTransformer("BAAI/bge-m3")