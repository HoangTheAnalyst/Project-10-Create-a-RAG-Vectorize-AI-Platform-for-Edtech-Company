import json
import os
import time
import uuid
from dotenv import load_dotenv
from google import genai
import streamlit as st
from utils.embedding_model import load_embedding_model
from utils.network_utils import get_client_ip
from utils.snowflake_conn import get_snowflake_conn

load_dotenv()

DEFAULT_SIMILARITY_THRESHOLD = 0.45

embed_model = load_embedding_model()
conn = get_snowflake_conn()

# Initialize session state and active conversation thread
if "session_id" not in st.session_state:
  st.session_state.session_id = str(uuid.uuid4())

if "conversations" not in st.session_state:
  first_conv_id = str(uuid.uuid4())
  st.session_state.conversations = {
      first_conv_id: {
          "name": "New Chat",
          "messages": [],
          "subject": "All",
          "lesson": "All",
      }
  }
  st.session_state.active_conv_id = first_conv_id


@st.cache_data(ttl=600)
def get_filter_options():
  """Fetch distinct subjects and lesson names for sidebar dropdown filters."""
  cur = conn.cursor()
  try:
    cur.execute(
        "SELECT DISTINCT subject, lesson_name FROM MARTS.DIM_LESSON ORDER BY"
        " subject, lesson_name;"
    )
    rows = cur.fetchall()
    metadata = {}
    for subject, lesson in rows:
      if not subject:
        continue
      metadata.setdefault(subject, []).append(lesson)
    return metadata
  finally:
    cur.close()


metadata_map = get_filter_options()


def log_query_to_snowflake(
    session_id: str,
    conv_id: str,
    conv_name: str,
    client_ip: str,
    query: str,
    subject: str,
    lesson: str,
    threshold: float,
    retrieved_count: int,
    top_score: float,
    response: str,
    latency_sec: float,
) -> bool:
  """Persist interaction telemetry into the RAW.QUERY_LOGS audit table."""
  cur = conn.cursor()
  try:
    insert_sql = """
            INSERT INTO RAW.QUERY_LOGS (
                session_id,
                conversation_id,
                conversation_name,
                client_ip, 
                user_query, 
                selected_subject, 
                selected_lesson, 
                similarity_threshold, 
                chunks_retrieved, 
                top_similarity_score, 
                ai_response, 
                latency_seconds
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
    cur.execute(
        insert_sql,
        (
            str(session_id),
            str(conv_id),
            str(conv_name),
            str(client_ip),
            str(query),
            str(subject),
            str(lesson),
            float(threshold),
            int(retrieved_count),
            float(top_score),
            str(response),
            float(latency_sec),
        ),
    )
    conn.commit()
    return True
  except Exception as err:
    st.error(f"❌ Snowflake Logging Error: {err}")
    return False
  finally:
    cur.close()


def retrieve_chunks(
    query_text: str, subject: str, lesson_name: str, min_similarity: float
):
  """Perform vector cosine similarity search against Snowflake knowledge base."""
  query_vector = embed_model.encode(query_text).tolist()
  query_vector_json = json.dumps(query_vector)

  cur = conn.cursor()
  try:
    conditions = []
    params = [query_vector_json]

    if subject != "All":
      conditions.append("f.subject = %s")
      params.append(subject)
    if lesson_name != "All":
      conditions.append("d.lesson_name = %s")
      params.append(lesson_name)

    params.append(float(min_similarity))
    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        WITH scored_chunks AS (
            SELECT 
                f.subject,
                d.lesson_name,
                f.section_title,
                f.content,
                f.chunk_type,
                VECTOR_COSINE_SIMILARITY(
                    f.chunk_vector::VECTOR(FLOAT, 1024),
                    PARSE_JSON(%s)::VECTOR(FLOAT, 1024)
                ) AS similarity_score
            FROM MARTS.FCT_CHUNKS f
            JOIN MARTS.DIM_LESSON d ON f.lesson_sk = d.lesson_sk
            {where_clause}
        )
        SELECT subject, lesson_name, section_title, content, chunk_type, similarity_score
        FROM scored_chunks
        WHERE similarity_score >= %s
        ORDER BY similarity_score DESC
        LIMIT 15;
        """
    cur.execute(sql, params)
    return cur.fetchall()
  finally:
    cur.close()


