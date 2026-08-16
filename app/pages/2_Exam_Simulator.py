import re
import streamlit as st
from utils.snowflake_conn import get_snowflake_conn

conn = get_snowflake_conn()

# --- CSS CUSTOMIZATION FOR TYPOGRAPHY & SPACING ---
st.markdown(
    """
    <style>
    /* Font size and spacing for question stem */
    .exam-question-text {
        font-size: 1.18rem !important;
        font-weight: 600 !important;
        line-height: 1.6 !important;
        color: #F8FAFC !important;
        margin-bottom: 14px !important;
    }
    /* Font size and padding for option choices A, B, C, D */
    .stRadio div[role='radiogroup'] > label {
        font-size: 1.05rem !important;
        padding-top: 6px !important;
        padding-bottom: 6px !important;
        line-height: 1.5 !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- MAIN PAGE TITLE ---
st.title("📝 Exam Practice & Quiz Room")


# --- 1. METADATA FILTER ---
@st.cache_data(ttl=600)
def get_exam_metadata():
  cur = conn.cursor()
  try:
    cur.execute(
        "SELECT DISTINCT subject, lesson_name FROM MARTS.DIM_LESSON ORDER BY"
        " subject, lesson_name;"
    )
    rows = cur.fetchall()
    metadata = {}
    for subject, lesson in rows:
      if subject and lesson:
        metadata.setdefault(subject, []).append(lesson)
    return metadata
  finally:
    cur.close()


metadata = get_exam_metadata()
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
  subject_list = list(metadata.keys())
  selected_subject = st.selectbox(
      "📚 Select Subject:",
      subject_list if subject_list else ["No data available"],
  )
with col2:
  lesson_list = metadata.get(selected_subject, [])
  selected_lesson = st.selectbox(
      "📖 Select Lesson:",
      lesson_list if lesson_list else ["No data available"],
  )
with col3:
  num_questions = st.number_input(
      "🔢 Questions:", min_value=1, max_value=20, value=5
  )


# --- 2. PARSE AND NORMALIZE QUESTION DATA ---
def parse_question_data(raw_question: str, raw_answer: str):
  clean_text = raw_question.strip()

  # Locate start of option "A."
  match_a = re.search(r"\bA\.\s*", clean_text)
  if match_a:
    stem = clean_text[: match_a.start()].strip()
    options_raw = clean_text[match_a.start() :].strip()
    options_parts = re.split(r"(?=[A-D]\.\s*)", options_raw)
    options = [opt.strip() for opt in options_parts if opt.strip()]
  else:
    stem = clean_text
    options = []

  # Clean prefixes like "Câu X:", "Question X." from stem
  stem_clean = re.sub(
      r"^(?:câu|question)\s*\d+\s*[:.\-]\s*", "", stem, flags=re.IGNORECASE
  ).strip()

  # Extract correct answer key (A, B, C, or D)
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


# --- 3. DATABASE QUERY ---
def fetch_exam_bank(subj: str, l_name: str, limit_count: int):
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
    cur.execute(sql, (subj, l_name, limit_count))
    rows = cur.fetchall()

    return [parse_question_data(q_raw, a_raw) for _, q_raw, a_raw in rows]
  finally:
    cur.close()


# --- 4. START QUIZ ACTION ---
if st.button("🚀 Start Quiz", type="primary", use_container_width=True):
  with st.spinner("Generating quiz questions..."):
    questions = fetch_exam_bank(
        selected_subject, selected_lesson, num_questions
    )
    if questions:
      st.session_state.exam_questions = questions
      st.session_state.user_answers = {}
      st.session_state.is_submitted = False
    else:
      st.warning(
          f"No quiz questions available for lesson '{selected_lesson}'."
      )
      st.session_state.exam_questions = []

# --- 5. RENDER QUESTION LIST ---
if "exam_questions" in st.session_state and st.session_state.exam_questions:
  st.markdown("---")
  st.subheader(
      f"📋 {selected_subject} - {selected_lesson} "
      f"({len(st.session_state.exam_questions)} Questions)"
  )

  for idx, q in enumerate(st.session_state.exam_questions, 1):
    with st.container(border=True):
      # Combine Question Number & Stem
      st.markdown(
          f"<div class='exam-question-text'>Question {idx}: {q['stem']}</div>",
          unsafe_allow_html=True,
      )

      # Radio options selection
      if q["options"]:
        selected_option = st.radio(
            f"Options for Question {idx}:",
            q["options"],
            key=f"ans_q_{idx}",
            index=None,
            disabled=st.session_state.get("is_submitted", False),
            label_visibility="collapsed",
        )
        st.session_state.user_answers[idx] = selected_option
      else:
        st.info(q["stem"])

      # Post-submission Evaluation & Answer Reveal
      if st.session_state.get("is_submitted", False):
        user_choice = st.session_state.user_answers.get(idx)
        user_char = user_choice[0].upper() if user_choice else None
        correct_char = q["correct_char"]

        if user_char and correct_char:
          if user_char == correct_char:
            st.success(f"🎉 **Correct!** You selected: `{user_choice}`")
          else:
            st.error(
                f"❌ **Incorrect!** You selected: `{user_choice}` | Correct"
                f" answer: **{correct_char}**"
            )
        elif not user_choice:
          st.warning(
              f"⚠️ Unanswered. Correct answer:"
              f" **{correct_char or 'See detailed explanation below'}**"
          )

        with st.expander(
            f"💡 Detailed Explanation for Question {idx}", expanded=True
        ):
          st.markdown(q["raw_answer"])

  # Submit Button
  st.markdown("---")
  col_btn, _ = st.columns([2, 3])
  with col_btn:
    if not st.session_state.get("is_submitted", False):
      if st.button(
          "🏁 Submit & Grade", type="primary", use_container_width=True
      ):
        st.session_state.is_submitted = True
        st.rerun()

  # Final Score Summary
  if st.session_state.get("is_submitted", False):
    total = len(st.session_state.exam_questions)
    correct_count = 0
    for idx, q in enumerate(st.session_state.exam_questions, 1):
      u_choice = st.session_state.user_answers.get(idx)
      u_char = u_choice[0].upper() if u_choice else None
      if u_char and q["correct_char"] and u_char == q["correct_char"]:
        correct_count += 1

    score_pct = round((correct_count / total) * 100, 1)
    st.markdown("## 🏆 Quiz Results")
    res_col1, res_col2 = st.columns(2)
    res_col1.metric("Correct Answers:", f"{correct_count} / {total}")
    res_col2.metric("Accuracy Rate:", f"{score_pct}%")