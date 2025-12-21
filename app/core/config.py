# app/core/config.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field
from datetime import timedelta

class Settings(BaseSettings):
    # --- 1. LLM API 配置 ---
    DEEPSEEK_API_KEY: SecretStr = Field(default=SecretStr(""), description="DeepSeek API密钥")
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_MODEL_NAME: str = "deepseek-chat"

    # --- 2. 数据库配置 (MySQL) ---
    DB_USER: str = "rag_user"
    DB_PASSWORD: str = "rag_password"
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306  # 建议用 int
    DB_NAME: str = "rag_db"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # --- 3. 向量数据库配置 (Milvus) ---
    # ⚠️ 注意：Docker 运行时这里必须解析为 'milvus-standalone'
    MILVUS_HOST: str = "localhost" 
    MILVUS_PORT: int = 19530
    COLLECTION_NAME: str = "rag_collection"
    EMBEDDING_MODEL_NAME: str = "shibing624/text2vec-base-chinese"

    @property
    def MILVUS_URI(self) -> str:
        return f"http://{self.MILVUS_HOST}:{self.MILVUS_PORT}"

    # --- 4. 对象存储配置 (Minio) ---
    MINIO_ENDPOINT: str = "localhost:9002"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "rag-documents"
    MINIO_SECURE: bool = False

    # --- 5. 安全配置 ---
    SECRET_KEY: SecretStr = Field(default=SecretStr("your-secret-key-here"), description="JWT签名密钥")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 
    
    @property
    def ACCESS_TOKEN_EXPIRE_DELTA(self) -> timedelta:
        return timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # --- 6. Redis 配置 ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CACHE_TTL: int = 3600 

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # --- Pydantic V2 配置 ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # ⚠️ 关键：设为 True 确保环境变量(Docker env) 优先级高于 .env 文件
        # 如果这里是 False，且你挂载了包含 MILVUS_HOST=localhost 的 .env 文件，
        # 它可能会覆盖 Docker 的环境变量。
        case_sensitive=True 
    )

# 实例化配置
settings = Settings()

# --- 启动自检 (DEBUG) ---
# 这段代码会在后端启动时直接打印当前生效的配置，助你快速排查
print("\n" + "="*50)
print(f" RAG Backend Configuration Loaded")
print(f"  DB Host:     {settings.DB_HOST}:{settings.DB_PORT}")
print(f"  Milvus Host: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
print(f"  Redis Host:  {settings.REDIS_HOST}:{settings.REDIS_PORT}")
print("="*50 + "\n")