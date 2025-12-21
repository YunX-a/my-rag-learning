# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Any
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

# 密码哈希上下文 (复用原有逻辑，或者放在 password.py 也可以)
# 如果你之前的 password.py 已经处理了 pwd_context，这里可以只处理 Token

ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    生成 JWT Access Token
    :param data: 载荷数据 (e.g. {"sub": "username"})
    :param expires_delta: 过期时间增量
    """
    to_encode = data.copy()
    
    if expires_delta:
        # 使用 UTC 时间
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # 默认 15 分钟
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    # 将过期时间写入 payload ("exp" 是 JWT 标准字段)
    to_encode.update({"exp": expire})
    
    # 使用配置中的 SECRET_KEY 进行签名
    # 注意：settings.SECRET_KEY 是 SecretStr 类型，需要用 .get_secret_value() 获取
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY.get_secret_value(), 
        algorithm=ALGORITHM
    )
    
    return encoded_jwt