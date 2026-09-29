import json
import sqlite3
from pathlib import Path
from time import time


class LocalDatabase:
    """SQLite-backed refcount store for files and chunks.

    The database tracks reference counts for chunk and file objects. Zero-ref rows are
    retained until GC runs so callers can safely observe a stale object as having
    refcount 0 before the grace period expires.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._journal_path = self.path.with_suffix(f"{self.path.suffix}.journal" if self.path.suffix else ".journal")
        self._connection = sqlite3.connect(str(self.path))
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=NORMAL")
        self._ensure_schema()
        self.recover()

    def close(self) -> None:
        self._journal_path.unlink(missing_ok=True)
        self._connection.close()

    def _ensure_schema(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS objects (
                object_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                refcount INTEGER NOT NULL DEFAULT 0,
                size INTEGER NOT NULL DEFAULT 0,
                first_seen REAL NOT NULL,
                last_seen REAL NOT NULL,
                PRIMARY KEY (object_type, object_id)
            )
            """
        )
        self._connection.commit()

    def _record_journal(self, object_type: str, object_id: str, *, refcount: int, size: int | None = None) -> None:
        payload = {
            "object_type": object_type,
            "object_id": object_id,
            "status": "committed",
            "refcount": int(refcount),
            "delta": 0,
            "size": int(size if size is not None else 0),
            "ts": time(),
        }
        with self._journal_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True))
            handle.write("\n")

    def _apply_journal_entry(self, entry: dict) -> None:
        status = entry.get("status")
        if status != "committed":
            return
        object_type = entry.get("object_type")
        object_id = entry.get("object_id")
        if object_type not in {"chunk", "file"} or not object_id:
            return

        row = self._connection.execute(
            "SELECT refcount, size, first_seen, last_seen FROM objects WHERE object_type = ? AND object_id = ?",
            (object_type, object_id),
        ).fetchone()
        now = time()
        current_refcount = 0 if row is None else int(row[0])
        current_size = 0 if row is None else int(row[1])

        refcount = entry.get("refcount")
        delta = entry.get("delta")
        if refcount is None and delta is not None:
            refcount = current_refcount + int(delta)
        elif refcount is None:
            refcount = current_refcount

        size = int(entry.get("size", current_size))
        refcount = max(0, int(refcount))

        if row is None:
            self._connection.execute(
                "INSERT INTO objects (object_type, object_id, refcount, size, first_seen, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
                (object_type, object_id, refcount, size, now, now),
            )
        elif current_refcount >= refcount:
            self._connection.execute(
                "UPDATE objects SET size = ?, last_seen = ? WHERE object_type = ? AND object_id = ?",
                (size if size else current_size, now, object_type, object_id),
            )
        else:
            self._connection.execute(
                "UPDATE objects SET refcount = ?, size = ?, last_seen = ? WHERE object_type = ? AND object_id = ?",
                (refcount, size if size else current_size, now, object_type, object_id),
            )
        self._connection.commit()

    def recover(self) -> int:
        if not self._journal_path.exists():
            return 0
        recovered = 0
        with self._journal_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._apply_journal_entry(entry)
                recovered += 1
        self._journal_path.unlink(missing_ok=True)
        return recovered

    def _touch(self, object_type: str, object_id: str, *, delta: int, size: int | None = None) -> int:
        now = time()
        row = self._connection.execute(
            "SELECT refcount, size, first_seen, last_seen FROM objects WHERE object_type = ? AND object_id = ?",
            (object_type, object_id),
        ).fetchone()

        if row is None:
            if delta <= 0:
                return 0
            refcount = delta
            first_seen = now
            data_size = size if size is not None else 0
            self._connection.execute(
                "INSERT INTO objects (object_type, object_id, refcount, size, first_seen, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
                (object_type, object_id, refcount, data_size, first_seen, now),
            )
            self._connection.commit()
            self._record_journal(object_type, object_id, refcount=refcount, size=data_size)
            return refcount

        current_refcount, current_size, _, _ = row
        next_refcount = current_refcount + delta
        if next_refcount < 0:
            next_refcount = 0

        if next_refcount == 0:
            self._connection.execute(
                "UPDATE objects SET refcount = 0, size = ?, last_seen = ? WHERE object_type = ? AND object_id = ?",
                (size if size is not None else current_size, now, object_type, object_id),
            )
        else:
            self._connection.execute(
                "UPDATE objects SET refcount = ?, size = ?, last_seen = ? WHERE object_type = ? AND object_id = ?",
                (next_refcount, size if size is not None else current_size, now, object_type, object_id),
            )
        self._connection.commit()
        self._record_journal(object_type, object_id, refcount=next_refcount, size=size if size is not None else current_size)
        return next_refcount

    def acquire_chunk(self, chunk_id: str, *, size: int | None = None) -> int:
        return self._touch("chunk", chunk_id, delta=1, size=size)

    def release_chunk(self, chunk_id: str, *, size: int | None = None) -> int:
        return self._touch("chunk", chunk_id, delta=-1, size=size)

    def acquire_file(self, file_id: str, *, size: int | None = None) -> int:
        return self._touch("file", file_id, delta=1, size=size)

    def release_file(self, file_id: str, *, size: int | None = None) -> int:
        return self._touch("file", file_id, delta=-1, size=size)

    def refcount(self, object_type: str, object_id: str) -> int:
        row = self._connection.execute(
            "SELECT refcount FROM objects WHERE object_type = ? AND object_id = ?",
            (object_type, object_id),
        ).fetchone()
        return 0 if row is None else int(row[0])

    def chunk_refcount(self, chunk_id: str) -> int:
        return self.refcount("chunk", chunk_id)

    def file_refcount(self, file_id: str) -> int:
        return self.refcount("file", file_id)

    def has_chunk(self, chunk_id: str) -> bool:
        return self.chunk_refcount(chunk_id) > 0

    def has_file(self, file_id: str) -> bool:
        return self.file_refcount(file_id) > 0

    def install_manifest(self, manifest: dict) -> None:
        for file in manifest.get("files", []):
            self.acquire_file(file["file_hash"], size=file.get("size", 0))
            for chunk in file.get("chunks", []):
                self.acquire_chunk(chunk["hash"], size=chunk.get("len", 0))

    def uninstall_manifest(self, manifest: dict) -> None:
        for file in reversed(manifest.get("files", [])):
            self.release_file(file["file_hash"], size=file.get("size", 0))
            for chunk in reversed(file.get("chunks", [])):
                self.release_chunk(chunk["hash"], size=chunk.get("len", 0))

    def gc(self, grace_seconds: int = 60) -> int:
        now = time()
        cursor = self._connection.execute(
            "DELETE FROM objects WHERE refcount = 0 AND last_seen <= ?",
            (now - float(grace_seconds),),
        )
        self._connection.commit()
        return cursor.rowcount

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


Database = LocalDatabase
LocalDB = LocalDatabase
