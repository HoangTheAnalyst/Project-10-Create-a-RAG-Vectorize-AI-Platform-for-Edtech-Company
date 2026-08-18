import json
import os
import time
from app.config import embed_model, grok_client, get_snowflake_conn


def fetch_filter_metadata():
    """Retrieve distinct subjects and lesson hierarchy from the dimension table."""
    conn = get_snowflake_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT DISTINCT subject, lesson_name FROM MARTS.DIM_LESSON ORDER BY"
            " subject, lesson_name;"
        )
        rows = cur.fetchall()
        metadata = {}
        for subj, lesson in rows:
            if subj and lesson:
                metadata.setdefault(subj, []).append(lesson)
        return metadata
    finally:
        cur.close()
        conn.close()


def retrieve_chunks(
    query_text: str, subject: str, lesson_name: str, min_similarity: float
):
    """Encode query text and perform cosine similarity search on vector chunks in Snowflake."""
    query_vector = embed_model.encode(query_text)
    query_vector_json = json.dumps(query_vector)

    conn = get_snowflake_conn()
    cur = conn.cursor()
    try:
        params = [query_vector_json]
        conditions = []

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
        conn.close()


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
):
    """Insert query telemetry and model latency metrics into Snowflake RAW.QUERY_LOGS."""
    conn = get_snowflake_conn()
    cur = conn.cursor()
    try:
        insert_sql = """
            INSERT INTO RAW.QUERY_LOGS (
                session_id, conversation_id, conversation_name, client_ip, 
                user_query, selected_subject, selected_lesson, similarity_threshold, 
                chunks_retrieved, top_similarity_score, ai_response, latency_seconds
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
    finally:
        cur.close()
        conn.close()


def generate_llm_response(query: str, chunks: list, history: list) -> str:
    """Synthesize structured, pedagogically sound responses via Groq/LLM."""
    if not chunks:
        return "💡 Thầy chào em! Hiện tại hệ thống chưa tìm thấy dữ liệu bài học liên quan đến câu hỏi này. Em hãy kiểm tra lại bộ lọc môn/bài hoặc diễn đạt lại câu hỏi nhé!"

    context_str = "\n\n---\n\n".join([
        f"[Tài liệu {idx+1} | Môn: {c[0]} | Bài: {c[1]} | Phần: {c[2]} | Điểm tương đồng: {c[5]:.3f}]\n{c[3]}"
        for idx, c in enumerate(chunks)
    ])

    system_prompt = """Bạn là một Thầy giáo / Giảng viên tâm huyết, chuẩn mực và có nghiệp vụ sư phạm xuất sắc.
Nhiệm vụ của bạn là giải thích kiến thức, hướng dẫn tư duy phương pháp học và tạo bài tập ôn luyện dựa HOÀN TOÀN vào tài liệu bài học được cấp.

---
🎯 PHONG THÁI SƯ PHẠM & XƯNG HÔ:
- Xưng "Thầy" và gọi người học là "em" hoặc "các em". Giọng văn ấm áp, mạch lạc, dễ hiểu và truyền cảm hứng.
- Trực tiếp giải quyết trọng tâm câu hỏi của học sinh, không mở bài hay kết bài rườm rà.

---
📝 QUY TẮC ĐỊNH DẠNG LINH HOẠT THEO TÀI LIỆU:
1. Khi giải thích lý thuyết thông thường:
   - Trả lời bằng các đoạn văn gãy gọn kết hợp gạch đầu dòng (* hoặc -) rõ ràng, khoa học.
   - CHỈ DÙNG BẢNG BIỂU khi tài liệu gốc (chunks) vốn là dạng bảng, hoặc khi học sinh yêu cầu so sánh/đối chiếu trực diện giữa các đối tượng.
   - Nếu dùng bảng, bắt buộc dùng đúng cú pháp Markdown chuẩn:
     | Tiêu chí | Cột 1 | Cột 2 |
     | :--- | :--- | :--- |

2. Khi tạo câu hỏi ôn tập / bài tập trắc nghiệm:
   - Đặt câu hỏi in đậm rõ ràng.
   - Mỗi phương án A, B, C, D BẮT BUỘC nằm trên một dòng riêng:
     * **A.** Nội dung đáp án A
     * **B.** Nội dung đáp án B
     * **C.** Nội dung đáp án C
     * **D.** Nội dung đáp án D
   - TUYỆT ĐỐI KHÔNG tự tiện đưa ra đáp án hay lời giải chi tiết khi học sinh chỉ nhờ ra đề. Chỉ giải đáp và công bố kết quả khi học sinh hỏi đáp án hoặc đã nộp câu trả lời.

3. Xử lý câu hỏi ngoài phạm vi tài liệu:
   - Nếu câu hỏi không liên quan đến tài liệu được cấp, lịch sự từ chối: "Thầy rất tiếc là nội dung này nằm ngoài phạm vi tài liệu bài học hiện tại. Các em vui lòng đặt câu hỏi liên quan đến kiến thức môn học nhé!"."""

    messages = [{"role": "system", "content": system_prompt}]

    for turn in history[-4:]:
        role = "assistant" if turn["role"].lower() in ["assistant", "model"] else "user"
        messages.append({"role": role, "content": turn["content"]})

    user_prompt = f"""TÀI LIỆU BÀI HỌC CUNG CẤP:
{context_str}

CÂU HỎI / YÊU CẦU CỦA HỌC SINH:
{query}

Thầy hãy hướng dẫn và giải đáp câu hỏi trên một cách tự nhiên, chuẩn mực sư phạm ngay bên dưới:"""

    messages.append({"role": "user", "content": user_prompt})

    completion = grok_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        temperature=0.3,
        max_tokens=4096,
    )

    return completion.choices[0].message.content