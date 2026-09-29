"""Reference implementation of the deduplicating installer prototype."""

from .localdb import Database, LocalDB, LocalDatabase

__all__ = ["Database", "LocalDB", "LocalDatabase"]
