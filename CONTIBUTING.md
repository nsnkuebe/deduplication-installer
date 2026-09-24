# Contributing
- `main` is protected: open a pull request, CI must pass.
- Branch names: `feat/...`, `fix/...`, `docs/...`.
- Commit messages: imperative, reference the issue (`Add fixed chunker (#12)`).
- If you change hashing, chunking, or the manifest: update `docs/manifest-spec.md`, regenerate `spec/test-vectors/`, and make sure both implementations agree.
- Never commit private keys, `.db` files, or local stores.
