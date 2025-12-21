# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import users, rag, history
from app.core.config import settings

app = FastAPI(title="RAG Chatbot API")

# 配置 CORS (允许前端访问)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 生产环境建议改为具体的 ["http://localhost:5173"]
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
    return {"message": "Welcome to RAG Chatbot API. Docs at /docs"}

if __name__ == "__main__":
    import uvicorn
    # 允许在 0.0.0.0 上运行以便局域网访问
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)