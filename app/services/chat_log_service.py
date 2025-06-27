import json
from typing import List, Dict
import redis
from app.db.redis_conn import get_redis_conn
from app.db.database import SessionLocal
from app.crud import chat_log_crud, user_crud, manuals_crud

CHAT_LOG_REDIS_KEY = "chat_logs_buffer"
CHAT_LOG_FLUSH_THRESHOLD = 10  # Persist to DB every 10 messages

class ChatLogService:
    def __init__(self):
        self.redis_conn = get_redis_conn()

    def add_chat_to_cache(self, experiment_id: int, user_id: str, manual_id: str, sender: str, message: str):
        """Adds a chat message to the Redis cache and checks if it needs to be flushed."""
        db = SessionLocal()
        try:
            # Convert string IDs to integer primary keys
            user = user_crud.get_user_by_id(db, user_id=user_id)
            db_user_id = user.id if user else None
            if db_user_id is None:
                print(f"Warning: User with user_id '{user_id}' not found.")

            manual = manuals_crud.get_manual_by_manual_id(db, manual_id=manual_id)
            db_manual_id = manual.id if manual else None
            
            if db_manual_id is None:
                print(f"Warning: Manual with manual_id '{manual_id}' not found. Storing chat log with manual_id=NULL.")

            log_entry = {
                "experiment_id": experiment_id,
                "user_id": db_user_id,
                "manual_id": db_manual_id,
                "sender": sender,
                "message": message
            }
            print("rpush", log_entry)
            result = self.redis_conn.rpush(CHAT_LOG_REDIS_KEY, json.dumps(log_entry))
            print("rpush result", result)
            
            if self.redis_conn.llen(CHAT_LOG_REDIS_KEY) >= CHAT_LOG_FLUSH_THRESHOLD:
                print("flush_chat_logs_from_cache_to_db")
                self.flush_chat_logs_from_cache_to_db()
        finally:
            db.close()

    def flush_chat_logs_from_cache_to_db(self):
        """Flushes chat logs from Redis to the main database."""
        try:
            pipe = self.redis_conn.pipeline()
            pipe.lrange(CHAT_LOG_REDIS_KEY, 0, -1)
            pipe.delete(CHAT_LOG_REDIS_KEY)
            logs_json, _ = pipe.execute()

            if not logs_json:
                print("No chat logs in Redis cache to flush.")
                return

            logs_to_db = [json.loads(log) for log in logs_json]
            
            db = SessionLocal()
            try:
                for log in logs_to_db:
                    chat_log_crud.create_chat_log(db, log)
                print(f"Flushed {len(logs_to_db)} chat logs from Redis to DB.")
            finally:
                db.close()

        except Exception as e:
            print(f"Error flushing chat logs to DB: {e}")

# Create a singleton instance
chat_log_service = ChatLogService() 