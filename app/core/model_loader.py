# app/core/model_loader.py

from sentence_transformers import SentenceTransformer
import os

# 全局变量，用来托住模型
global_embedding_model = None

def load_model_on_startup():
    """
    系统启动时调用：加载模型到内存
    """
    global global_embedding_model
    model_path = "/app/models/text2vec-base-chinese"
    
    print(f" [系统启动] 正在预加载模型: {model_path} ...")
    try:
        if os.path.exists(model_path):
            global_embedding_model = SentenceTransformer(model_path)
            print(" 模型加载成功！")
        else:
            print(f" 模型路径不存在: {model_path}")
            # 如果本地调试没有挂载目录，可以回退到在线拉取（可选）
            # global_embedding_model = SentenceTransformer('shibing624/text2vec-base-chinese')
    except Exception as e:
        print(f" 模型加载严重错误: {e}")

def get_embedding_model():
    """
    业务逻辑调用：获取已加载的模型
    """
    if global_embedding_model is None:
        print(" 警告：模型未初始化，尝试紧急加载...")
        load_model_on_startup()
    return global_embedding_model