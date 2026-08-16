import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from utils.snowflake_conn import get_snowflake_conn

conn = get_snowflake_conn()

st.title("📈 Detailed Performance & Observability Dashboard")

# --- 1. DATA RETRIEVAL (CACHE 1H) ---
@st.cache_data(ttl=3600)
def load_rag_logs():
  cur = conn.cursor()
  try:
    sql = """
            SELECT 
                query_sk,
                hashed_client_ip,
                session_sk,
                conversation_sk,
                lesson_sk,
                selected_subject,
                selected_lesson,
                similarity_threshold,
                chunks_retrieved,
                top_similarity_score,
                latency_seconds,
                user_query_length,
                ai_response_length,
                similarity_score_diff,
                no_chunks_retrieved,
                high_latency,
                created_at,
                DATE_TRUNC('day', created_at) AS log_date
            FROM MARTS_LOG.FCT_LOG
            ORDER BY created_at DESC;
        """
    cur.execute(sql)
    cols = [col[0].lower() for col in cur.description]
    df = pd.DataFrame(cur.fetchall(), columns=cols)
    if not df.empty:
      df["created_at"] = pd.to_datetime(df["created_at"])
      df["log_date"] = pd.to_datetime(df["log_date"]).dt.date
    return df
  except Exception as e:
    st.error(f"Database Query Error: {e}")
    return pd.DataFrame()
  finally:
    cur.close()


df = load_rag_logs()

if df.empty:
  st.info("💡 No log records found in `MARTS_LOG.FCT_LOG`.")
  st.stop()

# --- 2. SIDEBAR FILTERS ---
with st.sidebar:
  st.header("🔍 Filter Analytics")
  min_d, max_d = df["log_date"].min(), df["log_date"].max()
  date_range = st.date_input(
      "Date Range:",
      value=(min_d, max_d),
      min_value=min_d,
      max_value=max_d,
  )

  subject_list = ["All"] + sorted(
      df["selected_subject"].dropna().unique().tolist()
  )
  selected_subj = st.selectbox("Subject:", subject_list)

  if st.button("🔄 Refresh Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# Apply filters
filtered_df = df.copy()
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
  filtered_df = filtered_df[
      (filtered_df["log_date"] >= date_range[0])
      & (filtered_df["log_date"] <= date_range[1])
  ]
if selected_subj != "All":
  filtered_df = filtered_df[filtered_df["selected_subject"] == selected_subj]

if filtered_df.empty:
  st.warning("No records match the current filter selection.")
  st.stop()

# --- 3. SUMMARY KPI METRICS ---
total_q = len(filtered_df)
unique_users = filtered_df["hashed_client_ip"].nunique()
unique_sessions = filtered_df["session_sk"].nunique()

avg_lat = filtered_df["latency_seconds"].mean() if total_q > 0 else 0
avg_sim = filtered_df["top_similarity_score"].mean() if total_q > 0 else 0
empty_count = filtered_df["no_chunks_retrieved"].sum()
empty_pct = (empty_count / total_q * 100) if total_q > 0 else 0

st.markdown("### 📊 Activity & Performance Overview")
c1, c2, c3 = st.columns(3)
c1.metric("Total Queries", f"{total_q:,}")
c2.metric("Active Users (Hashed IP)", f"{unique_users:,}")
c3.metric("Active Sessions", f"{unique_sessions:,}")

c4, c5, c6 = st.columns(3)
c4.metric("Avg Latency", f"{avg_lat:.2f}s")
c5.metric("Avg Top Similarity", f"{avg_sim:.3f}")
c6.metric(
    "Empty Retrieval Rate",
    f"{empty_pct:.1f}%",
    delta=f"{empty_count} errors",
    delta_color="inverse",
)

st.markdown("---")

# --- 4. DATA AGGREGATION ---
daily_summary = (
    filtered_df.groupby("log_date")
    .agg(
        total_queries=("query_sk", "count"),
        success_queries=("no_chunks_retrieved", lambda x: (~x).sum()),
        unique_users=("hashed_client_ip", "nunique"),
        unique_sessions=("session_sk", "nunique"),
        avg_latency=("latency_seconds", "mean"),
        max_latency=("latency_seconds", "max"),
        min_latency=("latency_seconds", "min"),
    )
    .reset_index()
)

subject_summary = (
    filtered_df.groupby("selected_subject")
    .agg(
        total_queries=("query_sk", "count"),
        avg_top_similarity=("top_similarity_score", "mean"),
        avg_threshold=("similarity_threshold", "mean"),
        empty_retrievals=("no_chunks_retrieved", "sum"),
    )
    .reset_index()
)

clean_legend_layout = dict(
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.22,
        xanchor="center",
        x=0.5,
    ),
    margin=dict(l=30, r=20, t=50, b=65),
    hovermode="x unified",
)

