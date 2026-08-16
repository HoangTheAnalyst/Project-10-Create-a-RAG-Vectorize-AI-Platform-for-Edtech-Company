import socket
import streamlit as st


def get_client_ip() -> str:
  """Xác định địa chỉ IP của Client qua Headers hoặc fallback về Socket."""
  try:
    if hasattr(st, "context") and hasattr(st.context, "headers"):
      headers = st.context.headers
      if headers:
        if "X-Forwarded-For" in headers:
          return headers["X-Forwarded-For"].split(",")[0].strip()
        if "Host" in headers:
          return headers["Host"].split(":")[0].strip()
  except Exception:
    pass

  try:
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)
  except Exception:
    return "127.0.0.1"