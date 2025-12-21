# app/schemas/rag.py
from pydantic import BaseModel

class ChatRequest(BaseModel):
    question: str