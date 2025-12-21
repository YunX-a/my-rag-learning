# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 创建数据库引擎
# pool_pre_ping=True 对于 MySQL 尤为重要，它可以防止“MySQL server has gone away”的连接断开错误
engine = create_engine(
    settings.DATABASE_URL, 
    pool_pre_ping=True
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    FastAPI 依赖项：获取数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()