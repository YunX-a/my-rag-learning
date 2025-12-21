# scripts/reset_db.py
from pymilvus import MilvusClient
from app.core.config import settings

def reset_milvus():
    # 拼接 URI 地址 (例如 http://localhost:19530)
    uri = f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}"
    
    print(f"🔌 正在连接 Milvus ({uri})...")
    
    # 使用新版 MilvusClient，它自动处理连接，不需要手动 connections.connect
    client = MilvusClient(uri=uri)
    
    collection_name = settings.COLLECTION_NAME
    
    # 检查并删除集合
    if client.has_collection(collection_name):
        print(f"发现集合 '{collection_name}'，正在删除...")
        client.drop_collection(collection_name)
        print("集合已删除！数据已清空。")
    else:
        print(f"集合 '{collection_name}' 不存在，无需清理。")

if __name__ == "__main__":
    try:
        reset_milvus()
    except Exception as e:
        print(f"操作失败: {e}")