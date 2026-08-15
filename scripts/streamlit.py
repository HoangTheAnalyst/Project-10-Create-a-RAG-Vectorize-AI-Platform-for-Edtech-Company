import json
import os
import socket
import time
import snowflake.connector
import streamlit as st
from dotenv import load_dotenv
from google import genai
from sentence_transformers import SentenceTransformer

load_dotenv()

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="EduRAG - Assistant & Query Logger",
    page_icon="🎓",
    layout="wide",
)


# --- 2. CLIENT IP IDENTIFIER ---
def get_client_ip() -> str:
    """Detect client IP address via Streamlit request headers or fallback to local IP."""
    try:
        # Check Streamlit context headers (Works behind reverse proxy / cloud deployment)
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            headers = st.context.headers
            if headers:
                if "X-Forwarded-For" in headers:
                    return headers["X-Forwarded-For"].split(",")[0].strip()
                if "Host" in headers:
                    return headers["Host"].split(":")[0].strip()
    except Exception:
        pass

    # Fallback to local network socket IP
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except Exception:
        return "127.0.0.1"


# --- 3. CACHING RESOURCES ---
@st.cache_resource
def load_embedding_model():
    print("[INIT] Loading SentenceTransformer: BAAI/bge-m3...")
    return SentenceTransformer("BAAI/bge-m3")


@st.cache_resource
def get_snowflake_conn():
    print("[INIT] Establishing Snowflake connection pool...")
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "RAG_AI_PLATFORM"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "MARTS")
    )


embed_model = load_embedding_model()
conn = get_snowflake_conn()


# --- 4. METADATA RETRIEVAL ---
@st.cache_data(ttl=600)
def get_filter_options():
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT DISTINCT subject, lesson_name FROM MARTS.DIM_LESSON ORDER"
            " BY subject, lesson_name;"
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


# --- 5. SNOWFLAKE INTERACTION LOGGER ---
def log_query_to_snowflake(
    client_ip: str,
    query: str,
    subject: str,
    lesson: str,
    threshold: float,
    retrieved_count: int,
    top_score: float,
    response: str,
    latency_sec: float,
):
    """Logs conversation metadata, client IP, and performance metrics into RAW.QUERY_LOGS."""
    cur = conn.cursor()
    try:
        cur.execute("CREATE SCHEMA IF NOT EXISTS RAW;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS RAW.QUERY_LOGS (
                query_id VARCHAR(36) DEFAULT UUID_STRING(),
                client_ip VARCHAR(50),
                user_query VARCHAR,
                selected_subject VARCHAR(100),
                selected_lesson VARCHAR(255),
                similarity_threshold FLOAT,
                chunks_retrieved INT,
                top_similarity_score FLOAT,
                ai_response VARCHAR,
                latency_seconds FLOAT,
                created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
            );
        """)
        insert_sql = """
            INSERT INTO RAW.QUERY_LOGS (
                client_ip, user_query, selected_subject, selected_lesson, 
                similarity_threshold, chunks_retrieved, top_similarity_score, 
                ai_response, latency_seconds
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        cur.execute(
            insert_sql,
            (
                client_ip,
                query,
                subject,
                lesson,
                threshold,
                retrieved_count,
                top_score,
                response,
                latency_sec,
            ),
        )
        conn.commit()
    except Exception as err:
        print(f"[ERROR] Failed to log interaction to Snowflake: {err}")
    finally:
        cur.close()


# --- 6. VECTOR SEARCH RETRIEVAL ---
def retrieve_chunks(
    query: str, subject: str, lesson_name: str, min_similarity: float
):
    query_vector = embed_model.encode(query).tolist()
    query_vector_json = json.dumps(query_vector)

    cur = conn.cursor()
    try:
        conditions = []
        params = [query_vector_json]

        if subject != "Tất cả":
            conditions.append("f.subject = %s")
            params.append(subject)
        if lesson_name != "Tất cả":
            conditions.append("d.lesson_name = %s")
            params.append(lesson_name)

        params.append(min_similarity)
        where_clause = (
            ("WHERE " + " AND ".join(conditions)) if conditions else ""
        )

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


# --- 7. GEMINI GENERATION ---
def generate_answer(query: str, chunks: list) -> str:
    if not chunks:
        return "💡 Không tìm thấy đoạn kiến thức nào đạt ngưỡng tương đồng yêu cầu. Vui lòng hạ ngưỡng lọc hoặc thay đổi câu hỏi."

    context_str = "\n\n---\n\n".join([
        f"[Tài liệu {idx+1} | Môn: {c[0]} | Bài: {c[1]} | Mục: {c[2]} | Điểm:"
        f" {c[5]:.3f}]\n{c[3]}"
        for idx, c in enumerate(chunks)
    ])

    prompt = f"""Bạn là trợ lý học tập thông minh. Dưới đây là các trích đoạn tài liệu truy xuất được từ database.

NGỮ CẢNH:
{context_str}

CÂU HỎI:
{query}

NHIỆM VỤ:
- Đọc, đối chiếu và tổng hợp câu trả lời chuẩn xác dựa trên ngữ cảnh đã cho.
- Bỏ qua các chi tiết không liên quan đến câu hỏi.
- Trình bày dạng Markdown mạch lạc, chuẩn sư phạm.
"""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
    )
    return response.text


