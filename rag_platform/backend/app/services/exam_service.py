import re
from app.config import get_snowflake_conn


def parse_question_data(raw_question: str, raw_answer: str):
    """Extract question stem, multiple-choice options, and correct answer character."""
    clean_text = raw_question.strip()
    match_a = re.search(r"\bA\.\s*", clean_text)
    if match_a:
        stem = clean_text[: match_a.start()].strip()
        options_raw = clean_text[match_a.start() :].strip()
        options_parts = re.split(r"(?=[A-D]\.\s*)", options_raw)
        options = [opt.strip() for opt in options_parts if opt.strip()]
    else:
        stem = clean_text
        options = []

    # Strip question index prefix (e.g., 'Câu 1:', 'Question 2.')
    stem_clean = re.sub(
        r"^(?:câu|question)\s*\d+\s*[:.\-]\s*", "", stem, flags=re.IGNORECASE
    ).strip()

    # Detect the correct option letter (A, B, C, or D) from raw answer explanation
    correct_match = re.search(
        r"(?:Đáp án|Đ/A|Chọn|Answer|Key|Option)?\s*[:\-\s]*([A-D])\b",
        raw_answer,
        re.IGNORECASE,
    )
    correct_char = correct_match.group(1).upper() if correct_match else None

    return {
        "stem": stem_clean,
        "options": options,
        "raw_answer": raw_answer,
        "correct_char": correct_char,
    }


def fetch_exam_questions(subj: str, lesson_name: str, limit: int):
    """Retrieve randomized question-answer chunk pairs for quizzes from Snowflake MARTS."""
    conn = get_snowflake_conn()
    cur = conn.cursor()
    try:
        sql = """
            SELECT 
                q.section_title,
                q.content AS question_content,
                COALESCE(a.content, 'No detailed explanation available.') AS answer_content
            FROM MARTS.FCT_CHUNKS q
            JOIN MARTS.DIM_LESSON d ON q.lesson_sk = d.lesson_sk
            LEFT JOIN MARTS.FCT_CHUNKS a 
                ON q.lesson_sk = a.lesson_sk 
                AND q.section_title = a.section_title
                AND LOWER(a.chunk_type) IN ('answer', 'answers')
            WHERE q.subject = %s 
              AND d.lesson_name = %s
              AND LOWER(q.chunk_type) IN ('question', 'questions')
            ORDER BY RANDOM()
            LIMIT %s;
            """
        cur.execute(sql, (subj, lesson_name, limit))
        rows = cur.fetchall()
        return [parse_question_data(q_raw, a_raw) for _, q_raw, a_raw in rows]
    finally:
        cur.close()
        conn.close()