"""Demo: install two apps that share a library, show the savings.
Run from repo root: python scripts/demo.py"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prototype"))
from dedup.cas import ChunkStore
from dedup.chunker import FixedChunker
from dedup.installer import install, plan
from dedup.manifest import publish_dir

with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    lib = bytes(range(256)) * 4096            # 1 MB shared engine
    for n in "ab":
        (t / n).mkdir()
        (t / n / "engine.bin").write_bytes(lib)
        (t / n / f"{n}.dat").write_bytes(f"unique to {n}".encode() * 1000)
    repo, local = ChunkStore(t / "repo"), ChunkStore(t / "local")
    ch = FixedChunker(64 * 1024)
    ma, mb = (publish_dir(t / n, f"app{n}", "1.0", repo, ch) for n in "ab")
    for m in (ma, mb):
        p = plan(m, local)
        print(f"{m['name']}: total {p['total_bytes']:,} B, download {p['download_bytes']:,} B, saved {p['saved_bytes']:,} B")
        install(m, local, t / f"inst_{m['name']}", fetch=repo.get)