# ==============================================================================
# ROW 1: CHART 1 & CHART 2
# ==============================================================================
r1_col1, r1_col2 = st.columns(2)

with r1_col1:
  # CHART 1: Daily Active Users
  fig1 = go.Figure()
  fig1.add_trace(
      go.Scatter(
          x=daily_summary["log_date"],
          y=daily_summary["unique_users"],
          mode="lines+markers",
          name="Daily Active Users",
          line=dict(color="#06B6D4", width=2.5),
          marker=dict(size=6),
      )
  )
  fig1.update_layout(
      title="1. Daily Active Users (Hashed IP)",
      xaxis_title="Date",
      yaxis_title="Unique Users",
      **clean_legend_layout,
  )
  st.plotly_chart(fig1, use_container_width=True)

with r1_col2:
  # CHART 2: Daily Active Sessions
  fig2 = go.Figure()
  fig2.add_trace(
      go.Scatter(
          x=daily_summary["log_date"],
          y=daily_summary["unique_sessions"],
          mode="lines+markers",
          name="Daily Active Sessions",
          line=dict(color="#8B5CF6", width=2.5),
          marker=dict(size=6),
      )
  )
  fig2.update_layout(
      title="2. Daily Active Sessions",
      xaxis_title="Date",
      yaxis_title="Unique Sessions",
      **clean_legend_layout,
  )
  st.plotly_chart(fig2, use_container_width=True)

# ==============================================================================
# ROW 2: CHART 3 & CHART 4
# ==============================================================================
r2_col1, r2_col2 = st.columns(2)

with r2_col1:
  # CHART 3: Query Volume vs Success Trend
  fig3 = go.Figure()
  fig3.add_trace(
      go.Scatter(
          x=daily_summary["log_date"],
          y=daily_summary["total_queries"],
          mode="lines+markers",
          name="Total Queries",
          line=dict(color="#3B82F6", width=2.5),
      )
  )
  fig3.add_trace(
      go.Scatter(
          x=daily_summary["log_date"],
          y=daily_summary["success_queries"],
          mode="lines+markers",
          name="Successful Retrievals",
          line=dict(color="#10B981", width=2.5, dash="dash"),
      )
  )
  fig3.update_layout(
      title="3. Query Volume vs Success Trend",
      xaxis_title="Date",
      yaxis_title="Interactions Count",
      **clean_legend_layout,
  )
  st.plotly_chart(fig3, use_container_width=True)

with r2_col2:
  # CHART 4: Query Distribution by Subject
  fig4 = px.bar(
      subject_summary.sort_values(by="total_queries", ascending=False),
      x="selected_subject",
      y="total_queries",
      text_auto=True,
      title="4. Query Distribution by Subject",
      labels={"selected_subject": "Subject", "total_queries": "Total Queries"},
      color="selected_subject",
      color_discrete_sequence=px.colors.qualitative.Safe,
  )
  fig4.update_layout(
      showlegend=False,
      margin=dict(l=30, r=20, t=50, b=40),
      xaxis_title="Subject",
      yaxis_title="Queries",
  )
  st.plotly_chart(fig4, use_container_width=True)

# ==============================================================================
# ROW 3: CHART 5 & CHART 6
# ==============================================================================
r3_col1, r3_col2 = st.columns(2)

