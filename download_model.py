import os
import shutil

# 1. 尝试导入 modelscope
try:
    from modelscope import snapshot_download
except ImportError:
    print("错误: 未找到 modelscope 库。")
    print("请先运行: uv pip install modelscope")
    exit(1)

print("CAN 正在为你从 ModelScope (魔搭社区) 下载模型...")
print("目标模型: BAAI/bge-base-zh-v1.5")

# 2. 配置路径
# ModelScope 默认会下载到 <cache_dir>/<namespace>/<model_name>
# 例如: models/BAAI/bge-base-zh-v1.5
DOWNLOAD_DIR = "models"
MODEL_ID = "BAAI/bge-base-zh-v1.5"
FINAL_PATH = "models/bge-base-zh-v1.5"

try:
    # 开始下载
    #ZB: cache_dir 指定下载的基础目录
    download_path = snapshot_download(MODEL_ID, cache_dir=DOWNLOAD_DIR)
    print(f"下载成功！原始路径: {download_path}")

    # 3. 路径标准化
    # 为了配合 app/core/model_loader.py 的逻辑，我们将模型移动到 models/bge-base-zh-v1.5
    
    # 检查当前下载路径是否已经是目标路径 (防止重复运行时的路径混乱)
    # modelscope 下载后的路径通常是绝对路径
    if os.path.abspath(download_path) != os.path.abspath(FINAL_PATH):
        print(f"正在整理文件结构，目标路径: {FINAL_PATH} ...")
        
        # 如果目标文件夹已存在，先删除（防止旧文件干扰）
        if os.path.exists(FINAL_PATH):
            shutil.rmtree(FINAL_PATH)
            
        # 移动文件
        # 注意：download_path 是深层目录，我们把它移出来
        shutil.move(download_path, FINAL_PATH)
        
        # 尝试清理 ModelScope留下的空目录 (models/BAAI)
        try:
            parent_dir = os.path.dirname(download_path)
            if len(os.listdir(parent_dir)) == 0:
                os.rmdir(parent_dir)
        except:
            pass
            
        print(f"模型已就绪: {FINAL_PATH}")
    else:
        print(f"模型路径已就绪: {FINAL_PATH}")

except Exception as e:
    print(f"下载失败: {e}")
    print("提示: 请检查网络，虽然 ModelScope 是国内源，但也需要联网。")