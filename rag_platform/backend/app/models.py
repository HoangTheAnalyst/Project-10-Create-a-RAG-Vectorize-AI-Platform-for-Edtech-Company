from typing import Dict, List
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Payload schema for multi-turn chat interactions and context retrieval."""

    session_id: str
    conv_id: str
    conv_name: str
    query: str
    subject: str = "All"
    lesson: str = "All"
    threshold: float = 0.55
    history: List[Dict[str, str]] = []


class ExamRequest(BaseModel):
    """Payload schema for generating structured quiz questions."""

    subject: str
    lesson: str
    limit: int = 5