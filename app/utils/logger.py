import datetime
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, Optional


class MyLogger:
    def __init__(self, name: str = "MyLogger", logs_db_path: Optional[str] = None):
        self.name = name
        self.init_time = datetime.datetime.now()
        self._db_path = logs_db_path
        self.log_count = 0
        self.session_id = self.init_time.strftime("%Y%m%d_%H%M%S")
        self._lock = threading.Lock()

        if self._db_path:
            self.setup()

        self.log(f"Logger '{self.name}' initialized", level="INFO")

    def setup(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level     TEXT NOT NULL,
                    logger    TEXT NOT NULL,
                    message   TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)")
            conn.commit()

    def _format_message(self, message: str, level: str = "INFO") -> str:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{level}] [{self.name}] {message}"

    def log(self, message: str, level: str = "INFO", print_console: bool = True):
        formatted_msg = self._format_message(message, level)
        if print_console:
            print(formatted_msg)
        with self._lock:
            self.log_count += 1
        if self._db_path:
            self._write_to_db(level, message)

    def info(self, message: str):
        self.log(message, "INFO")

    def warning(self, message: str):
        self.log(message, "WARNING")

    def error(self, message: str):
        self.log(message, "ERROR")

    def debug(self, message: str):
        self.log(message, "DEBUG")

    def _write_to_db(self, level: str, message: str) -> None:
        try:
            with self._lock, sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT INTO logs (timestamp, level, logger, message) VALUES (?, ?, ?, ?)",
                    (datetime.datetime.now().isoformat(), level, self.name, message),
                )
                conn.commit()
        except Exception as e:
            print(f"Failed to write to log DB: {e}")

    def log_dict(self, data: Dict[Any, Any], title: str = "Data"):
        self.log(f"{title}: {json.dumps(data, indent=2, default=str)}")

    def log_execution_time(self, func_name: str, start_time: datetime.datetime):
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        self.log(f"Function '{func_name}' executed in {duration:.3f} seconds")

    def get_stats(self) -> Dict[str, Any]:
        uptime = datetime.datetime.now() - self.init_time
        stats: Dict[str, Any] = {
            "logger_name": self.name,
            "session_id": self.session_id,
            "init_time": self.init_time.strftime("%d-%m-%Y %H:%M:%S"),
            "uptime_seconds": uptime.total_seconds(),
            "total_logs": self.log_count,
            "logs_db_path": self._db_path,
        }
        if self._db_path:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    "SELECT level, COUNT(*) FROM logs WHERE logger=? GROUP BY level",
                    (self.name,),
                ).fetchall()
            stats["level_counts"] = {row[0]: row[1] for row in rows}
        return stats

    def __str__(self):
        return f"MyLogger(name='{self.name}', logs={self.log_count}, uptime={datetime.datetime.now() - self.init_time})"

    def __repr__(self):
        return self.__str__()
