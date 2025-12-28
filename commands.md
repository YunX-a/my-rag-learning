# 1. Docker 服务管理
# 启动所有服务 (构建镜像并后台运行)
docker compose up -d --build


# 查看服务日志 

# 查看后端日志 (实时刷新)
docker compose logs -f backend

# 查看所有服务日志
docker compose logs -f


# 重启特定服务 (修改代码后让其生效)

# 重启后端
docker compose restart backend

# 重启前端 (如果前端也在docker里)
docker compose restart frontend

# 停止所有服务
docker compose down

# 2. 数据与脚本 (本地运行)
# 注意：在容器外（本机）运行脚本时，必须设置 MILVUS_HOST=localhost，否则连不上 Docker 里的数据库。

# 批量上传 PDF (处理 data/pdfs 目录下的文件)
MILVUS_HOST=localhost python scripts/batch_ingest.py

# 清空向量数据库 (Milvus)
MILVUS_HOST=localhost python scripts/reset_db.py

# 手动下载模型
python download_model.py

# 3. 数据库维护 (MySQL)
# 进入 MySQL 命令行
docker exec -it rag_mysql mysql -u rag_user -prag_password rag_db


# 强制重置数据库表 (解决字段缺失/表结构变更问题) 注意：此操作会清空所有历史对话记录！

# 停止后端 (防止锁表)
docker stop rag_backend

# 删除旧表
docker exec -it rag_mysql mysql -u rag_user -prag_password rag_db -e "DROP TABLE IF EXISTS messages; DROP TABLE IF EXISTS conversations;"

# 启动后端 (自动重建新表)
docker start rag_backend

# 提交代码

git add .
git commit -m "提交说明"
git push origin main
git push github main

# 启动项目

docker compose up -d --build

cd frontend && npm run dev