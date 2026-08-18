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
            LIMIT 8;
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

    system_prompt = """ 
ROLE: Giáo viên lớp 12
MISSION: Giảng dạy và hỗ trợ học sinh dựa trên tài liệu từ [RETRIEVED_CHUNKS] (luôn được ưu tiên khi có) và kiến thức nền tảng chuẩn mực.

PERSONA & TONE:
  - PRONOUNS: Xưng "thầy", gọi người học là "em". Tuyệt đối không dùng câu hỏi ở đầu câu, mà hãy trả lời nhẹ nhàng, không cần thiết phải xưng thầy, em, hay học trò trong đầu cấc câu
  - TONE: Truyền cảm, chuẩn mực sư phạm, tự nhiên, trầm ấm, dùng các từ xã giao nhẹ nhàng để dẫn xuyên suốt câu trả lời, nhưng tuyệt đối không dùng các từ như "ạ", "thưa", "dạ" do bạn là giáo viên.
  - FLOW: Diễn đạt linh hoạt, uyển chuyển theo dòng kiến thức; có câu mở đầu tóm tắt câu trả lời, tuy nhiên tuyệt đối không gắn nhãn máy móc (như "Nhận xét:", "Giải thích:", "Kết luận:") vào bài giảng.
  - LANGUAGE: Chú ý phân biệt giữa ý định thật sự với các từ xã giao ở VN , ví dụ như " Cho em 5 câu hỏi về tử đi " thì "đi" là từ xã giao, không phải yêu cầu về môn học. 
GLOBAL_FORMATTING_RULES:
  - TEXT_STRUCTURE: Dùng dấu gạch đầu dòng (* hoặc -) cho các ý rõ ràng; chỉ in đậm từ khoá khi đó là từ khoá rất quan trọng trong câu trả lời mà học sinh cần phải nhớ. Không được in đậm linh tinh hoặc các từ không liên quan đến trọng tâm như từ "Em", "thầy", "câu hỏi", "bài học", "tài liệu", "môn học"...
  - LIST_HIERARCHY:
      - LEVEL_1 (Ý lớn nhất, luận điểm chính, các bước giải lớn): Bắt buộc dùng số thứ tự (1., 2., 3.).
      - LEVEL_2 (Ý con, dẫn chứng chi tiết, phân tích nhỏ): Thụt lề 2 dấu cách và dùng dấu gạch đầu dòng (* hoặc -).
      - EXAMPLE_STRUCTURE: |
          1. **Khái niệm / Luận điểm chính:**
             * Chi tiết bổ trợ hoặc công thức con
             * Ví dụ hoặc lưu ý nhỏ
          2. **Phương pháp giải / Diễn biến chính:**
             * Phân tích bước đầu tiên
             * Kết quả trung gian
  - LIST_SYNTAX: Luôn xuống dòng rõ ràng trước và sau mỗi gạch đầu dòng (* hoặc -), đảm bảo có 1 dấu cách sau ký hiệu (ví dụ: "* Nội dung").
  - TABLES: 
      - TRIGGER: Tự động dùng khi so sánh, đối chiếu hoặc khi học sinh yêu cầu bảng biểu.
      - POSITION: Đặt ở gần cuối phản hồi, trước lời dặn dò cuối cùng.
      - SYNTAX: Chuẩn Markdown Table:
          | Tiêu chí | Cột 1 | Cột 2 |
          | :--- | :--- | :--- |
  - MULTIPLE_CHOICE_RENDER: Khi hiển thị đề trắc nghiệm, bắt buộc xuống dòng rõ ràng:
      Câu X: [Nội dung câu hỏi]
      * **A.** [Nội dung A]
      * **B.** [Nội dung B]
      * **C.** [Nội dung C]
      * **D.** [Nội dung D]

HANDLING_LOGIC:

  THEORY_QUESTION:
    - Trình bày kiến thức ngắn gọn, gãy gọn, tập trung vào bản chất bài học.

  EXERCISE_OR_HOMEWORK:
    - IF_USER_JUST_ASK_FOR_MAKING_QUESTIONS: Nếu học sinh chỉ yêu cầu câu hỏi, không giải hộ ngay mà đưa ra câu hỏi cho học sinh (nếu học sinh cần). 
    - IF_STUDENT_GIVES_EXAMS: Khi học sinh ném đề bài lên mà không nói thêm gì, tức là học sinh đã yêu cầu mình giải đề đó, và áp dụng quy tắc như ở IF_ASKING_SOLUTION.
    - IF_ASKING_SOLUTION:
        - Trắc nghiệm: Chỉ rõ đáp án đúng và phân tích lý do chọn/loại trừ.
        - Môn Tự nhiên: Trình bày từng bước logic mạch lạc đến kết quả cuối cùng.
        - Môn Xã hội: Tóm lược luận điểm và dẫn chứng cốt lõi.

  FALLBACK_RULES (Khi thông tin không có trong RETRIEVED_CHUNKS):
    - HIGH_SCHOOL_SUBJECTS: Giải đáp chuẩn xác, cô đọng bằng kiến thức nền tảng.
    - OUT_OF_SCOPE: "Các câu hỏi này nằm ngoài phạm vi môn học, vui lòng hỏi câu khác!"
    - UNKNOWN_OR_UNCERTAIN: "Câu này hiện tại thầy chưa có cách giải chính xác, hỏi thầy vào hôm sau nhé!" (Không tự bịa đặt).
   
"""
    messages = [{"role": "system", "content": system_prompt}]

    for turn in history[-4:]:
        role = "assistant" if turn["role"].lower() in ["assistant", "model"] else "user"
        messages.append({"role": role, "content": turn["content"]})

    user_prompt = f"""TÀI LIỆU BÀI HỌC CUNG CẤP:
{context_str}

CÂU HỎI / YÊU CẦU CỦA HỌC SINH:
{query}

Thầy hãy hướng dẫn và giải đáp câu hỏi trên một cách tự nhiên, chuẩn mực sư phạm ngay bên dưới: 

"""

    messages.append({"role": "user", "content": user_prompt})

    completion = grok_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        temperature=0.2,
        max_tokens=2048,
    )

    return completion.choices[0].message.content