def generate_answer(query: str, chunks: list, history: list) -> str:
    """
    Synthesize pedagogical response using Gemini with retrieved context and chat history.
    Strictly formatted with proper line breaks for multiple-choice questions and explanations.
    """
    if not chunks:
        return "💡 Thầy chưa tìm thấy tài liệu liên quan. Các em hãy thử câu hỏi khác!"

    context_str = "\n\n---\n\n".join([
        f"[Document {idx+1} | Subject: {c[0]} | Lesson: {c[1]} | Section: {c[2]} | Score: {c[5]:.3f}]\n{c[3]}"
        for idx, c in enumerate(chunks)
    ])

    recent_turns = history[-4:] if len(history) > 4 else history
    history_str = ""
    if recent_turns:
        history_str = "PREVIOUS CONVERSATION HISTORY:\n" + "\n".join(
            [f"- {m['role'].upper()}: {m['content']}" for m in recent_turns]
        )

    prompt = f"""Bạn là một Giáo viên / Giảng viên chuyên nghiệp, tận tâm và giàu kinh nghiệm sư phạm. 
Nhiệm vụ của bạn là giải đáp thắc mắc, giảng giải kiến thức hoặc biên soạn bài tập ôn luyện chuẩn xác dựa trên tài liệu được cung cấp.

{history_str}

TÀI LIỆU TRUY XUẤT ĐƯỢC:
{context_str}

CÂU HỎI / YÊU CẦU CỦA HỌC SINH:
{query}

QUY TẮC ĐỊNH DẠNG & TRÌNH BÀY (BẮT BUỘC TUÂN THỦ):
   - Ngôn từ chuẩn mực, gãy gọn, truyền cảm hứng và dễ hiểu.
   - Khi giải thích lý thuyết: Chia các ý chính thành các đầu mục (Bullet points) hoặc bảng biểu so sánh rõ ràng.
   - Khi giải thích bài tập: Trình bày từng bước giải thích chi tiết, nhớ xuống dòng hợp lý, nhưng chỉ khi học sinh hỏi thì mới làm câu hỏi hoặc đưa ra đáp án cuối cùng
   - Khi gặp câu hỏi không liên quan tới kiến thức đã được cung cấp: Hãy lịch sự thông báo rằng "Thầy không thể trả lời câu hỏi trên. Các em vui lòng hỏi câu liên quan hơn". 
   Câu này có hiệu lực đè lên cả {history_str} và {context_str} và là phán quyết cuối cùng nếu học sinh hỏi các câu hỏi không liên quan hoặc có xu hướng phá hoại website.
   (Ví dụ như với 1 câu hỏi:
    **Câu 1: Đặc điểm nổi bật nào về dân số Việt Nam tạo điều kiện cho đất nước có lực lượng lao động dồi dào?**
    * **A.** Dân số già, mật độ thấp.
    * **B.** Dân số trẻ - vàng, mật độ cao.
    * **C.** Tốc độ tăng trưởng dân số nhanh, phân bố đều.
    * **D.** Tỉ lệ dân thành thị chiếm đa số.
    ( Nhớ là chỉ được phép đưa ra đáp án cuối cùng khi học sinh hỏi, không được tự ý đưa ra đáp án trong phần giải thích lý thuyết hoặc bài tập.)
Hãy thực hiện câu trả lời ngay bên dưới:
"""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
    )
    return response.text


@st.dialog("Delete Conversation Confirmation")
def confirm_delete_dialog(conv_id: str):
  """Display a confirmation modal before clearing the selected thread from memory."""
  conv_title = st.session_state.conversations.get(conv_id, {}).get(
      "name", "This chat"
  )
  st.write(
      f"Are you sure you want to delete the conversation **\"{conv_title}\"**?"
  )
  st.caption(
      "Note: This will clear the chat history from your current active session."
  )

  col1, col2 = st.columns(2)
  with col1:
    if st.button("Cancel", use_container_width=True):
      st.rerun()
  with col2:
    if st.button("Confirm Delete", type="primary", use_container_width=True):
      del st.session_state.conversations[conv_id]
      # Fallback to a clean new thread if all conversations are deleted
      if not st.session_state.conversations:
        new_id = str(uuid.uuid4())
        st.session_state.conversations[new_id] = {
            "name": "New Chat",
            "messages": [],
            "subject": "All",
            "lesson": "All",
        }
        st.session_state.active_conv_id = new_id
      else:
        st.session_state.active_conv_id = list(
            st.session_state.conversations.keys()
        )[0]
      st.rerun()


