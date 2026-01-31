import os
import sqlite3
import time
from typing import Optional


class DedupStore:
    def __init__(
        self,
        db_path: str,
        window_seconds: int,
        cleanup_interval_seconds: int = 3600
    ) -> None:
        self.db_path = db_path
        self.window_seconds = window_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self._last_cleanup: int = 0

        directory = os.path.dirname(db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        self.conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS processed_messages ("
            "message_id TEXT PRIMARY KEY,"
            "created_at INTEGER NOT NULL"
            ")"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_processed_messages_created_at "
            "ON processed_messages(created_at)"
        )
        self.conn.commit()

    def is_duplicate(self, message_id: str) -> bool:
        now = int(time.time())
        if now - self._last_cleanup >= self.cleanup_interval_seconds:
            self.cleanup(now)

        cursor = self.conn.execute(
            "INSERT OR IGNORE INTO processed_messages (message_id, created_at) "
            "VALUES (?, ?)",
            (message_id, now)
        )
        self.conn.commit()
        return cursor.rowcount == 0

    def cleanup(self, now: Optional[int] = None) -> None:
        if now is None:
            now = int(time.time())
        cutoff = now - self.window_seconds
        self.conn.execute(
            "DELETE FROM processed_messages WHERE created_at < ?",
            (cutoff,)
        )
        self.conn.commit()
        self._last_cleanup = now
