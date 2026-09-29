import json
from pathlib import Path, PurePosixPath

from .cas import ChunkStore
from .hashing import hash_bytes


def canonical_bytes(manifest: dict) -> bytes:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _validate_path(path: str) -> None:
    parsed = PurePosixPath(path)
    if parsed.is_absolute() or ".." in parsed.parts or not parsed.parts:
        raise ValueError(f"invalid relative path: {path}")


def _safe_root_relative(root: Path, path: Path) -> Path:
    resolved = path.resolve(strict=False)
    root_resolved = root.resolve(strict=False)
    try:
        return resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"refusing path escaping package root: {path}") from exc


def publish_dir(root: Path, name: str, version: str, store: ChunkStore, chunker) -> dict:
    files = []
    root = Path(root)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        _validate_path(relative)
        _safe_root_relative(root, path)
        data = path.read_bytes()
        chunks = []
        for offset, length in chunker.split(data):
            chunk = data[offset:offset + length]
            chunk_id, _ = store.put(chunk)
            chunks.append({"hash": chunk_id, "off": offset, "len": length})
        files.append({
            "path": relative,
            "type": "file",
            "size": len(data),
            "file_hash": hash_bytes(data),
            "chunks": chunks,
        })
    return {
        "format": 1,
        "name": name,
        "version": version,
        "hash_algo": "sha256",
        "chunker": {"type": "fixed", "size": chunker.size},
        "files": files,
        "total_size": sum(file["size"] for file in files),
    }