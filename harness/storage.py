"""Immutable JSON records and ordered events; active execution is not durable."""

import hashlib
import json
import sqlite3
from typing import Any

from harness.contracts import Rejected, encode


class Store:
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, body TEXT NOT NULL)"
        )

    def put(self, value: dict[str, Any]) -> str:
        body = encode(value)
        if len(body.encode()) > 1_000_000:
            raise Rejected("Reference store limit is 1 MB per record; use external blobs")
        ref = hashlib.sha256(body.encode()).hexdigest()
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO records VALUES (?,?)", (ref, body))
        return ref

    def get(self, ref: str) -> dict[str, Any]:
        row = self.db.execute("SELECT body FROM records WHERE id=?", (ref,)).fetchone()
        if row is None:
            raise Rejected("Unknown artifact")
        if hashlib.sha256(row[0].encode()).hexdigest() != ref:
            raise Rejected("Artifact integrity failure")
        return json.loads(row[0])

    def event(self, **value: Any) -> None:
        with self.db:
            self.db.execute("INSERT INTO events(body) VALUES (?)", (encode(value),))

    def events(self) -> list[dict[str, Any]]:
        return [
            json.loads(body) for (body,) in self.db.execute("SELECT body FROM events ORDER BY seq")
        ]

    def close(self) -> None:
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
