# scripts/reset_db.py
import sys
import os

# 将项目根目录加入 Python 路径，防止找不到 app 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymilvus import MilvusClient
from app.core.config import settings

def reset_milvus():
    # 拼接 URI 地址 (例如 http://milvus-standalone:19530)
    uri = f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}"
    
    print(f"🔌 正在连接 Milvus ({uri})...")
    
    try:
        # 使用新版 MilvusClient，它自动处理连接
        client = MilvusClient(uri=uri)
        
        collection_name = settings.COLLECTION_NAME
        
        # 检查并删除集合
        if client.has_collection(collection_name):
            print(f"发现集合 '{collection_name}'，正在删除...")
            client.drop_collection(collection_name)
            print("✅ 集合已删除！数据已清空。")
        else:
            print(f"集合 '{collection_name}' 不存在，无需清理。")
            
    except Exception as e:
        print(f"❌ 连接或操作失败: {e}")
        # 如果是 host 解析失败，提示用户
        if "Name or service not known" in str(e):
            print("提示: 如果你在容器外运行此脚本，请设置环境变量 MILVUS_HOST=localhost")

if __name__ == "__main__":
    reset_milvus()