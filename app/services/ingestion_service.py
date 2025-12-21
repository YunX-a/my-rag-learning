# app/services/ingestion_service.py
import os
from typing import List
from minio import Minio
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_milvus import Milvus
from langchain_core.embeddings import Embeddings 
from app.core.config import settings
from app.core.model_loader import get_embedding_model 

# --- 1. 定义同样的适配器类 (保持与 rag_service.py 一致) ---
class GlobalLazyEmbeddings(Embeddings):
    def __init__(self):
        # 从全局加载器获取模型
        model = get_embedding_model()
        if model is None:
            raise ValueError("Fatal Error: Embedding model failed to initialize. Please check docker logs.")
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # 开启 normalize_embeddings 以优化余弦相似度
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

# --- Minio 初始化 ---
def init_minio_client():
    """初始化 Minio 客户端"""
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE
    )

def upload_to_minio(file_path: str, object_name: str) -> str:
    """
    将文件上传到 Minio，并返回下载链接（或桶内路径）
    """
    client = init_minio_client()
    bucket_name = settings.MINIO_BUCKET_NAME

    # 1. 检查桶是否存在，不存在则创建
    if not client.bucket_exists(bucket_name):
        print(f"Bucket '{bucket_name}' 不存在，正在创建...")
        client.make_bucket(bucket_name)
    
    # 2. 上传文件
    print(f"正在上传文件 {object_name} 到 Minio...")
    client.fput_object(bucket_name, object_name, file_path)
    print(f"上传成功！")
    
    return f"{bucket_name}/{object_name}"

def process_and_embed_document(file_path: str, collection_name: str = settings.COLLECTION_NAME):
    """
    全流程处理：上传 Minio -> 解析 PDF -> 切分 -> 向量化 -> 存入 Milvus
    """
    file_name = os.path.basename(file_path)
    
    # --- 步骤 1: 上传原始文件到 Minio ---
    try:
        minio_path = upload_to_minio(file_path, file_name)
    except Exception as e:
        print(f"Minio 上传失败: {e}")
        return 0

    # --- 步骤 2: 加载与切分文档 ---
    print(f"正在解析 PDF: {file_path}")
    loader = PyMuPDFLoader(file_path)
    documents = loader.load()
    
    #  优化切分参数：增加重叠量，防止关键句子被切断
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    splits = text_splitter.split_documents(documents)
    
    if not splits:
        print("未提取到文本，跳过。")
        return 0

    # --- 步骤 3: 注入元数据 (Metadata) ---
    for doc in splits:
        doc.metadata["source"] = file_name
        doc.metadata["minio_path"] = minio_path

    # --- 步骤 4: 向量化并存入 Milvus ---
    print(f"正在将 {len(splits)} 个文本块存入 Milvus ({settings.MILVUS_HOST})...")
    
    #  删除原来的: embeddings = HuggingFaceEmbeddings(...)
    #  改为统一的:
    embeddings = GlobalLazyEmbeddings()
    
    # 连接 Milvus
    vector_store = Milvus(
        embedding_function=embeddings,
        collection_name=collection_name,
        connection_args={
            "host": settings.MILVUS_HOST,
            "port": str(settings.MILVUS_PORT), # 确保端口是字符串
            "alias": "default" # 显式指定 alias 比较安全
        },
        auto_id=True,
        #  关键：确保索引参数一致
        index_params={"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 1024}}
    )
    
    # 写入数据
    vector_store.add_documents(splits)
    print("写入 Milvus 完成！")
    
    return len(splits)