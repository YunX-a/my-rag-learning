import json
import asyncio
from typing import AsyncGenerator, List
from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from pymilvus import connections
from langchain_core.embeddings import Embeddings 
from app.core.model_loader import get_embedding_model 

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


# 1. 定义一个适配器类
# 作用：把我们预加载的 SentenceTransformer "裸模型" 
# 包装成 LangChain 认识的 "Embeddings" 对象
class GlobalLazyEmbeddings(Embeddings):
    def __init__(self):
        model = get_embedding_model()
        
        if model is None:
            raise ValueError("Fatal Error: Embedding model failed to initialize. Please check docker logs.")
            
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # 调用 sentence-transformers 的 encode 方法
        # normalize_embeddings=True 建议开启，对余弦相似度更好
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        # 单条查询编码
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    

def get_retriever(collection_name: str = settings.COLLECTION_NAME, k: int = 5) -> VectorStoreRetriever:
    """连接 Milvus 并返回检索器"""
    print(f"正在尝试建立底层连接 -> {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
    
    # 强制 PyMilvus 建立名为 "default" 的连接，这样 LangChain 内部会直接复用它
    try:
        if not connections.has_connection("default"):
            connections.connect(
                alias="default", 
                host=settings.MILVUS_HOST, 
                port=settings.MILVUS_PORT
            )
            print(" 底层 PyMilvus 连接成功！")
    except Exception as e:
        print(f" 底层连接失败: {e}")

    embeddings = GlobalLazyEmbeddings()
    
    from pymilvus import Collection
    try:
        col = Collection(collection_name)
        col.load()
        print(f"集合 {collection_name} 已加载至内存")
    except Exception as e:
        print(f"加载集合失败: {e}")
        
    # 在初始化 Milvus 时，显式指定 connection_args
    vector_store = Milvus(
        embedding_function=embeddings,
        collection_name=collection_name,
        connection_args={
            "host": settings.MILVUS_HOST,
            "port": str(settings.MILVUS_PORT), # 确保端口是字符串
            "alias": "default" # 强制关联我们上面建立的连接
        },
        auto_id=True
    )
    return vector_store.as_retriever(search_kwargs={"k": k})

async def _save_chat_to_db(db: Session, user_id: int, question: str, answer: str, sources: List = None):
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

        # 3. 保存 AI 回答 (🌟 把 sources 存进去)
        ai_msg = Message(
            conversation_id=new_conversation.id,
            role="assistant",
            content=answer,
            sources=sources # <--- 关键点：这里必须把 sources 传给数据库模型
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
        await _save_chat_to_db(db, user.id, question, answer, sources=cached_data.get("sources"))
        return

    # === 2. 缓存未命中，开始 RAG ===
    
    # 获取检索器
    try:
        retriever = get_retriever(collection_name=collection_name)
        # 修复：之前这里调用了两次 invoke，删掉了一次
        print("--- DEBUG: 开始检索... ---")
        docs = retriever.invoke(question)
        print(f"--- DEBUG: 检索到 {len(docs)} 篇文档 ---")
        if not docs:
            print("--- DEBUG: 没搜到匹配，正在获取推荐参考... ---")
            # 方案：尝试检索最泛化的内容，或者直接从文件列表里拿前3个
            try:
                # 再次检索，但这次用一个极简的关键词或者空字符串，获取一些基础资料
                recommend_docs = retriever.invoke("基础知识") 
                docs = recommend_docs[:3] # 取前3个作为可能相关的资料
            except:
                docs = []
                
    except Exception as e:
        print(f"检索出错: {e}")
        docs = []

    # if not docs:
    #     yield "在知识库中未找到相关内容，无法回答您的问题。"
    #     return

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
    你是一个智能助手。请结合[参考资料]回答用户的[问题]。
    
    [规则]:
    1. 如果[参考资料]与问题高度相关，请详细回答并引用。
    2. 如果[参考资料]与问题相关度较低，请先回答用户的问题，并说明：“以下是可能与您问题相关的参考资料，供您参考。”
    3. 如果没有完全匹配的内容，请根据你的通用知识回答，并在结尾列出可能相关的文件。
    
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
            await _save_chat_to_db(db, user.id, question, full_answer, sources=doc_metadatas)

    print("--- DEBUG: RAG 流程结束 ---")