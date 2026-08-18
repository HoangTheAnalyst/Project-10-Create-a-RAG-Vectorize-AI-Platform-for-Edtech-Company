import json
import os
import time
from app.config import embed_model, genai_client, get_snowflake_conn


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
                        f.chunk_vector::VECTOR(FLOAT, 384),
                        PARSE_JSON(%s)::VECTOR(FLOAT, 384)
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


def generate_llm_response(query: str, chunks: list, history: list):
    """Synthesize final response via Gemini using contextual retrieved chunks and chat history."""
    if not chunks:
        return "💡 Thầy chưa tìm thấy tài liệu liên quan. Các em hãy thử câu hỏi khác!"

    # Format retrieved document context
    context_str = "\n\n---\n\n".join([
        f"[Document {idx+1} | Subject: {c[0]} | Lesson: {c[1]} | Section: {c[2]} | Score: {c[5]:.3f}]\n{c[3]}"
        for idx, c in enumerate(chunks)
    ])

    # Preserve sliding window of conversation history
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
   - Khi giải thích bài tập: Trình bày từng bước giải thích chi tiết, nhớ xuống dòng hợp lý từng câu A, B , C , D phải xuống dòng chuẩn chỉnh, nhưng chỉ khi học sinh hỏi thì mới làm câu hỏi hoặc đưa ra đáp án cuối cùng
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
    response = genai_client.models.generate_content(
        model="gemini-3.1-flash-lite", contents=prompt
    )
    return response.text