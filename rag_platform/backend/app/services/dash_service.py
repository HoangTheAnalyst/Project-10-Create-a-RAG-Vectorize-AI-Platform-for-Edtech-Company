import pandas as pd
from app.config import get_snowflake_conn


def fetch_dashboard_analytics(
    start_date: str = None, end_date: str = None, subject: str = "All"
):
    """Fetch and aggregate telemetry metrics, chart datasets, and the marts log records table."""
    conn = get_snowflake_conn()
    cur = conn.cursor()
    try:
        # Query analytical telemetry data from MARTS_LOG.FCT_LOG
        sql = """
            SELECT 
                query_sk, hashed_client_ip, session_sk, conversation_sk, lesson_sk,
                selected_subject, selected_lesson, similarity_threshold, chunks_retrieved,
                top_similarity_score, latency_seconds, user_query_length, ai_response_length,
                similarity_score_diff, no_chunks_retrieved, high_latency, created_at,
                DATE_TRUNC('day', created_at) AS log_date
            FROM MARTS_LOG.FCT_LOG
            ORDER BY created_at DESC;
            """
        cur.execute(sql)
        cols = [col[0].lower() for col in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=cols)
    finally:
        cur.close()
        conn.close()

    if df.empty:
        return {}

    # Format timestamp and date columns
    df["log_date"] = pd.to_datetime(df["log_date"]).dt.strftime("%Y-%m-%d")
    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    # Apply date range and subject slicers
    if start_date and end_date:
        df = df[(df["log_date"] >= start_date) & (df["log_date"] <= end_date)]
    if subject != "All":
        df = df[df["selected_subject"] == subject]

    if df.empty:
        return {}

    # Compute high-level KPI cards summary
    total_q = len(df)
    unique_users = int(df["hashed_client_ip"].nunique())
    unique_sessions = int(df["session_sk"].nunique())
    avg_lat = float(df["latency_seconds"].mean())
    avg_sim = float(df["top_similarity_score"].mean())
    empty_count = int(df["no_chunks_retrieved"].sum())
    empty_pct = float((empty_count / total_q * 100) if total_q > 0 else 0)

    # Compute daily trend aggregations
    daily = (
        df.groupby("log_date")
        .agg(
            total_queries=("query_sk", "count"),
            success_queries=("no_chunks_retrieved", lambda x: int((~x).sum())),
            unique_users=("hashed_client_ip", "nunique"),
            unique_sessions=("session_sk", "nunique"),
            avg_latency=("latency_seconds", "mean"),
            max_latency=("latency_seconds", "max"),
            min_latency=("latency_seconds", "min"),
        )
        .reset_index()
    )

    # Compute subject distribution metrics
    subj_summary = (
        df.groupby("selected_subject")
        .agg(
            total_queries=("query_sk", "count"),
            avg_top_similarity=("top_similarity_score", "mean"),
            avg_threshold=("similarity_threshold", "mean"),
            empty_retrievals=("no_chunks_retrieved", "sum"),
        )
        .reset_index()
    )

    # Select columns for Marts Data Table: retain query_sk and omit other surrogate keys
    marts_table_cols = [
        "query_sk",
        "created_at",
        "selected_subject",
        "selected_lesson",
        "similarity_threshold",
        "chunks_retrieved",
        "top_similarity_score",
        "latency_seconds",
        "user_query_length",
        "ai_response_length",
        "similarity_score_diff",
        "no_chunks_retrieved",
        "high_latency",
    ]

    return {
        "kpi": {
            "total_queries": total_q,
            "unique_users": unique_users,
            "unique_sessions": unique_sessions,
            "avg_latency": round(avg_lat, 2),
            "avg_similarity": round(avg_sim, 3),
            "empty_rate": round(empty_pct, 1),
            "empty_count": empty_count,
        },
        "daily_trends": daily.to_dict(orient="records"),
        "subject_distribution": subj_summary.to_dict(orient="records"),
        "scatter_data": df[
            [
                "top_similarity_score",
                "latency_seconds",
                "selected_subject",
                "chunks_retrieved",
            ]
        ]
        .head(300)
        .to_dict(orient="records"),
        "marts_table_data": df[marts_table_cols].head(150).to_dict(orient="records"),
    }