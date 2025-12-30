from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas.rag import ChatRequest
from app.services.agent_service import stream_agent_chat

router = APIRouter()

@router.post("/chat")
async def agent_chat(request: ChatRequest):
    """
    Agent 对话接口
    """
    return StreamingResponse(
        stream_agent_chat(request.question),
        media_type="text/event-stream"
    )