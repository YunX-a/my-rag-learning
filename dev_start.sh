#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}>>> 正在启动 RAG 开发环境...${NC}"

# 启动 Redis
if [ ! "$(docker ps -q -f name=rag-redis)" ]; then
    if [ "$(docker ps -aq -f name=rag-redis)" ]; then
        echo "启动现有 Redis 容器..."
        docker start rag-redis
    else
        echo "创建并启动 Redis..."
        docker run -d --name rag-redis -p 6379:6379 redis:latest
    fi
else
    echo "Redis 正在运行。"
fi

# 启动 Minio
if [ ! "$(docker ps -q -f name=rag-minio)" ]; then
    if [ "$(docker ps -aq -f name=rag-minio)" ]; then
        echo "启动现有 Minio 容器..."
        docker start rag-minio
    else
        echo "创建并启动 Minio..."
        docker run -d --name rag-minio -p 9000:9000 -p 9001:9001 \
          -e "MINIO_ROOT_USER=minioadmin" \
          -e "MINIO_ROOT_PASSWORD=minioadmin" \
          quay.io/minio/minio server /data --console-address ":9001"
    fi
else
    echo "Minio 正在运行。"
fi

echo -e "${GREEN}>>> 环境准备就绪！${NC}"
echo "Minio 控制台: http://localhost:9001 (账号/密码: minioadmin)"
