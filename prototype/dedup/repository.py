import json
import shutil
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen

from .cas import ChunkStore
from .hashing import hash_bytes
from .manifest import canonical_bytes


def _chunk_path(root: Path, chunk_id: str) -> Path:
    algorithm, digest = chunk_id.split(":", 1)
    if algorithm != "sha256" or len(digest) != 64:
        raise ValueError("invalid chunk id")
    return root / "chunks" / algorithm / digest[:2] / digest[2:]


class StaticRepository:
    def __init__(self, root: Path):
        self.root = Path(root)

    def publish(self, manifest: dict, store: ChunkStore) -> None:
        name = manifest["name"]
        version = manifest["version"]
        manifest_path = self.root / "manifests" / name / f"{version}.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_bytes(canonical_bytes(manifest))
        for file in manifest["files"]:
            for chunk in file["chunks"]:
                target = _chunk_path(self.root, chunk["hash"])
                if target.exists():
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(store.get(chunk["hash"]))
        index_path = self.root / "index.json"
        index = json.loads(index_path.read_text()) if index_path.exists() else {"packages": {}}
        versions = index["packages"].setdefault(name, [])
        if version not in versions:
            versions.append(version)
            versions.sort()
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_bytes(canonical_bytes(index))


class RepositoryClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/") + "/"

    def _url(self, relative: str) -> str:
        parsed = urlparse(relative)
        if parsed.scheme or parsed.netloc or ".." in Path(relative).parts:
            raise ValueError("invalid repository path")
        return urljoin(self.base_url, quote(relative, safe="/"))

    def get_index(self) -> dict:
        with urlopen(self._url("index.json")) as response:
            return json.loads(response.read())

    def get_manifest(self, name: str, version: str) -> dict:
        with urlopen(self._url(f"manifests/{name}/{version}.json")) as response:
            return json.loads(response.read())

    def download_chunk(self, chunk_id: str, destination: Path) -> None:
        algorithm, digest = chunk_id.split(":", 1)
        if algorithm != "sha256" or len(digest) != 64:
            raise ValueError("invalid chunk id")
        destination = Path(destination)
        existing = destination.stat().st_size if destination.exists() else 0
        request = Request(self._url(f"chunks/{algorithm}/{digest[:2]}/{digest[2:]}"))
        if existing:
            request.add_header("Range", f"bytes={existing}-")
        try:
            with urlopen(request) as response:
                status = response.status
                mode = "ab" if existing and status == 206 else "wb"
                if mode == "wb":
                    existing = 0
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open(mode) as output:
                    shutil.copyfileobj(response, output)
        except HTTPError as error:
            if error.code == 416 and destination.exists():
                return
            raise
        data = destination.read_bytes()
        if hash_bytes(data) != chunk_id:
            destination.unlink(missing_ok=True)
            raise ValueError(f"downloaded chunk failed verification: {chunk_id}")

    def fetch_chunk(self, chunk_id: str, store: ChunkStore) -> bytes:
        temporary = store.root / ".downloads" / chunk_id.replace(":", "-")
        self.download_chunk(chunk_id, temporary)
        data = temporary.read_bytes()
        store.put(data, expected_id=chunk_id)
        temporary.unlink()
        return data