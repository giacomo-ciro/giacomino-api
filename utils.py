import datetime
import json
import os
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional
import time
from functools import wraps
from flask import request, jsonify

class MyLogger:
    def __init__(self, name: str = "MyLogger", log_file: Optional[str] = None):
        self.name = name
        self.init_time = datetime.datetime.now()
        self.log_file = log_file
        self.payload = ""
        self.log_count = 0
        self.session_id = self.init_time.strftime("%Y%m%d_%H%M%S")

        # Create log directory if file logging is enabled
        if self.log_file:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)

        # Log initialization
        self.log(f"Logger '{self.name}' initialized", level="INFO")

    def _format_message(self, message: str, level: str = "INFO") -> str:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{level}] [{self.name}] {message}"

    def log(self, message: str, level: str = "INFO", print_console: bool = True):
        formatted_msg = self._format_message(message, level)

        # Print to console
        if print_console:
            print(formatted_msg)

        # Add to payload
        self.payload += f"{formatted_msg}\n"
        self.log_count += 1

        # Write to file if specified
        if self.log_file:
            self._write_to_file(formatted_msg)

    def info(self, message: str):
        self.log(message, "INFO")

    def warning(self, message: str):
        self.log(message, "WARNING")

    def error(self, message: str):
        self.log(message, "ERROR")

    def debug(self, message: str):
        self.log(message, "DEBUG")

    def _write_to_file(self, formatted_message: str):
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(formatted_message + "\n")
        except Exception as e:
            print(f"Failed to write to log file: {e}")

    def log_dict(self, data: Dict[Any, Any], title: str = "Data"):
        """Log a dictionary in a formatted way"""
        self.log(f"{title}: {json.dumps(data, indent=2, default=str)}")

    def log_execution_time(self, func_name: str, start_time: datetime.datetime):
        """Log execution time of a function"""
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        self.log(f"Function '{func_name}' executed in {duration:.3f} seconds")

    def get_stats(self) -> Dict[str, Any]:
        """Get logger statistics"""
        uptime = datetime.datetime.now() - self.init_time
        return {
            "logger_name": self.name,
            "session_id": self.session_id,
            "init_time": self.init_time.strftime("%d-%m-%Y %H:%M:%S"),
            "uptime_seconds": uptime.total_seconds(),
            "total_logs": self.log_count,
            "log_file": self.log_file,
        }

    def dumps(self) -> str:
        """Return all logged messages as string"""
        return self.payload

    def clear(self):
        """Clear the payload and reset log count"""
        self.payload = ""
        self.log_count = 0
        self.log("Logger cleared", level="INFO")

    def __str__(self):
        return f"MyLogger(name='{self.name}', logs={self.log_count}, uptime={datetime.datetime.now() - self.init_time})"

    def __repr__(self):
        return self.__str__()


def requires_env(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if os.path.exists(".env"):
            return func(*args, **kwargs)
        return jsonify({"error": "Environment configuration missing."}), 400

    return wrapper

# In-memory store: {(user, endpoint): [timestamps]}
rate_limit_store = {}

def rate_limit(request_count:int, h:int, logger=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = request.remote_addr  # Or use user id if authenticated
            endpoint = request.endpoint
            key = (user, endpoint)
            now = time.time()
            window = h * 3600

            # Get or create the list of timestamps
            timestamps = rate_limit_store.get(key, [])
            # Remove timestamps outside the window
            timestamps = [ts for ts in timestamps if now - ts < window]

            if len(timestamps) >= request_count:
                return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429

            log_msg = f"[RateLimit] Allowed: user={user}, endpoint={endpoint}, count={len(timestamps)}/{request_count} in last {h}h"
            if logger:
                logger.info(log_msg)

            # Record this request
            timestamps.append(now)
            rate_limit_store[key] = timestamps

            return func(*args, **kwargs)
        return wrapper
    return decorator