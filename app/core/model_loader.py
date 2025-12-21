# app/core/model_loader.py

from sentence_transformers import SentenceTransformer
import os

# 全局变量，用来托住模型
global_embedding_model = None

def load_model_on_startup():
    """
    加载模型，自动适配本地路径和 Docker 路径
    """
    global global_embedding_model
    
    # 备选路径列表
    possible_paths = [
        "models/text2vec-base-chinese",          # 1. 本地相对路径 (对应你在项目根目录运行)
        "/app/models/text2vec-base-chinese",     # 2. Docker 容器内路径
        "./models/text2vec-base-chinese",        # 3. 本地相对路径变体
        # 如果你是在 windows 下的其他盘符，也可以在这里加绝对路径
    ]
    
    selected_path = None
    
    # 遍历检查哪个路径是真实存在的
    for path in possible_paths:
        if os.path.exists(path):
            selected_path = path
            print(f" 发现模型文件，路径: {selected_path}")
            break
            
    if not selected_path:
        print(f" 错误：在以下路径均未找到模型: {possible_paths}")
        print(" 提示：请确保你已在项目根目录运行脚本，且 models 文件夹已下载。")
        # 最后的兜底：如果本地没模型，尝试在线拉取 (可选)
        # selected_path = "shibing624/text2vec-base-chinese"
        return

    print(f" [系统启动] 正在加载模型: {selected_path} ...")
    try:
        global_embedding_model = SentenceTransformer(selected_path)
        print(" 模型加载成功！")
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