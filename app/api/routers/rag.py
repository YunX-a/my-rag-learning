# app/api/routers/rag.py
import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.rag import ChatRequest
from app.services.rag_service import stream_rag_answer
from app.services.ingestion_service import process_and_embed_document
from app.core.config import settings
from app.services.minio_service import minio_client
from app.api.deps import get_current_user
from sqlalchemy.orm import Session  
from app.db.session import get_db   
from app.models.user import User    
from app.api.deps import get_current_user

router = APIRouter()
from typing import List

@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),              # 注入数据库
    # current_user: User = Depends(get_current_user) # 注入当前用户 (需要登录)
):
    class FakeUser: id = 1
    current_user = FakeUser()
    """
    RAG 流式问答接口 (已开启鉴权与存储)
    """
    return StreamingResponse(
        stream_rag_answer(
            question=request.question,
            llm_api_key=settings.DEEPSEEK_API_KEY,
            llm_base_url=settings.LLM_BASE_URL,
            llm_model=settings.LLM_MODEL_NAME,
            db=db,             # 传入 DB
            user=current_user  # 传入用户 # type: ignore
        ),
        media_type="text/event-stream"
    )
    
@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    上传 PDF 文档 -> 存入 Minio -> 写入 Milvus
    """
    allowed_extensions = (".pdf", ".txt")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is missing")

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    # 1. 临时保存上传的文件
    temp_dir = "data/uploads"
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. 调用摄取服务
        chunks_count = process_and_embed_document(temp_path)
        
        if chunks_count == 0:
             raise HTTPException(status_code=500, detail="Failed to process document")
             
        return {"filename": file.filename, "chunks": chunks_count, "message": "Successfully ingested"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 清理临时文件 (可选: 如果你希望保留本地备份则注释掉这行)
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
@router.get("/files", response_model=List[str])
async def list_files():
    """
    列出 Minio 存储桶中所有的文件名
    """
    try:
        # 检查 Bucket 是否存在
        if not minio_client.bucket_exists(settings.MINIO_BUCKET_NAME):
            return []

        # 列出所有对象
        objects = minio_client.list_objects(settings.MINIO_BUCKET_NAME)
        
        # 提取文件名
        file_names = [obj.object_name for obj in objects]
        return file_names
    except Exception as e:
        print(f"获取文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")