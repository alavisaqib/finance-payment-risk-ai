import json
import sqlite3
import time
from contextlib import contextmanager
from .config import state_dir

@contextmanager
def connect():
    connection = sqlite3.connect(state_dir() / 'operations.sqlite3', timeout=15)
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, created REAL, payload TEXT)')
    connection.execute('CREATE TABLE IF NOT EXISTS audit (id TEXT PRIMARY KEY, created REAL, payload TEXT)')
    try:
        with connection:
            yield connection
    finally:
        connection.close()

def cached(key):
    with connect() as connection:
        row = connection.execute('SELECT payload FROM cache WHERE key=? AND created>?', (key, time.time() - 3600)).fetchone()
    return json.loads(row[0]) if row else None

def record(key, result):
    payload = json.dumps(result, allow_nan=False)
    with connect() as connection:
        connection.execute('INSERT OR REPLACE INTO cache VALUES (?, ?, ?)', (key, time.time(), payload))
        connection.execute('DELETE FROM cache WHERE created < ?', (time.time() - 3600,))
        connection.execute('INSERT INTO audit VALUES (?, ?, ?)', (result['run_id'], time.time(), payload))

def history(limit=20):
    with connect() as connection:
        rows = connection.execute('SELECT payload FROM audit ORDER BY created DESC LIMIT ?', (limit,)).fetchall()
    return [json.loads(row[0]) for row in rows]
