from pathlib import Path
import shutil

from .cas import ChunkStore
from .hashing import hash_bytes


def plan(manifest: dict, store: ChunkStore) -> dict:
    needed = {chunk["hash"]: chunk["len"]
              for file in manifest["files"] for chunk in file["chunks"]}
    download_bytes = sum(size for chunk_id, size in needed.items()
                         if not (store.root / "sha256" / chunk_id.split(":", 1)[1][:2]
                                 / chunk_id.split(":", 1)[1][2:]).exists())
    total_bytes = manifest["total_size"]
    return {
        "total_bytes": total_bytes,
        "download_bytes": download_bytes,
        "saved_bytes": total_bytes - download_bytes,
    }


def install(manifest: dict, store: ChunkStore, destination: Path, fetch) -> None:
    staging = Path(str(destination) + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        for file in manifest["files"]:
            output = staging / file["path"]
            output.parent.mkdir(parents=True, exist_ok=True)
            data = bytearray()
            for chunk in file["chunks"]:
                try:
                    chunk_data = store.get(chunk["hash"])
                except FileNotFoundError:
                    chunk_data = fetch(chunk["hash"])
                    store.put(chunk_data, expected_id=chunk["hash"])
                data.extend(chunk_data)
            if len(data) != file["size"] or hash_bytes(data) != file["file_hash"]:
                raise ValueError(f"file verification failed: {file['path']}")
            output.write_bytes(data)
        if destination.exists():
            shutil.rmtree(destination)
        staging.replace(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise