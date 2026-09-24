# ADR 0002: Fixed-size chunking first, CDC later
**Status:** accepted

**Decision:** Start with fixed 64 KiB chunks behind a `Chunker` interface. Add FastCDC later.

**Why:** Simple, easy to test, and whole-file dedup already gives real savings. Fixed chunks are weak when bytes are inserted, which gives a measurable baseline for the CDC comparison.

**Consequences:** Packages built with different chunkers do not share chunk hashes. The manifest records the chunker, and a repo should not mix chunkers for the same package family.
