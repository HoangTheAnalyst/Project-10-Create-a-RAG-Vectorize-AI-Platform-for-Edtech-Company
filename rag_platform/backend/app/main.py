import time
from app.models import ChatRequest, ExamRequest
from app.services.chat_service import (
    fetch_filter_metadata,
    generate_llm_response,
    log_query_to_snowflake,
    retrieve_chunks,
)
from app.services.dash_service import fetch_dashboard_analytics
from app.services.exam_service import fetch_exam_questions
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="RAG AI Core Platform API", version="2.0.0")

# Enable CORS for frontend client interactions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/metadata")
async def get_metadata():
    """Retrieve available subjects and lesson hierarchy."""
    return fetch_filter_metadata()


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest, request: Request):
    """Handle multi-turn conversational chat, semantic retrieval, and telemetry logging."""
    start_time = time.time()

    # Extract client IP safely to avoid NoneType errors
    client_ip = "127.0.0.1"
    if request.headers.get("x-forwarded-for"):
        client_ip = request.headers.get("x-forwarded-for").split(",")[0].strip()
    elif request.client and request.client.host:
        client_ip = request.client.host

    try:
        # Build composite multi-turn context from user conversation history
        all_user_queries = [
            m["content"] for m in req.history if m.get("role") == "user"
        ]
        all_user_queries.append(req.query)
        composite_context = " \n ".join(all_user_queries)

        # 1. Retrieve matching knowledge chunks from Snowflake
        chunks = retrieve_chunks(
            query_text=composite_context,
            subject=req.subject,
            lesson_name=req.lesson,
            min_similarity=req.threshold,
        )

        # 2. Generate contextual response using LLM
        response_text = generate_llm_response(req.query, chunks, req.history)
        latency = time.time() - start_time
        top_score = float(chunks[0][5]) if chunks else 0.0

        # 3. Log audit telemetry to Snowflake RAW.QUERY_LOGS
        try:
            log_query_to_snowflake(
                session_id=req.session_id,
                conv_id=req.conv_id,
                conv_name=req.conv_name,
                client_ip=client_ip,
                query=req.query,
                subject=req.subject,
                lesson=req.lesson,
                threshold=req.threshold,
                retrieved_count=len(chunks),
                top_score=top_score,
                response=response_text,
                latency_sec=round(latency, 3),
            )
        except Exception as log_err:
            print(f"⚠️ [SNOWFLAKE LOGGING WARNING]: {log_err}")

        return {
            "reply": response_text,
            "chunks_count": len(chunks),
            "score": top_score,
        }

    except Exception as e:
        print(f"❌ [CHAT ENDPOINT ERROR]: {e}")
        return {
            "reply": f"⚠️ System error: {str(e)}",
            "chunks_count": 0,
            "score": 0.0,
        }


@app.post("/api/exam")
async def exam_endpoint(req: ExamRequest):
    """Fetch structured multiple-choice quiz questions."""
    questions = fetch_exam_questions(req.subject, req.lesson, req.limit)
    return {"questions": questions}


@app.get("/api/dashboard")
async def dashboard_endpoint(
    start_date: str = None, end_date: str = None, subject: str = "All"
):
    """Fetch aggregated telemetry KPIs, trends, and distribution metrics."""
    return fetch_dashboard_analytics(start_date, end_date, subject)