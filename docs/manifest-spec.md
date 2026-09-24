# Manifest specification (format 1, DRAFT)

The single source of truth that the Python prototype and the C++ core must both follow.

## Fields
| Field | Meaning |
|---|---|
| `format` | Integer. Readers MUST refuse formats they do not understand. |
| `name`, `version` | Package identity. `(name, version)` is immutable once published. |
| `hash_algo` | Algorithm used for `file_hash` (`sha256` now, `b3` later). |
| `chunker` | `{ "type": "fixed", "size": N }` now; `{ "type": "fastcdc", "min", "avg", "max" }` later. |
| `files[]` | `path`, `type`, `size`, `file_hash`, `chunks[]` (`hash`, `off`, `len`). |
| `total_size` | Sum of file sizes. |

## Rules
1. **Hash IDs are algorithm-tagged**: `sha256:<lowercase hex>`. Never mix algorithms within one file's chunk list.
2. **Paths** are relative, use `/`, and MUST NOT be absolute or contain `..`. Reject on read.
3. **Canonical bytes**: UTF-8 JSON, sorted keys, no whitespace (`separators=(",", ":")`). The signature covers those exact bytes; verify the same bytes, never a re-serialisation.
4. **Chunk hash** is over the *uncompressed* chunk bytes. Compression is a storage detail.
5. Files are sorted by `path` so identical inputs give identical manifests.

## Verification order (client)
signature -> manifest fields/paths -> each chunk hash on arrival -> assembled `file_hash`.

## Later
- `dependencies`, `install_scripts`, symlinks, modes
- multimedia `media.streams`
- CBOR encoding as format 2