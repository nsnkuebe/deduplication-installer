import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from dedup.cas import ChunkStore, HashMismatch
from dedup.chunker import FixedChunker
from dedup.hashing import hash_bytes
from dedup.installer import install, plan
from dedup.manifest import canonical_bytes, publish_dir
from dedup.repository import RepositoryClient, StaticRepository
from dedup.signing import generate_keypair, sign_manifest, verify_manifest

VECTORS = Path(__file__).resolve().parents[2] / "spec" / "test-vectors" / "sha256.json"


def test_hash_vectors():
    for v in json.loads(VECTORS.read_text())["vectors"]:
        assert hash_bytes(v["input"].encode()) == v["sha256"]


def test_fixed_chunker_covers_data():
    data = b"x" * 1000
    parts = FixedChunker(300).split(data)
    assert parts == [(0, 300), (300, 300), (600, 300), (900, 100)]


def test_cas_dedups_and_rejects_bad_hash(tmp_path):
    s = ChunkStore(tmp_path / "s")
    cid, new1 = s.put(b"hello")
    _, new2 = s.put(b"hello")
    assert new1 and not new2
    with pytest.raises(HashMismatch):
        s.put(b"hello", expected_id=hash_bytes(b"other"))


def test_cas_compresses_when_compression_shrinks(tmp_path):
    s = ChunkStore(tmp_path / "s")
    chunk_id, _ = s.put(b"a" * 10000)
    digest = chunk_id.split(":", 1)[1]
    assert (tmp_path / "s" / "sha256" / digest[:2] / (digest[2:] + ".zst")).exists()
    assert s.get(chunk_id) == b"a" * 10000


def _make_pkg(root: Path, files: dict):
    for rel, data in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)


def test_shared_content_is_not_downloaded_twice(tmp_path):
    shared = bytes(range(256)) * 1024          # 256 KB library both apps ship
    a, b = tmp_path / "a", tmp_path / "b"
    _make_pkg(a, {"lib/engine.bin": shared, "a.txt": b"app A"})
    _make_pkg(b, {"lib/engine.bin": shared, "b.txt": b"app B is different"})

    repo = ChunkStore(tmp_path / "repo")
    ch = FixedChunker(64 * 1024)
    ma = publish_dir(a, "appA", "1.0", repo, ch)
    mb = publish_dir(b, "appB", "1.0", repo, ch)

    local = ChunkStore(tmp_path / "local")
    install(ma, local, tmp_path / "inst_a", fetch=repo.get)
    p = plan(mb, local)
    assert p["download_bytes"] < mb["total_size"] * 0.05   # only b.txt is new
    install(mb, local, tmp_path / "inst_b", fetch=repo.get)
    assert (tmp_path / "inst_b" / "lib/engine.bin").read_bytes() == shared


def test_identical_files_are_hardlinked(tmp_path):
    src = tmp_path / "src"
    _make_pkg(src, {"a.bin": b"same", "b.bin": b"same"})
    repo = ChunkStore(tmp_path / "repo")
    manifest = publish_dir(src, "p", "1", repo, FixedChunker(64))
    destination = tmp_path / "install"
    install(manifest, repo, destination, fetch=repo.get)
    assert (destination / "a.bin").stat().st_ino == (destination / "b.bin").stat().st_ino


def test_corrupt_chunk_from_repo_is_rejected(tmp_path):
    src = tmp_path / "src"
    _make_pkg(src, {"f.bin": b"payload" * 100})
    repo = ChunkStore(tmp_path / "repo")
    m = publish_dir(src, "p", "1", repo, FixedChunker(64))
    local = ChunkStore(tmp_path / "local")
    with pytest.raises(HashMismatch):
        install(m, local, tmp_path / "inst", fetch=lambda cid: b"tampered")
    assert not (tmp_path / "inst").exists()                 # nothing half-installed
    assert not (tmp_path / "inst.staging").exists()


def test_manifest_bytes_are_deterministic(tmp_path):
    src = tmp_path / "src"
    _make_pkg(src, {"z.txt": b"1", "a.txt": b"2"})
    r = ChunkStore(tmp_path / "r")
    m1 = publish_dir(src, "p", "1", r, FixedChunker(64))
    m2 = publish_dir(src, "p", "1", r, FixedChunker(64))
    assert canonical_bytes(m1) == canonical_bytes(m2)


def test_manifest_signature_detects_tampering():
    private_key, public_key = generate_keypair()
    manifest = {"format": 1, "name": "p", "version": "1"}
    signed = sign_manifest(manifest, private_key)
    assert verify_manifest(signed, public_key)
    signed["version"] = "2"
    assert not verify_manifest(signed, public_key)


def test_static_repository_publishes_and_client_downloads(tmp_path):
    src = tmp_path / "src"
    _make_pkg(src, {"app.bin": b"repository payload"})
    store = ChunkStore(tmp_path / "store")
    manifest = publish_dir(src, "app", "1", store, FixedChunker(64))
    repository = tmp_path / "repo"
    StaticRepository(repository).publish(manifest, store)

    client = RepositoryClient(repository.as_uri())
    assert client.get_index() == {"packages": {"app": ["1"]}}
    downloaded_manifest = client.get_manifest("app", "1")
    chunk_id = downloaded_manifest["files"][0]["chunks"][0]["hash"]
    destination = tmp_path / "chunk"
    client.download_chunk(chunk_id, destination)
    assert destination.read_bytes() == b"repository payload"


def test_repository_client_resumes_http_download(tmp_path):
    payload = b"0123456789" * 100
    chunk_id = hash_bytes(payload)
    root = tmp_path / "repo"
    chunk_path = root / "chunks" / "sha256" / chunk_id.split(":", 1)[1][:2] / chunk_id.split(":", 1)[1][2:]
    chunk_path.parent.mkdir(parents=True)
    chunk_path.write_bytes(payload)
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.headers.get("Range"))
            start = int(self.headers["Range"].split("=", 1)[1][:-1]) if self.headers.get("Range") else 0
            body = payload[start:]
            self.send_response(206 if start else 200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        destination = tmp_path / "partial"
        destination.write_bytes(payload[:37])
        RepositoryClient(f"http://127.0.0.1:{server.server_port}/").download_chunk(chunk_id, destination)
        assert destination.read_bytes() == payload
        assert requests == ["bytes=37-"]
    finally:
        server.shutdown()
        thread.join()
