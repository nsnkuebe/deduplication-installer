# ADR 0003: Local database
**Status:** OPEN - decide before Phase 3

**Options:** (a) SQLite embedded (no server, single file, crash-safe with WAL). (b) MySQL (as originally listed; needs a running server on every machine).

**Notes:** All SQL goes through one data-access layer so the choice can change. Central repository DB is PostgreSQL either way.
