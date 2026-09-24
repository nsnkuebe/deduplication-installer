from pathlib import Path

try:
    from compression import zstd
    _compress = zstd.compress
    _decompress = zstd.decompress
except ImportError:
    import zstandard as zstd
    _compress = lambda data: zstd.ZstdCompressor().compress(data)
    _decompress = lambda data: zstd.ZstdDecompressor().decompress(data)

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

    def _file_path(self, file_id: str) -> Path:
        algorithm, digest = file_id.split(":", 1)
        if algorithm != "sha256" or len(digest) != 64:
            raise ValueError("invalid file id")
        return self.root / "files" / algorithm / digest[:2] / digest[2:]

    def has(self, chunk_id: str) -> bool:
        path = self._path(chunk_id)
        return path.exists() or path.with_suffix(".zst").exists()

    def put(self, data: bytes, expected_id: str | None = None) -> tuple[str, bool]:
        chunk_id = hash_bytes(data)
        if expected_id is not None and chunk_id != expected_id:
            raise HashMismatch(f"expected {expected_id}, got {chunk_id}")
        path = self._path(chunk_id)
        if self.has(chunk_id):
            return chunk_id, False
        path.parent.mkdir(parents=True, exist_ok=True)
        compressed = _compress(data)
        target = path.with_suffix(".zst") if len(compressed) < len(data) else path
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_bytes(compressed if target.suffix == ".zst" else data)
        temporary.replace(target)
        return chunk_id, True

    def get(self, chunk_id: str) -> bytes:
        path = self._path(chunk_id)
        if path.with_suffix(".zst").exists():
            data = _decompress(path.with_suffix(".zst").read_bytes())
        else:
            data = path.read_bytes()
        if hash_bytes(data) != chunk_id:
            raise HashMismatch(f"corrupt chunk {chunk_id}")
        return data

    def put_file(self, data: bytes, expected_id: str) -> None:
        actual_id = hash_bytes(data)
        if actual_id != expected_id:
            raise HashMismatch(f"expected {expected_id}, got {actual_id}")
        path = self._file_path(expected_id)
        if path.exists():
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(data)
        temporary.replace(path)

    def link_file(self, file_id: str, destination: Path) -> None:
        source = self._file_path(file_id)
        if not source.exists():
            raise FileNotFoundError(file_id)
        destination.hardlink_to(source)