import redis
import os
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# 환경 변수 불러오기
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
# REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)  # 기본은 None

# Redis 연결 풀 설정 (timeout 포함)
redis_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    # password=REDIS_PASSWORD,
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=3
)

def get_redis_conn():
    """
    Redis 연결 객체 반환
    """
    return redis.Redis(connection_pool=redis_pool)
