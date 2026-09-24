# Deduplicating Installer

An installer that detects content already on the machine (shared libraries, engines, multimedia assets) and downloads/stores only what is missing, saving disk space, bandwidth, and (via shared files) memory.

**Idea:** split packages into content-addressed chunks -> compare signed manifests against the local store -> fetch only missing chunks -> assemble the install atomically.

## Status
Phase 1: Python prototype (SHA-256, fixed-size chunks, local CAS, staged atomic install).

## Quick start
```bash
pip install pytest
python -m pytest prototype/tests -q
python scripts/demo.py
```

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

## Stack
C++ core - Python prototype - Qt GUI - Zstandard - SHA-256 then BLAKE3 - Ed25519 - JSON manifest - local filesystem CAS - REST/HTTPS repo - PostgreSQL (central).

## Roadmap
See `ISSUES.md` (one milestone per phase).