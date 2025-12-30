# app/services/es_service.py
from elasticsearch import Elasticsearch
from app.core.config import settings

# 初始化客户端
es_client = Elasticsearch(settings.ES_URL)

def create_index_if_not_exists():
    """创建索引"""
    try:
        if not es_client.indices.exists(index=settings.ES_INDEX):
            print(f"正在创建 ES 索引: {settings.ES_INDEX} ...")
            es_client.indices.create(
                index=settings.ES_INDEX,
                mappings={
                    "properties": {
                        "content": {"type": "text", "analyzer": "standard"},
                        "source": {"type": "keyword"},
                        "page": {"type": "integer"}
                    }
                }
            )
            print(f"ES 索引 '{settings.ES_INDEX}' 创建成功")
    except Exception as e:
        print(f"创建索引失败: {e}")

def index_document(doc_id: str, content: str, metadata: dict):
    """写入文档 (带数据清洗)"""
    
    # CAN: 关键修复 - 清洗 metadata，移除空值
    # ES 的动态映射非常敏感，如果它认为某个字段是 Date，传空字符串就会报错
    clean_metadata = {}
    for k, v in metadata.items():
        # 剔除空字符串、None，以及可能导致问题的复杂对象
        if v == "" or v is None:
            continue
        # 确保值是基本类型
        if isinstance(v, (str, int, float, bool)):
            clean_metadata[k] = v
        else:
            # 其他类型转字符串，求稳
            clean_metadata[k] = str(v)

    doc_data = {
        "content": content,
        **clean_metadata
    }
    
    try:
        es_client.index(
            index=settings.ES_INDEX, 
            id=doc_id, 
            document=doc_data
        )
    except Exception as e:
        print(f"写入 ES 失败 (ID: {doc_id}): {e}")

def search_keyword(query: str, k: int = 5):
    """关键词检索"""
    try:
        response = es_client.search(
            index=settings.ES_INDEX,
            query={
                "match": {
                    "content": query
                }
            },
            size=k
        )
        return response["hits"]["hits"]
    except Exception as e:
        print(f"ES 检索失败: {e}")
        return []