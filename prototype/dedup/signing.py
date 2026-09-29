import base64
import copy
from datetime import datetime, timezone

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey

from .manifest import canonical_bytes


def generate_keypair() -> tuple[bytes, bytes]:
    key = SigningKey.generate()
    return bytes(key), bytes(key.verify_key)


def _unsigned_payload(payload: dict) -> dict:
    unsigned = copy.deepcopy(payload)
    unsigned.pop("signature", None)
    return unsigned


def _parse_datetime(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("invalid datetime")
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def sign_payload(payload: dict, private_key: bytes, key_id: str = "default", *, expires: str | None = None) -> dict:
    signed = _unsigned_payload(payload)
    if expires is not None:
        signed["expires"] = expires
    signature = SigningKey(private_key).sign(canonical_bytes(signed)).signature
    signed["signature"] = {
        "algorithm": "ed25519",
        "key_id": key_id,
        "value": base64.b64encode(signature).decode("ascii"),
    }
    return signed


def sign_manifest(manifest: dict, private_key: bytes, key_id: str = "default") -> dict:
    return sign_payload(manifest, private_key, key_id)


def sign_index(index: dict, private_key: bytes, key_id: str = "default", *, expires: str | None = None) -> dict:
    return sign_payload(index, private_key, key_id, expires=expires)


def verify_payload(payload: dict, public_key: bytes) -> bool:
    signature = payload.get("signature")
    if not isinstance(signature, dict) or signature.get("algorithm") != "ed25519":
        return False
    try:
        value = base64.b64decode(signature["value"], validate=True)
        VerifyKey(public_key).verify(canonical_bytes(_unsigned_payload(payload)), value)
    except (KeyError, ValueError, TypeError, BadSignatureError):
        return False
    return True


def verify_manifest(manifest: dict, public_key: bytes) -> bool:
    return verify_payload(manifest, public_key)


def verify_index(index: dict, public_key: bytes, *, now: datetime | None = None) -> bool:
    if not verify_payload(index, public_key):
        return False
    expires = index.get("expires")
    if expires is None:
        return True
    try:
        expires_at = _parse_datetime(expires)
    except ValueError:
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now < expires_at
