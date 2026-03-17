from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Optional

PBKDF2_ITERATIONS = 240_000


@dataclass(frozen=True)
class PBKDF2Hash:
    iterations: int
    salt: bytes
    digest: bytes

    def encode(self) -> str:
        salt_b64 = base64.b64encode(self.salt).decode("ascii")
        digest_b64 = base64.b64encode(self.digest).decode("ascii")
        return f"pbkdf2_sha256${self.iterations}${salt_b64}${digest_b64}"


def _pbkdf2(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=32)


def hash_secret(secret: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = _pbkdf2(secret, salt, iterations)
    return PBKDF2Hash(iterations=iterations, salt=salt, digest=digest).encode()


def parse_hash(encoded: str) -> Optional[PBKDF2Hash]:
    try:
        algo, iter_text, salt_b64, digest_b64 = encoded.split("$")
        if algo != "pbkdf2_sha256":
            return None
        return PBKDF2Hash(
            iterations=int(iter_text),
            salt=base64.b64decode(salt_b64.encode("ascii")),
            digest=base64.b64decode(digest_b64.encode("ascii")),
        )
    except Exception:
        return None


def verify_secret(secret: str, encoded: str) -> bool:
    parsed = parse_hash(encoded)
    if not parsed:
        return False
    digest = _pbkdf2(secret, parsed.salt, parsed.iterations)
    return hmac.compare_digest(digest, parsed.digest)


def hash_passcode(passcode: str) -> str:
    return hash_secret(passcode, iterations=180_000)


def verify_passcode(passcode: str, encoded_hash: str) -> bool:
    return verify_secret(passcode, encoded_hash)


def passcode_params(encoded_hash: str) -> dict:
    parsed = parse_hash(encoded_hash)
    if not parsed:
        return {"enabled": False}
    return {
        "enabled": True,
        "iterations": parsed.iterations,
        "salt_b64": base64.b64encode(parsed.salt).decode("ascii"),
        "digest_b64": base64.b64encode(parsed.digest).decode("ascii"),
    }