with r3_col1:
  # CHART 5: Top Similarity vs Filter Threshold
  fig5 = go.Figure()
  fig5.add_trace(
      go.Bar(
          x=subject_summary["selected_subject"],
          y=subject_summary["avg_top_similarity"],
          name="Avg Top Similarity",
          marker_color="#6366F1",
      )
  )
  fig5.add_trace(
      go.Bar(
          x=subject_summary["selected_subject"],
          y=subject_summary["avg_threshold"],
          name="Avg Threshold",
          marker_color="#94A3B8",
      )
  )
  fig5.update_layout(
      title="5. Top Similarity vs Filter Threshold",
      barmode="group",
      xaxis_title="Subject",
      yaxis_title="Score (0.0 - 1.0)",
      **clean_legend_layout,
  )
  st.plotly_chart(fig5, use_container_width=True)

with r3_col2:
  # CHART 6: Correlation: Similarity Score vs Latency
  fig6 = px.scatter(
      filtered_df,
      x="top_similarity_score",
      y="latency_seconds",
      color="selected_subject",
      size="chunks_retrieved",
      hover_data=["selected_lesson", "similarity_score_diff"],
      title="6. Correlation: Similarity Score vs Latency",
      labels={
          "top_similarity_score": "Top Similarity Score",
          "latency_seconds": "Latency (s)",
          "selected_subject": "Subject",
          "chunks_retrieved": "Chunks",
      },
  )
  fig6.update_layout(
      margin=dict(l=30, r=20, t=50, b=40),
      xaxis_title="Top Similarity Score",
      yaxis_title="Latency (s)",
  )
  st.plotly_chart(fig6, use_container_width=True)

# ==============================================================================
# ROW 4: CHART 7 & CHART 8
# ==============================================================================
r4_col1, r4_col2 = st.columns(2)

with r4_col1:
  # CHART 7: Empty Retrievals Count by Subject
  fig7 = px.bar(
      subject_summary.sort_values(by="empty_retrievals", ascending=False),
      x="selected_subject",
      y="empty_retrievals",
      text_auto=True,
      title="7. Empty Retrievals Count by Subject",
      labels={
          "selected_subject": "Subject",
          "empty_retrievals": "No Chunks Found",
      },
      color_discrete_sequence=["#EF4444"],
  )
  fig7.update_layout(
      margin=dict(l=30, r=20, t=50, b=40),
      xaxis_title="Subject",
      yaxis_title="Zero Chunk Count",
  )
  st.plotly_chart(fig7, use_container_width=True)

with r4_col2:
  # CHART 8: Latency Bounds Over Time
  fig8 = go.Figure()
  fig8.add_trace(
      go.Scatter(
          x=daily_summary["log_date"],
          y=daily_summary["max_latency"],
          mode="lines+markers",
          name="Max Latency",
          line=dict(color="#DC2626", width=2),
      )
  )
  fig8.add_trace(
      go.Scatter(
          x=daily_summary["log_date"],
          y=daily_summary["avg_latency"],
          mode="lines+markers",
          name="Avg Latency",
          line=dict(color="#F59E0B", width=2.5),
      )
  )
  fig8.add_trace(
      go.Scatter(
          x=daily_summary["log_date"],
          y=daily_summary["min_latency"],
          mode="lines+markers",
          name="Min Latency",
          line=dict(color="#10B981", width=2),
      )
  )
  fig8.update_layout(
      title="8. Latency Bounds Over Time (s)",
      xaxis_title="Date",
      yaxis_title="Latency (seconds)",
      **clean_legend_layout,
  )
  st.plotly_chart(fig8, use_container_width=True)

# ==============================================================================
# ROW 5: TABLE 9
# ==============================================================================
st.markdown("---")
st.subheader("9. 📋 Audit Log Records")

display_cols = [
    "created_at",
    "query_sk",
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

renamed_cols = {
    "created_at": "Timestamp",
    "query_sk": "Query SK",
    "selected_subject": "Subject",
    "selected_lesson": "Lesson",
    "similarity_threshold": "Threshold",
    "chunks_retrieved": "Chunks",
    "top_similarity_score": "Top Score",
    "latency_seconds": "Latency (s)",
    "user_query_length": "Query Len",
    "ai_response_length": "Resp Len",
    "similarity_score_diff": "Score Diff",
    "no_chunks_retrieved": "Empty Data",
    "high_latency": "SLA Breach (>5s)",
}

st.dataframe(
    filtered_df[display_cols].rename(columns=renamed_cols),
    use_container_width=True,
    hide_index=True,
)