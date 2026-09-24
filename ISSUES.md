# Milestones and issues

## M1 - Python prototype
- Algorithm-tagged hashing (SHA-256) *(done)*
- Fixed-size chunker behind `Chunker` interface *(done)*
- Local CAS with atomic, verified writes *(done)*
- Manifest build + canonical bytes *(done)*
- Plan (missing chunks) + staged atomic install *(done)*
- Per-chunk Zstandard compression in the CAS (skip if it does not shrink)
- Whole-file dedup via hardlinks when materialising
- Measure: bytes downloaded vs naive install, dedup ratio

## M2 - Signing and repository
- Ed25519 signing and verification of canonical manifest bytes
- Static HTTPS repo layout (index, manifests, chunks) and download client with resume
- Path-traversal and symlink-escape tests
- Signed index with expiry (rollback protection)

## M3 - Database, refcounts, GC
- Decide local DB (ADR 0003) and write schema + migrations
- Refcounts for file objects and chunks, uninstall
- Mark-and-sweep GC with grace period
- Transaction journal and crash-recovery tests

## M4 - C++ core
- Port hashing, chunker, CAS, manifest to C++ against `spec/test-vectors`
- Cross-check job: Python vs C++ output must match
- CLI: install, remove, verify, gc, stats

## M5 - Front-ends and server
- Qt GUI (worker thread; progress, savings preview)
- REST API + PostgreSQL central index and publisher upload

## M6 - Advanced
- BLAKE3 support (`b3:` IDs)
- FastCDC chunker and comparison against fixed-size
- Dependency resolver
- Updates: manifest diff, generations, rollback
- Multimedia: whole-file dedup, container demuxing, structural chunk boundaries