import json
import hashlib
import redis.asyncio as redis # type: ignore
from typing import Optional, Dict, Any
from app.core.config import settings

# 创建 Redis 连接池
pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)

def get_redis_client():
    return redis.Redis(connection_pool=pool)

def generate_cache_key(question: str) -> str:
    """
    将问题进行 MD5 哈希，生成唯一的 Key
    """
    # 比如 "rag_cache:md5_of_question"
    hash_str = hashlib.md5(question.encode("utf-8")).hexdigest()
    return f"rag_cache:{hash_str}"

async def get_cache(question: str) -> Optional[Dict[str, Any]]:
    """
    尝试获取缓存
    """
    client = get_redis_client()
    key = generate_cache_key(question)
    data = await client.get(key)
    if data:
        print(f" 命中 Redis 缓存: {key}")
        return json.loads(data)
    return None

async def set_cache(question: str, answer: str, sources: list):
    """
    写入缓存
    """
    client = get_redis_client()
    key = generate_cache_key(question)
    
    data = {
        "answer": answer,
        "sources": sources
    }

    # 写入并设置过期时间
    await client.setex(key, settings.CACHE_TTL, json.dumps(data, ensure_ascii=False))
    print(f"已写入 Redis 缓存: {key}")