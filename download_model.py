import os
# 1. 设置国内镜像环境变量 (关键！)
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

from huggingface_hub import snapshot_download

print("🚀 开始下载模型 shibing624/text2vec-base-chinese ...")

# 2. 下载到本地的 models/text2vec-base-chinese 目录
snapshot_download(
    repo_id="shibing624/text2vec-base-chinese",
    local_dir="models/text2vec-base-chinese",
    local_dir_use_symlinks=False  # 确保下载的是真实文件，不是软链接
)

print("✅ 下载完成！文件已保存在 models/text2vec-base-chinese")
