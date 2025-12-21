# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import users, rag, history
from app.core.config import settings

from app.db.session import engine
from app.models.user import Base
from app.models.chat import Conversation, Message
# ----------------

# --- 关键动作：启动时自动创建表 ---
# 这句话会检查数据库，如果 'users' 表不存在，就会自动创建它
Base.metadata.create_all(bind=engine)
# ---------------------------------

app = FastAPI(title="RAG Chatbot API")

# 配置 CORS (允许前端访问)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(rag.router, prefix="/api/rag", tags=["rag"])
app.include_router(history.router, prefix="/api/history", tags=["history"])

@app.get("/")
def read_root():
    return {"message": "RAG Backend is running!", "docs_url": "/docs"}

if __name__ == "__main__":
    import uvicorn
    # 这里的 reload=True 可能会导致 create_all 运行两次，不过没关系，它是幂等的
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)