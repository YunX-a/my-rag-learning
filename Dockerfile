# 1. 使用官方轻量级 Python 镜像
FROM python:3.10-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 安装系统依赖 (编译某些库需要)
# netcat-openbsd 用于启动脚本中的健康检查
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources || \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list
    
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 4. 复制依赖文件并安装
COPY requirements.txt .
# 使用清华源加速安装，避免超时
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 5. 复制项目代码
COPY . .

# 6. 暴露端口
EXPOSE 8000

# 7. 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]