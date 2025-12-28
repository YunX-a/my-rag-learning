# scripts/sync_minio.py
import os
import sys

# 将项目根目录加入 python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.minio_service import minio_client
from app.core.config import settings

def sync_local_to_minio(local_folder: str = "data/pdfs"):
    """
    将本地文件夹中的 PDF 同步上传到 Minio
    """
    bucket_name = settings.MINIO_BUCKET_NAME

    # 1. 确保 Bucket 存在
    if not minio_client.bucket_exists(bucket_name):
        print(f" Bucket '{bucket_name}' 不存在，正在创建...")
        minio_client.make_bucket(bucket_name)

    print(f" 开始将 '{local_folder}' 同步到 Minio: {bucket_name} ...")
    
    success_count = 0
    
    # 2. 遍历本地文件
    for root, dirs, files in os.walk(local_folder):
        for filename in files:
            if filename.lower().endswith('.pdf'):
                local_path = os.path.join(root, filename)
                # 在 Minio 中的文件名 (保持相对路径结构，或者直接用文件名)
                # 这里为了简单，我们直接用文件名，如果你有重名文件可能需要注意
                object_name = filename 
                
                print(f"正在上传: {object_name} ... ", end="", flush=True)
                
                try:
                    # fput_object 专门用来上传本地文件
                    minio_client.fput_object(
                        bucket_name, 
                        object_name, 
                        local_path,
                        content_type="application/pdf"
                    )
                    print("成功")
                    success_count += 1
                except Exception as e:
                    print(f"失败: {e}")

    print("-" * 50)
    print(f"同步完成！共上传 {success_count} 个文件。")

if __name__ == "__main__":
    sync_local_to_minio()