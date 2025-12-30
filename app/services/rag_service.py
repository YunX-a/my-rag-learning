# app/services/rag_service.py
import json
import asyncio
from typing import AsyncGenerator, List, Optional, Any
from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from pymilvus import connections
from langchain_core.embeddings import Embeddings 
from app.core.model_loader import get_embedding_model 

from langchain_milvus import Milvus
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.user import User
from app.models.chat import Conversation, Message
from app.services.cache_service import get_cache, set_cache

# --- 1. 定义适配器类 (每个需要用的文件里都需要定义，或提取到单独的 common 文件) ---
class GlobalLazyEmbeddings(Embeddings):
    def __init__(self):
        model = get_embedding_model()
        if model is None:
            raise ValueError("Fatal Error: Embedding model failed to initialize.")
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

# --- 2. 数据库辅助函数 ---
async def _save_chat_to_db(
    db: Session, 
    user_id: int, 
    question: str, 
    answer: str, 
    sources: Optional[List[Any]] = None
):
    """
    (内部辅助函数) 将问答记录保存到 MySQL
    """
    try:
        new_conversation = Conversation(user_id=user_id, title=question[:30])
        db.add(new_conversation)
        db.commit()
        db.refresh(new_conversation)

        user_msg = Message(
            conversation_id=new_conversation.id,
            role="user",
            content=question
        )
        db.add(user_msg)

        ai_msg = Message(
            conversation_id=new_conversation.id,
            role="assistant",
            content=answer,
            sources=sources 
        )
        db.add(ai_msg)
        
        db.commit()
    except Exception as e:
        print(f"保存数据库失败: {e}")
        db.rollback()

def get_retriever(collection_name: str = settings.COLLECTION_NAME, k: int = 5) -> VectorStoreRetriever:
    """连接 Milvus 并返回检索器"""
    try:
        if not connections.has_connection("default"):
            connections.connect(
                alias="default", 
                host=settings.MILVUS_HOST, 
                port=settings.MILVUS_PORT
            )
    except Exception as e:
        print(f"底层连接警告: {e}")

    embeddings = GlobalLazyEmbeddings()
    
    vector_store = Milvus(
        embedding_function=embeddings,
        collection_name=collection_name,
        connection_args={
            "host": settings.MILVUS_HOST,
            "port": str(settings.MILVUS_PORT), 
            "alias": "default" 
        },
        auto_id=True
    )
    return vector_store.as_retriever(search_kwargs={"k": k})

# --- 3. 核心 RAG 逻辑 ---
async def stream_rag_answer(
    question: str,
    llm_api_key: SecretStr,
    llm_base_url: str,
    llm_model: str,
    db: Session,       
    user: User,
    collection_name: str = settings.COLLECTION_NAME
) -> AsyncGenerator[str, None]:
    """
    RAG 核心逻辑 (修复版)
    """
    print(f"--- RAG Start: {question} ---")
    
    # === 1. 检查 Redis 缓存 ===
    cached_data = await get_cache(question)
    
    if cached_data:
        # --- 命中缓存 ---
        answer = cached_data["answer"]
        yield answer
        
        yield "\n\n---SOURCES---\n"
        # 修复之前的 forSz 拼写错误
        cached_sources = cached_data.get("sources")
        if cached_sources:
            for sz in cached_sources:
                 yield json.dumps(sz, ensure_ascii=False) + "\n"
        
        # 存入数据库
        await _save_chat_to_db(db, user.id, question, answer, sources=cached_sources)
        return

    # === 2. 检索 (Retrieval) ===
    try:
        retriever = get_retriever(collection_name=collection_name, k=4)
        docs = retriever.invoke(question)
        
        if docs:
            # 构建上下文
            context_text = "\n\n------\n\n".join([doc.page_content for doc in docs])
        else:
            context_text = "没有找到相关文档，请依据你的通用知识回答。"
            
    except Exception as e:
        print(f"检索出错: {e}")
        docs = []
        context_text = ""

    doc_metadatas = [doc.metadata for doc in docs]

    # === 3. 构建 Prompt ===
    system_prompt = f"""你是一个专业的助手。
                        请依据下方的【参考资料】来回答用户的【问题】。

                        【参考资料】:
                        {context_text}

                        要求：
                        1. 若参考资料包含答案，请详细回答。
                        2. 若无相关资料，请利用你的知识回答，并说明资料中未提及。
                    """

    # === 4. 生成 (Generation) ===
    # 实例化 LLM
    llm = ChatOpenAI(
        api_key=llm_api_key,
        base_url=llm_base_url,
        model=llm_model,
        temperature=0.3,
        streaming=True
    )

    full_answer = ""
    
    try:
        # 修复点：直接遍历 astream，不需要 create_task
        # astream 返回的是 BaseMessageChunk，我们需要转成字符串
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question)
        ]
        
        async for chunk in llm.astream(messages):
            content = chunk.content
            if content:
                full_answer += str(content) # 确保是字符串
                yield str(content)
                
    except Exception as e:
        print(f"LLM 生成出错: {e}")
        yield f"\n[生成中断: {e}]"
    
    # === 5. 收尾 ===
    # 输出引用来源
    yield "\n\n---SOURCES---\n"
    for meta in doc_metadatas:
        yield json.dumps(meta, ensure_ascii=False) + "\n"

    # 写入缓存 & 数据库
    if full_answer:
        asyncio.create_task(set_cache(question, full_answer, doc_metadatas))
        await _save_chat_to_db(db, user.id, question, full_answer, sources=doc_metadatas)

    print("--- RAG End ---")