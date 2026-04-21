import sqlite3
import threading

import pytest

from app.utils.logger import MyLogger


def test_logger_creates_db(tmp_path):
    db_path = str(tmp_path / "logs.db")
    MyLogger(name="test", logs_db_path=db_path)
    assert (tmp_path / "logs.db").exists()


def test_logger_writes_entry(tmp_path):
    db_path = str(tmp_path / "logs.db")
    logger = MyLogger(name="test", logs_db_path=db_path)
    logger.info("hello world")
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT level, message FROM logs WHERE message='hello world'").fetchall()
    assert rows == [("INFO", "hello world")]


def test_logger_all_levels(tmp_path):
    db_path = str(tmp_path / "logs.db")
    logger = MyLogger(name="test", logs_db_path=db_path)
    logger.warning("w")
    logger.error("e")
    logger.debug("d")
    with sqlite3.connect(db_path) as conn:
        levels = {r[0] for r in conn.execute("SELECT level FROM logs").fetchall()}
    assert {"WARNING", "ERROR", "DEBUG"}.issubset(levels)


def test_logger_get_stats_level_counts(tmp_path):
    db_path = str(tmp_path / "logs.db")
    logger = MyLogger(name="test", logs_db_path=db_path)
    logger.error("e1")
    logger.error("e2")
    stats = logger.get_stats()
    assert "level_counts" in stats
    assert stats["level_counts"].get("ERROR", 0) >= 2


def test_logger_thread_safety(tmp_path):
    db_path = str(tmp_path / "logs.db")
    logger = MyLogger(name="test", logs_db_path=db_path)
    threads = [threading.Thread(target=lambda: logger.info("msg")) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert logger.log_count >= 20


def test_logger_no_db(capsys):
    # Logger without a db_path should not raise
    logger = MyLogger(name="test")
    logger.info("no db")
    assert logger.log_count >= 1
