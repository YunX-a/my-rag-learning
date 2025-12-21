# app/services/minio_service.py
from minio import Minio
from app.core.config import settings

def get_minio_client():
    """
    初始化并返回 Minio 客户端
    """
    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE
    )
    return client

# 创建一个单例客户端供全局使用
minio_client = get_minio_client()