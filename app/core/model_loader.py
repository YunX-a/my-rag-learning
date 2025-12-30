# app/core/model_loader.py
from sentence_transformers import SentenceTransformer
import os

global_embedding_model = None

def load_model_on_startup():
    global global_embedding_model
    
    # CAN: 优先查找 BGE 模型
    possible_paths = [
        "models/bge-base-zh-v1.5",           # 本地运行
        "/app/models/bge-base-zh-v1.5",      # Docker 容器
        "models/text2vec-base-chinese",      # 旧模型备选
    ]
    
    selected_path = None
    for path in possible_paths:
        if os.path.exists(path):
            selected_path = path
            print(f"发现模型文件: {selected_path}")
            break
            
    if not selected_path:
        print(f"未找到模型文件，请先运行 download_model.py")
        return

    print(f"正在加载 Embedding 模型...")
    # device='cuda' 利用你的 3060 显卡
    try:
        global_embedding_model = SentenceTransformer(selected_path, device='cuda')
        print("模型加载成功 (CUDA Enabled)！")
    except Exception:
        print("CUDA 加载失败，尝试使用 CPU...")
        global_embedding_model = SentenceTransformer(selected_path, device='cpu')

def get_embedding_model():
    if global_embedding_model is None:
        load_model_on_startup()
    return global_embedding_model