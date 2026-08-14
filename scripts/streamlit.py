import json
import os
import snowflake.connector
import streamlit as st
from dotenv import load_dotenv
from google import genai
from sentence_transformers import SentenceTransformer

# Load biến môi trường
load_dotenv()

# --- 1. CẤU HÌNH GIAO DIỆN ---
st.set_page_config(
    page_title="EduRAG - Trợ Lý Học Tập Thông Minh",
    page_icon="🎓",
    layout="wide",
)


# --- 2. CACHING TÀI NGUYÊN (MODEL & DATABASE) ---
@st.cache_resource
def load_model():
    return SentenceTransformer(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )


@st.cache_resource
def get_snowflake_conn():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "RAG_AI_PLATFORM"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "MARTS"),
    )


embed_model = load_model()
conn = get_snowflake_conn()


# --- 3. TRUY XUẤT METADATA TỪ DIM_LESSON ---
@st.cache_data(ttl=600)
def get_subjects():
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT DISTINCT subject FROM MARTS.DIM_LESSON ORDER BY subject;"
        )
        return ["Tất cả"] + [row[0] for row in cur.fetchall() if row[0]]
    finally:
        cur.close()


@st.cache_data(ttl=600)
def get_lessons_by_subject(subject: str):
    cur = conn.cursor()
    try:
        if subject == "Tất cả":
            cur.execute(
                "SELECT DISTINCT lesson_name FROM MARTS.DIM_LESSON ORDER BY"
                " lesson_name;"
            )
        else:
            cur.execute(
                """
                SELECT DISTINCT lesson_name 
                FROM MARTS.DIM_LESSON 
                WHERE subject = %s 
                ORDER BY lesson_name;
            """,
                (subject,),
            )
        return ["Tất cả"] + [row[0] for row in cur.fetchall() if row[0]]
    finally:
        cur.close()


# --- 4. VECTOR SEARCH THEO NGƯỠNG TƯƠNG ĐỒNG (DYNAMIC THRESHOLD) ---
def retrieve_chunks_by_threshold(
    query: str, subject: str, lesson_name: str, min_similarity: float = 0.60
):
    """Lấy TẤT CẢ các chunks có độ tương đồng >= min_similarity (không giới hạn cố định Top-K)."""
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

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Dùng CTE tính điểm rồi lọc WHERE similarity_score >= min_similarity
        # Giữ LIMIT an toàn 15 để tránh vượt quá context window của LLM nếu dữ liệu quá lớn
        sql_query = f"""
        WITH scored_chunks AS (
            SELECT 
                f.subject,
                d.lesson_name,
                f.section_title,
                f.content,
                VECTOR_COSINE_SIMILARITY(
                    f.chunk_vector::VECTOR(FLOAT, 384),
                    PARSE_JSON(%s)::VECTOR(FLOAT, 384)
                ) AS similarity_score
            FROM MARTS.FCT_CHUNKS f
            JOIN MARTS.DIM_LESSON d ON f.lesson_sk = d.lesson_sk
            {where_clause}
        )
        SELECT 
            subject, 
            lesson_name, 
            section_title, 
            content, 
            similarity_score
        FROM scored_chunks
        WHERE similarity_score >= %s
        ORDER BY similarity_score DESC
        LIMIT 15;
        """

        cur.execute(sql_query, params)
        return cur.fetchall()
    finally:
        cur.close()


# --- 5. GỌI GEMINI VỚI CƠ CHẾ TỰ ĐÁNH GIÁ NGỮ CẢNH ---
def generate_rag_answer(query: str, chunks: list) -> str:
    if not chunks:
        return (
            "💡 **Không tìm thấy tài liệu phù hợp:**\n"
            "Không có đoạn kiến thức nào đạt ngưỡng tương đồng yêu cầu. "
            "Bạn hãy thử hạ ngưỡng độ khớp ở Sidebar hoặc đổi từ khóa tra cứu."
        )

    # Ghép toàn bộ các chunks hợp lệ kèm điểm tương đồng
    context_text = "\n\n---\n\n".join(
        [
            f"[Tài liệu {idx+1} | Môn: {c[0]} | Bài: {c[1]} | Mục: {c[2]} |"
            f" Độ khớp: {c[4]:.3f}]\n{c[3]}"
            for idx, c in enumerate(chunks)
        ]
    )

    prompt = f"""Bạn là một chuyên gia học thuật và trợ lý AI thông minh. Dưới đây là danh sách các đoạn trích giáo trình tiềm năng được truy xuất từ cơ sở dữ liệu.

NGỮ CẢNH CUNG CẤP:
{context_text}

CÂU HỎI CỦA NGƯỜI DÙNG:
{query}

NHIỆM VỤ CỦA BẠN:
1. Đọc và tự đánh giá các tài liệu trên: Đoạn nào thực sự liên quan đến câu hỏi thì tổng hợp lại; đoạn nào thông tin râu ria hoặc không khớp câu hỏi thì bỏ qua.
2. Trả lời một cách sư phạm, chi tiết, chuẩn xác dựa trên các thông tin đáng tin cậy nhất.
3. Trình bày dạng Markdown với tiêu đề, gạch đầu dòng rõ ràng, dễ tiếp thu.
"""
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"⚠️ Lỗi khi gọi AI: {str(e)}"


