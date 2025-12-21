# app/core/password.py
import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否与哈希后的密码匹配"""
    # bcrypt 需要字节串，所以我们对它们进行编码
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    """生成密码的哈希值"""
    # bcrypt 同样需要字节串进行哈希
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    # 将哈希后的字节串解码成字符串以便存入数据库
    return hashed.decode('utf-8')