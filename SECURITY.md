# Security
- Private signing keys stay off GitHub. Commit public keys only. If a key is ever committed, treat it as compromised and rotate it.
- Report vulnerabilities privately (GitHub Security Advisories), not in public issues.
- Design rules: re-hash every chunk on receipt, verify signature before trusting any hash, reject path traversal, keep store objects read-only.