# --- 6. SIDEBAR: BỘ LỌC VÀ ĐIỀU CHỈNH NGƯỠNG ---
with st.sidebar:
    st.title("⚙️ Cấu Hình Tra Cứu")

    subject_list = get_subjects()
    selected_subject = st.selectbox("📚 Chọn môn học:", subject_list)

    lesson_list = get_lessons_by_subject(selected_subject)
    selected_lesson = st.selectbox("📖 Chọn bài học:", lesson_list)

    st.markdown("---")

    # Thay thế Top-K bằng Slider chọn ngưỡng tương đồng tối thiểu
    min_similarity_score = st.slider(
        "🎚️ Ngưỡng tương đồng tối thiểu (Threshold):",
        min_value=0.50,
        max_value=0.85,
        value=0.60,
        step=0.05,
        help="Chỉ những đoạn tài liệu có điểm Cosine Similarity lớn hơn hoặc bằng ngưỡng này mới được gửi tới AI.",
    )

    st.caption(
        f"📌 *Đang lấy tất cả tài liệu có độ khớp $\ge {min_similarity_score:.2f}$*"
    )

    st.markdown("---")
    if st.button("🗑️ Xóa hội thoại"):
        st.session_state.messages = []
        st.rerun()


# --- 7. GIAO DIỆN CHAT ---
st.title("🎓 EduRAG Knowledge Assistant")
st.caption(
    f"Chế độ: **Dynamic Retrieval** | Lọc: **{selected_subject}** ➔"
    f" **{selected_lesson}** (Ngưỡng $\ge {min_similarity_score:.2f}$)"
)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Hiển thị lịch sử chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander(
                f"📖 Xem {len(msg['sources'])} tài liệu trích dẫn đã dùng"
            ):
                for s in msg["sources"]:
                    st.markdown(
                        f"**📚 {s['subject']} | 📖 {s['lesson']} | 📌"
                        f" {s['title']}** *(Điểm khớp: {s['score']:.3f})*"
                    )
                    st.info(s["content"])

# Nhận câu hỏi mới
if prompt := st.chat_input("Nhập câu hỏi bạn muốn tra cứu..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner(
            f"🔍 Đang quét toàn bộ tài liệu có độ khớp >= {min_similarity_score:.2f}..."
        ):
            retrieved_chunks = retrieve_chunks_by_threshold(
                query=prompt,
                subject=selected_subject,
                lesson_name=selected_lesson,
                min_similarity=min_similarity_score,
            )

        with st.spinner("✍️ AI đang thẩm định tài liệu và viết câu trả lời..."):
            response_text = generate_rag_answer(prompt, retrieved_chunks)
            st.markdown(response_text)

        sources = []
        if retrieved_chunks:
            with st.expander(
                f"📖 Xem {len(retrieved_chunks)} tài liệu trích dẫn (Độ khớp >="
                f" {min_similarity_score:.2f})"
            ):
                for row in retrieved_chunks:
                    subj, l_name, sec_title, content, score = row
                    sources.append(
                        {
                            "subject": subj,
                            "lesson": l_name,
                            "title": sec_title,
                            "content": content,
                            "score": score,
                        }
                    )
                    st.markdown(
                        f"**📚 {subj} | 📖 {l_name} | 📌 {sec_title}** *(Điểm"
                        f" khớp: {score:.3f})*"
                    )
                    st.info(content)

    st.session_state.messages.append(
        {"role": "assistant", "content": response_text, "sources": sources}
    )