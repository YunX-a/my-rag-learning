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
    #  修改：默认使用 Docker 服务名 'rag_mysql'
    DB_HOST: str = "rag_mysql"  
    DB_PORT: int = 3306
    DB_NAME: str = "rag_db"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # --- 3. 向量数据库配置 (Milvus) ---
    #  修改：默认使用 Docker 服务名 'milvus-standalone'
    MILVUS_HOST: str = "milvus-standalone"  
    MILVUS_PORT: int = 19530
    COLLECTION_NAME: str = "rag_collection"
    EMBEDDING_MODEL_NAME: str = "/app/models/bge-base-zh-v1.5"

    @property
    def MILVUS_URI(self) -> str:
        return f"http://{self.MILVUS_HOST}:{self.MILVUS_PORT}"

    # --- 4. 对象存储配置 (Minio) ---
    #  修改：默认使用 Docker 服务名 'milvus-minio'
    MINIO_ENDPOINT: str = "milvus-minio:9002"  #  原来是 localhost:9002
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
    #  修改：默认使用 Docker 服务名 'rag_redis'
    REDIS_HOST: str = "rag_redis"  #  原来是 localhost
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
        #  建议改为 False，防止因为大小写问题导致 Docker 环境变量没被读取
        case_sensitive=False 
    )
    
    # --- 7. Elasticsearch 配置 ---
    ES_HOST: str = "rag_elasticsearch" # 本地开发可能需要改为 localhost，Docker内用服务名
    ES_PORT: int = 9200
    ES_INDEX: str = "rag_documents"
    
    @property
    def ES_URL(self) -> str:
        return f"http://{self.ES_HOST}:{self.ES_PORT}"

# 实例化配置
settings = Settings()

# --- 启动自检 (DEBUG) ---
print("\n" + "="*50)
print(f" RAG Backend Configuration Loaded (Docker Mode)")
print(f"  DB Host:     {settings.DB_HOST}:{settings.DB_PORT}")
print(f"  Milvus Host: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
print(f"  Redis Host:  {settings.REDIS_HOST}:{settings.REDIS_PORT}")
print(f"  Minio Endpoint: {settings.MINIO_ENDPOINT}")
print("="*50 + "\n")