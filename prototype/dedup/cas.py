from pathlib import Path

from .hashing import hash_bytes


class HashMismatch(ValueError):
    pass


class ChunkStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, chunk_id: str) -> Path:
        algorithm, digest = chunk_id.split(":", 1)
        if algorithm != "sha256" or len(digest) != 64:
            raise ValueError("invalid chunk id")
        return self.root / algorithm / digest[:2] / digest[2:]

    def put(self, data: bytes, expected_id: str | None = None) -> tuple[str, bool]:
        chunk_id = hash_bytes(data)
        if expected_id is not None and chunk_id != expected_id:
            raise HashMismatch(f"expected {expected_id}, got {chunk_id}")
        path = self._path(chunk_id)
        if path.exists():
            return chunk_id, False
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(data)
        temporary.replace(path)
        return chunk_id, True

    def get(self, chunk_id: str) -> bytes:
        data = self._path(chunk_id).read_bytes()
        if hash_bytes(data) != chunk_id:
            raise HashMismatch(f"corrupt chunk {chunk_id}")
        return data