import streamlit as st

st.set_page_config(
    page_title="EduRAG Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

chat_page = st.Page(
    "pages/1_Chat_Assistant.py",
    title="Chat Assistant",
    icon="💬",
    default=True,
)
exam_page = st.Page(
    "pages/2_Exam_Simulator.py",
    title="Exam Simulator",
    icon="📝",
)
analytics_page = st.Page(
    "pages/3_Daily_Monitoring.py",
    title="Daily Monitoring",
    icon="📊",
)

pg = st.navigation({
    "Learning & Practice": [chat_page, exam_page],
    "Administration & Analytics": [analytics_page],
})

pg.run()