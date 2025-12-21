# app/services/rag_service.py
import json
import asyncio
from typing import AsyncGenerator
from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_milvus import Milvus
from langchain_core.vectorstores import VectorStoreRetriever
from langchain.callbacks.streaming_aiter import AsyncIteratorCallbackHandler
from langchain_core.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.user import User
from app.models.chat import Conversation, Message
from app.services.cache_service import get_cache, set_cache

# 全局缓存 Embeddings 模型
_EMBEDDINGS = None

def get_embeddings():
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        print(f"正在加载 Embedding 模型: {settings.EMBEDDING_MODEL_NAME} ...")
        _EMBEDDINGS = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)
    return _EMBEDDINGS

def get_retriever(collection_name: str = settings.COLLECTION_NAME, k: int = 5) -> VectorStoreRetriever:
    """连接 Milvus 并返回检索器"""
    print(f"DEBUG !!!!!!!!: 真实代码正在连接 -> {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
    embeddings = get_embeddings()
    vector_store = Milvus(
        embedding_function=embeddings,
        collection_name=collection_name,
        connection_args={
            "host": settings.MILVUS_HOST,
            "port": settings.MILVUS_PORT
        },
        auto_id=True
    )
    return vector_store.as_retriever(search_kwargs={"k": k})

async def _save_chat_to_db(db: Session, user_id: int, question: str, answer: str):
    """
    (内部辅助函数) 将问答记录保存到 MySQL
    """
    try:
        # 1. 创建新会话
        new_conversation = Conversation(
            user_id=user_id,
            title=question[:30] # 截取前30字作为标题
        )
        db.add(new_conversation)
        db.commit()
        db.refresh(new_conversation)

        # 2. 保存用户提问
        user_msg = Message(
            conversation_id=new_conversation.id,
            role="user",
            content=question
        )
        db.add(user_msg)

        # 3. 保存 AI 回答
        ai_msg = Message(
            conversation_id=new_conversation.id,
            role="assistant",
            content=answer
        )
        db.add(ai_msg)
        
        db.commit()
        print(f"--- DEBUG: 会话保存成功 (ID: {new_conversation.id}) ---")
    except Exception as e:
        print(f" 保存数据库失败: {e}")
        db.rollback()

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
    RAG 核心逻辑：缓存 -> 检索 Milvus -> 构造 Prompt -> 流式调用 LLM -> 持久化
    """
    print(f"--- DEBUG: 进入 RAG 流程，问题: {question} ---")
    
    # === 1. 检查 Redis 缓存 ===
    cached_data = await get_cache(question)
    
    if cached_data:
        # --- 命中缓存分支 ---
        answer = cached_data["answer"]
        yield answer
        
        # 输出引用来源
        yield "\n\n---SOURCES---\n"
        for src in cached_data["sources"]:
             yield json.dumps(src, ensure_ascii=False) + "\n"
        
        # 关键修复：即使命中缓存，也要保存到 MySQL 历史记录
        await _save_chat_to_db(db, user.id, question, answer)
        return

    # === 2. 缓存未命中，开始 RAG ===
    
    # 获取检索器
    try:
        retriever = get_retriever(collection_name=collection_name)
        # 修复：之前这里调用了两次 invoke，删掉了一次
        print("--- DEBUG: 开始检索... ---")
        docs = retriever.invoke(question)
        print(f"--- DEBUG: 检索到 {len(docs)} 篇文档 ---")
    except Exception as e:
        yield f"检索服务暂时不可用: {e}"
        return

    if not docs:
        yield "在知识库中未找到相关内容，无法回答您的问题。"
        return

    # 初始化 LLM
    callback = AsyncIteratorCallbackHandler()
    llm = ChatOpenAI(
        api_key=llm_api_key,
        base_url=llm_base_url,
        model=llm_model,
        temperature=0.3,
        streaming=True,
        callbacks=[callback]
    ) # type: ignore

    # 构造 Chain
    template = """
    你是一个智能、热情的知识库助手。请结合下面的[参考资料]和你的通用知识来回答用户的[问题]。
    
    [参考资料]:
    {context}

    [问题]:
    {input}

    回答:
    """
    prompt = PromptTemplate.from_template(template)
    qa_chain = create_stuff_documents_chain(llm, prompt)
    
    # 启动生成任务
    task = asyncio.create_task(
        qa_chain.ainvoke({"input": question, "context": docs})
    )
    
    full_answer = ""
    doc_metadatas = [doc.metadata for doc in docs]

    try:
        async for token in callback.aiter():
            full_answer += token
            yield token
    except Exception as e:
        print(f"LLM 生成出错: {e}")
        yield f"\n[生成中断: {e}]"
    finally:
        await task 
        
        # 输出引用来源
        yield "\n\n---SOURCES---\n"
        for meta in doc_metadatas:
            yield json.dumps(meta, ensure_ascii=False) + "\n"

        # === 3. 收尾工作：写入缓存 & 写入数据库 ===
        if full_answer:
            # 写入 Redis (异步后台执行，不阻塞)
            asyncio.create_task(set_cache(question, full_answer, doc_metadatas))
            
            # 写入 MySQL (确保记录历史)
            await _save_chat_to_db(db, user.id, question, full_answer)

    print("--- DEBUG: RAG 流程结束 ---")