# --- 8. SIDEBAR FILTERS ---
metadata_map = get_filter_options()
with st.sidebar:
    st.title("⚙️ Cấu Hình")
    subjects = ["Tất cả"] + list(metadata_map.keys())
    selected_subject = st.selectbox("📚 Môn học:", subjects)

    lessons = ["Tất cả"]
    if selected_subject != "Tất cả":
        lessons += metadata_map.get(selected_subject, [])
    selected_lesson = st.selectbox("📖 Bài học:", lessons)

    min_threshold = st.slider(
        "🎚️ Similarity Threshold:",
        min_value=0.40,
        max_value=0.85,
        value=0.60,
        step=0.05,
    )

    if st.button("🗑️ Xóa hội thoại", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# --- 9. CHAT INTERFACE ---
st.title("🎓 EduRAG Knowledge Assistant")
st.caption(
    f"Subject: **{selected_subject}** | Lesson: **{selected_lesson}** |"
    f" Threshold: **{min_threshold:.2f}**"
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander(
                f"📖 Xem {len(msg['sources'])} trích đoạn tài liệu"
            ):
                for s in msg["sources"]:
                    st.markdown(
                        f"**📚 {s['subject']} | 📖 {s['lesson']} | 📌"
                        f" {s['title']}** *(Điểm: {s['score']:.3f})*"
                    )
                    st.info(s["content"])

if prompt := st.chat_input("Nhập câu hỏi học tập..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        start_time = time.time()
        client_ip = get_client_ip()
        retrieved_chunks = []
        response_text = ""

        # Tracking journey via Status container
        with st.status(
            "⚡ Đang xử lý quy trình RAG Pipeline...", expanded=True
        ) as status:
            # Step 1: Client info & Embedding
            st.write(
                f"🌐 **Khởi tạo:** Client IP `{client_ip}` | Mã hóa vector"
                " 1024 chiều..."
            )
            t0 = time.time()
            _ = embed_model.encode(prompt)
            st.write(f"✓ Vector encoding hoàn tất trong {time.time() - t0:.2f}s")

            # Step 2: Vector Search
            st.write("🔍 **Bước 2:** Truy vấn Cosine Similarity trên Snowflake...")
            t1 = time.time()
            try:
                retrieved_chunks = retrieve_chunks(
                    query=prompt,
                    subject=selected_subject,
                    lesson_name=selected_lesson,
                    min_similarity=min_threshold,
                )
                st.write(
                    f"✓ Tìm thấy **{len(retrieved_chunks)}** chunks thỏa mãn độ"
                    f" khớp $\ge {min_threshold:.2f}$ ({time.time() - t1:.2f}s)"
                )
            except Exception as e:
                st.error(f"✗ Lỗi truy vấn Vector DB: {e}")
                status.update(
                    label="Pipeline thất bại ở bước Database!", state="error"
                )
                st.stop()

            # Step 3: LLM Generation
            st.write("✍️ **Bước 3:** Gửi ngữ cảnh và sinh phản hồi với Gemini...")
            t2 = time.time()
            try:
                response_text = generate_answer(prompt, retrieved_chunks)
                st.write(
                    f"✓ Gemini hoàn tất sinh phản hồi trong"
                    f" {time.time() - t2:.2f}s"
                )
            except Exception as e:
                st.error(f"✗ Lỗi gọi LLM API: {e}")
                response_text = f"⚠️ Không thể sinh câu trả lời: {e}"
                status.update(
                    label="Pipeline thất bại ở bước LLM!", state="error"
                )

            # Step 4: Snowflake Logging
            st.write("📝 **Bước 4:** Ghi log phiên tương tác vào Snowflake...")
            total_latency = time.time() - start_time
            top_score = (
                float(retrieved_chunks[0][5]) if retrieved_chunks else 0.0
            )

            log_query_to_snowflake(
                client_ip=client_ip,
                query=prompt,
                subject=selected_subject,
                lesson=selected_lesson,
                threshold=min_threshold,
                retrieved_count=len(retrieved_chunks),
                top_score=top_score,
                response=response_text,
                latency_sec=round(total_latency, 3),
            )
            st.write(
                f"✓ Log tương tác từ IP `{client_ip}` đã lưu vào"
                " `RAW.QUERY_LOGS`"
            )

            status.update(
                label=f"Hoàn thành toàn bộ quy trình ({total_latency:.2f}s)!",
                state="complete",
                expanded=False,
            )

        st.markdown(response_text)

        sources = []
        if retrieved_chunks:
            with st.expander(
                f"📖 Xem {len(retrieved_chunks)} trích đoạn tài liệu"
            ):
                for row in retrieved_chunks:
                    subj, l_name, sec_title, content, _, score = row
                    sources.append({
                        "subject": subj,
                        "lesson": l_name,
                        "title": sec_title,
                        "content": content,
                        "score": score,
                    })
                    st.markdown(
                        f"**📚 {subj} | 📖 {l_name} | 📌 {sec_title}** *(Điểm:"
                        f" {score:.3f})*"
                    )
                    st.info(content)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "sources": sources,
    })