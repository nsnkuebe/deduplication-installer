# Deduplicating Installer

An installer that detects content already on the machine (shared libraries, engines, multimedia assets) and downloads/stores only what is missing, saving disk space, bandwidth, and (via shared files) memory.

**Idea:** split packages into content-addressed chunks -> compare signed manifests against the local store -> fetch only missing chunks -> assemble the install atomically.

## Status
Phase 3 / M3 complete: local database, refcounts, garbage collection, and recovery journaling are now in the prototype.

## Quick start
```powershell
py -m pip install -r requirements.txt
py -m pytest prototype/tests -q
py scripts/demo.py
```

> Verified on Python 3.13 in this workspace.

## Layout
| Path | Purpose |
|---|---|
| `docs/` | Architecture, manifest spec, decision records |
| `spec/test-vectors/` | Shared known-answer tests for every implementation |
| `prototype/` | Python reference implementation |
| `core/` | C++ library (`libdedup`) |
| `cli/`, `gui/` | Command-line and Qt front-ends |
| `repo-server/` | REST/HTTPS repository API (PostgreSQL) |
| `schema/` | SQL migrations |

## Tech Stack
| Technology | Role |
|---|---|
| C++ | Core library (`libdedup`) |
| Python | Reference prototype and tooling |
| Qt | Desktop GUI |
| Zstandard | Per-chunk compression |
| SHA-256 | Current content hashing algorithm |
| BLAKE3 | Planned future hashing algorithm |
| Ed25519 | Manifest and index signing |
| JSON | Manifest and index format |
| Local filesystem CAS | Content-addressed local storage |
| REST/HTTPS | Repository transport |
| PostgreSQL | Central repository database |

## Roadmap
See `ISSUES.md` (one milestone per phase).