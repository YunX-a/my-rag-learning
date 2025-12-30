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
from langchain_core.documents import Document

from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.user import User
from app.models.chat import Conversation, Message
from app.services.cache_service import get_cache, set_cache
# 引入 ES 服务 (确保你已经创建了 app/services/es_service.py)
from app.services.es_service import search_keyword

# --- 1. 定义适配器类 ---
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

# --- 2. RRF 融合算法 (核心新增) ---
def reciprocal_rank_fusion(results: List[List[Any]], k=60):
    """
    RRF 融合算法：合并多路检索结果
    :param results: 多个列表，包含 Document 或 ES hit 对象
    """
    fused_scores = {}
    
    for doc_list in results:
        for rank, item in enumerate(doc_list):
            # 统一转换为内容字符串和元数据字符串作为唯一 Key
            if isinstance(item, Document):
                content = item.page_content
                # json dumps 保证字典顺序一致，作为唯一标识的一部分
                meta_str = json.dumps(item.metadata, sort_keys=True, ensure_ascii=False)
            else:
                # 兼容可能的其他格式
                content = str(item)
                meta_str = "{}"

            key = (content, meta_str)
            
            if key not in fused_scores:
                fused_scores[key] = 0
            
            # RRF 公式: score = 1 / (rank + k)
            fused_scores[key] += 1 / (rank + k)
            
    # 按分数倒序排列
    reranked = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    
    # 还原为 Document 对象
    final_docs = []
    for (content, meta_str), score in reranked:
        try:
            meta = json.loads(meta_str)
        except:
            meta = {}
        # 可以在 metadata 里把 score 加上，方便调试
        meta["rrf_score"] = score
        final_docs.append(Document(page_content=content, metadata=meta))
    
    return final_docs

# --- 3. 数据库辅助函数 ---
async def _save_chat_to_db(
    db: Session, 
    user_id: int, 
    question: str, 
    answer: str, 
    sources: Optional[List[Any]] = None
):
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

# --- 4. 核心 RAG 逻辑 (混合检索版) ---
async def stream_rag_answer(
    question: str,
    llm_api_key: SecretStr,
    llm_base_url: str,
    llm_model: str,
    db: Session,       
    user: User,
    collection_name: str = settings.COLLECTION_NAME
) -> AsyncGenerator[str, None]:
    
    print(f"--- Hybrid RAG Start: {question} ---")
    
    # === 1. 检查 Redis 缓存 ===
    cached_data = await get_cache(question)
    if cached_data:
        yield cached_data["answer"]
        yield "\n\n---SOURCES---\n"
        cached_sources = cached_data.get("sources")
        if cached_sources:
            for sz in cached_sources:
                 yield json.dumps(sz, ensure_ascii=False) + "\n"
        await _save_chat_to_db(db, user.id, question, cached_data["answer"], sources=cached_sources)
        return

    # === 2. 混合检索 (Hybrid Search) ===
    try:
        # A. 向量检索 (Milvus)
        print("🔍 执行 Milvus 向量检索...")
        retriever = get_retriever(collection_name=collection_name, k=5)
        milvus_docs = retriever.invoke(question)
        
        # B. 关键词检索 (ES)
        print("🔍 执行 ES 关键词检索...")
        es_hits = search_keyword(question, k=5)
        es_docs = []
        for hit in es_hits:
            source = hit["_source"]
            # 统一转为 Document
            es_docs.append(Document(
                page_content=source.get("content", ""),
                metadata={k: v for k, v in source.items() if k != "content"}
            ))

        # C. RRF 融合
        print(f"⚗️ 执行 RRF 融合 (向量: {len(milvus_docs)}, 关键词: {len(es_docs)})...")
        final_docs = reciprocal_rank_fusion([milvus_docs, es_docs])
        
        # 取前 6 个
        used_docs = final_docs[:6]
        
        if used_docs:
            context_text = "\n\n------\n\n".join([d.page_content for d in used_docs])
        else:
            context_text = "没有找到相关文档，请依据你的通用知识回答。"

    except Exception as e:
        print(f"检索过程出错: {e}")
        used_docs = []
        context_text = ""
    
    # [关键修复]：在这里根据 used_docs 定义 doc_metadatas，供后续使用
    doc_metadatas = [doc.metadata for doc in used_docs]

    # === 3. 构建 Prompt ===
    system_prompt = f"""你是一个专业的知识库助手。
请结合下方的【参考资料】来回答用户的【问题】。
如果参考资料中有多个观点，请综合回答。

【参考资料】:
{context_text}

要求：
1. 引用资料中的事实来支持你的观点。
2. 如果资料不足，请诚实说明。
"""

    # === 4. 生成 (Generation) ===
    llm = ChatOpenAI(
        api_key=llm_api_key,
        base_url=llm_base_url,
        model=llm_model,
        temperature=0.3,
        streaming=True
    )

    full_answer = ""
    
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question)
        ]
        
        async for chunk in llm.astream(messages):
            content = chunk.content
            if content:
                full_answer += str(content)
                yield str(content)
                
    except Exception as e:
        print(f"LLM 生成出错: {e}")
        yield f"\n[生成中断: {e}]"
    
    # === 5. 收尾 ===
    yield "\n\n---SOURCES---\n"
    # 这里 doc_metadatas 已经被正确定义了
    for meta in doc_metadatas:
        yield json.dumps(meta, ensure_ascii=False) + "\n"

    if full_answer:
        asyncio.create_task(set_cache(question, full_answer, doc_metadatas))
        await _save_chat_to_db(db, user.id, question, full_answer, sources=doc_metadatas)

    print("--- RAG End ---")