# tests/test_integration.py
import pytest
import asyncio
from sqlalchemy import text
from app.db.session import SessionLocal
from app.services import ingestion_service, rag_service
from app.core.config import settings

# 标记为异步测试
@pytest.mark.asyncio
async def test_mysql_connection():
    """测试 MySQL 数据库连接"""
    try:
        db = SessionLocal()
        # 执行一个简单的 SQL 查询
        result = db.execute(text("SELECT 1"))
        assert result.scalar() == 1
        print("\n✅ MySQL 连接成功")
    finally:
        db.close()

def test_minio_connection():
    """测试 Minio 连接"""
    client = ingestion_service.init_minio_client()
    # 列出所有桶，如果不报错说明连接成功
    client.list_buckets()
    print("\n✅ Minio 连接成功")

def test_milvus_connection():
    """测试 Milvus 连接"""
    # 尝试获取 Embeddings 模型（如果还没加载）
    embeddings = rag_service.get_embeddings()
    assert embeddings is not None
    print("\n✅ Embedding 模型加载成功")
    
    # 尝试连接 Milvus 并获取检索器
    try:
        retriever = rag_service.get_retriever()
        assert retriever is not None
        print("\n✅ Milvus 连接成功")
    except Exception as e:
        pytest.fail(f"Milvus 连接失败: {e}")

@pytest.mark.asyncio
async def test_rag_flow():
    """
    测试核心 RAG 流程 (检索 + 生成)
    注意：这需要 Docker 服务全部正常运行，且 Milvus 里有数据
    """
    test_question = "计算机" # 使用一个大概率能命中的词
    
    print(f"\n🧪 正在测试 RAG 检索，问题: {test_question}")
    
    # 1. 测试检索
    retriever = rag_service.get_retriever()
    docs = retriever.invoke(test_question)
    
    if not docs:
        print("⚠️ 警告: Milvus 中没有检索到文档。可能是尚未摄取数据。跳过后续生成测试。")
        return

    assert len(docs) > 0
    print(f"✅ 检索成功，找到 {len(docs)} 条相关文档")

    # 2. 测试生成 (简单验证 LLM 是否响应)
    # 我们只取流式响应的第一个 chunk 就行，证明连通了即可
    found_response = False
    try:
        async for chunk in rag_service.stream_rag_answer(
            question=test_question,
            llm_api_key=settings.DEEPSEEK_API_KEY,
            llm_base_url=settings.LLM_BASE_URL,
            llm_model=settings.LLM_MODEL_NAME
        ):
            if chunk:
                found_response = True
                break # 只要收到第一个字，就说明通了
    except Exception as e:
        pytest.fail(f"LLM 调用失败: {e}")

    assert found_response is True
    print("✅ LLM 响应成功")