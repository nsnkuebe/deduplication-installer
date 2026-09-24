# ADR 0001: SHA-256 first, BLAKE3 later
**Status:** accepted

**Decision:** Use SHA-256 for v1. All IDs are algorithm-tagged (`sha256:...`, `b3:...`).

**Why:** SHA-256 is available everywhere (OpenSSL, Python stdlib), which keeps the prototype and C++ core easy to cross-check. BLAKE3 is faster and can come once the pipeline works.

**Consequences:** Changing the algorithm changes chunk IDs, so tagging is mandatory now. Migration means adding `b3:` objects beside existing ones.
