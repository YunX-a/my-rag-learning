# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.routers import users, rag, history, agent
from app.db.session import engine
from app.models.user import Base
from app.core.model_loader import load_model_on_startup

# 自动建表
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时加载模型
    load_model_on_startup()
    yield
    print("系统关闭")

app = FastAPI(title="RAG Backend", lifespan=lifespan)


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
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])

@app.get("/")
def read_root():
    return {"message": "RAG Backend is running!"}