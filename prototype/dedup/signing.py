import base64
import copy

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey

from .manifest import canonical_bytes


def generate_keypair() -> tuple[bytes, bytes]:
    key = SigningKey.generate()
    return bytes(key), bytes(key.verify_key)


def _unsigned_manifest(manifest: dict) -> dict:
    unsigned = copy.deepcopy(manifest)
    unsigned.pop("signature", None)
    return unsigned


def sign_manifest(manifest: dict, private_key: bytes, key_id: str = "default") -> dict:
    signed = _unsigned_manifest(manifest)
    signature = SigningKey(private_key).sign(canonical_bytes(signed)).signature
    signed["signature"] = {
        "algorithm": "ed25519",
        "key_id": key_id,
        "value": base64.b64encode(signature).decode("ascii"),
    }
    return signed


def verify_manifest(manifest: dict, public_key: bytes) -> bool:
    signature = manifest.get("signature")
    if not isinstance(signature, dict) or signature.get("algorithm") != "ed25519":
        return False
    try:
        value = base64.b64decode(signature["value"], validate=True)
        VerifyKey(public_key).verify(canonical_bytes(_unsigned_manifest(manifest)), value)
    except (KeyError, ValueError, TypeError, BadSignatureError):
        return False
    return True