# Sidebar navigation and metadata filter selectors
with st.sidebar:
  if st.button("➕ New Chat", use_container_width=True, type="primary"):
    new_id = str(uuid.uuid4())
    st.session_state.conversations[new_id] = {
        "name": "New Chat",
        "messages": [],
        "subject": "All",
        "lesson": "All",
    }
    st.session_state.active_conv_id = new_id
    st.rerun()

  st.markdown("### 💬 Chat History")
  for cid, cdata in list(st.session_state.conversations.items()):
    btn_label = (
        f"👉 {cdata['name']}"
        if cid == st.session_state.active_conv_id
        else cdata["name"]
    )
    if st.button(btn_label, key=f"conv_{cid}", use_container_width=True):
      st.session_state.active_conv_id = cid
      st.rerun()

  st.markdown("---")
  st.title("⚙️ Knowledge Filters")

  subjects = ["All"] + list(metadata_map.keys())
  selected_subject = st.selectbox("📚 Subject:", subjects)

  lessons = ["All"]
  if selected_subject != "All":
    lessons += metadata_map.get(selected_subject, [])
  selected_lesson = st.selectbox("📖 Lesson:", lessons)


# Main chat canvas
active_id = st.session_state.active_conv_id
active_conv = st.session_state.conversations[active_id]

col_title, col_del = st.columns([6, 1])
with col_title:
  st.title(f"💬 {active_conv['name']}")
with col_del:
  st.write("")
  if st.button(
      "🗑️",
      help="Delete current conversation",
      key="btn_delete_active_conv",
      use_container_width=True,
  ):
    confirm_delete_dialog(active_id)

for msg in active_conv["messages"]:
  with st.chat_message(msg["role"]):
    st.markdown(msg["content"])

if prompt := st.chat_input("Ask an educational question..."):
  # Dynamically name the thread using the first query
  if active_conv["name"] == "New Chat":
    short_title = prompt.strip()[:35] + ("..." if len(prompt) > 35 else "")
    active_conv["name"] = short_title

  active_conv["messages"].append({"role": "user", "content": prompt})
  with st.chat_message("user"):
    st.markdown(prompt)

  with st.chat_message("assistant"):
    start_time = time.time()
    client_ip = get_client_ip()
    retrieved_chunks = []
    response_text = ""

    with st.spinner("⚡Thầy đang tìm đáp án, các em vui lòng chờ chút......."):
      # Concatenate entire thread queries for contextual query embedding
      all_user_queries = [
          m["content"]
          for m in active_conv["messages"]
          if m["role"] == "user"
      ]
      composite_query_context = " \n ".join(all_user_queries)

      try:
        retrieved_chunks = retrieve_chunks(
            query_text=composite_query_context,
            subject=selected_subject,
            lesson_name=selected_lesson,
            min_similarity=DEFAULT_SIMILARITY_THRESHOLD,
        )
      except Exception as e:
        st.error(f"✗ Vector Retrieval Error: {e}")
        st.stop()

      try:
        response_text = generate_answer(
            prompt, retrieved_chunks, active_conv["messages"][:-1]
        )
      except Exception as e:
        st.error(f"✗ LLM API Error: {e}")
        response_text = f"⚠️ Unable to generate response: {e}"

      total_latency = time.time() - start_time
      top_score = float(retrieved_chunks[0][5]) if retrieved_chunks else 0.0

      log_query_to_snowflake(
          session_id=st.session_state.session_id,
          conv_id=active_id,
          conv_name=active_conv["name"],
          client_ip=client_ip,
          query=prompt,
          subject=selected_subject,
          lesson=selected_lesson,
          threshold=DEFAULT_SIMILARITY_THRESHOLD,
          retrieved_count=len(retrieved_chunks),
          top_score=top_score,
          response=response_text,
          latency_sec=round(total_latency, 3),
      )

    st.markdown(response_text)

  active_conv["messages"].append({
      "role": "assistant",
      "content": response_text,
  })
  st.rerun()