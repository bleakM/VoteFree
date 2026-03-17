from __future__ import annotations

import base64
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class VoteCryptoError(Exception):
    pass


class VoteCrypto:
    """Hybrid encryption for .vote files: RSA-OAEP + AES-256-GCM."""

    def __init__(self, keys_dir: Path):
        self.keys_dir = keys_dir
        self.private_key_path = keys_dir / "admin_private.pem"
        self.public_key_path = keys_dir / "admin_public.pem"
        self._private_key = None
        self._public_key = None

    def keys_exist(self) -> bool:
        return self.private_key_path.exists() and self.public_key_path.exists()

    def generate_keys(self, admin_password: str) -> None:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        public_key = private_key.public_key()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(admin_password.encode("utf-8")),
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self.private_key_path.write_bytes(private_pem)
        self.public_key_path.write_bytes(public_pem)
        self._private_key = private_key
        self._public_key = public_key

    def load_public_key(self):
        if self._public_key is None:
            if not self.public_key_path.exists():
                raise VoteCryptoError("Public key file not found.")
            self._public_key = serialization.load_pem_public_key(self.public_key_path.read_bytes())
        return self._public_key

    def unlock_private_key(self, admin_password: str) -> None:
        if not self.private_key_path.exists():
            raise VoteCryptoError("Private key file not found.")
        try:
            self._private_key = serialization.load_pem_private_key(
                self.private_key_path.read_bytes(),
                password=admin_password.encode("utf-8"),
            )
        except Exception as exc:  # noqa: BLE001
            raise VoteCryptoError("Invalid administrator password.") from exc

    def lock_private_key(self) -> None:
        self._private_key = None

    @property
    def unlocked(self) -> bool:
        return self._private_key is not None

    def reprotect_private_key(self, new_password: str) -> None:
        if not self._private_key:
            raise VoteCryptoError("Private key is locked.")
        private_pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(new_password.encode("utf-8")),
        )
        self.private_key_path.write_bytes(private_pem)

    def public_key_spki_b64(self) -> str:
        public_key = self.load_public_key()
        der = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return base64.b64encode(der).decode("ascii")

    def _build_envelope(self, payload: Dict[str, Any], source: str) -> Dict[str, Any]:
        public_key = self.load_public_key()
        aes_key = secrets.token_bytes(32)
        nonce = secrets.token_bytes(12)
        aad = b"VoteFree-v1"
        plaintext = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ciphertext = AESGCM(aes_key).encrypt(nonce, plaintext, aad)
        encrypted_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return {
            "version": 1,
            "algorithm": "RSA-OAEP-3072+AES-256-GCM",
            "source": source,
            "created_at": utc_now(),
            "aad_b64": base64.b64encode(aad).decode("ascii"),
            "encrypted_key_b64": base64.b64encode(encrypted_key).decode("ascii"),
            "nonce_b64": base64.b64encode(nonce).decode("ascii"),
            "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        }

    def encrypt_payload(self, payload: Dict[str, Any], source: str = "lan") -> Dict[str, Any]:
        return self._build_envelope(payload, source=source)

    def decrypt_envelope(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        if not self._private_key:
            raise VoteCryptoError("Private key is locked.")
        try:
            encrypted_key = base64.b64decode(envelope["encrypted_key_b64"])
            nonce = base64.b64decode(envelope["nonce_b64"])
            ciphertext = base64.b64decode(envelope["ciphertext_b64"])
            aad = base64.b64decode(envelope.get("aad_b64", ""))
        except Exception as exc:  # noqa: BLE001
            raise VoteCryptoError("Invalid vote envelope format.") from exc

        try:
            aes_key = self._private_key.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            plaintext = AESGCM(aes_key).decrypt(nonce, ciphertext, aad)
            payload = json.loads(plaintext.decode("utf-8"))
            if not isinstance(payload, dict):
                raise VoteCryptoError("Vote payload is not an object.")
            return payload
        except VoteCryptoError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise VoteCryptoError("Failed to decrypt vote file.") from exc

    def save_vote_file(self, envelope: Dict[str, Any], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_vote_file(self, vote_path: Path) -> Dict[str, Any]:
        try:
            return json.loads(vote_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise VoteCryptoError("Failed to load vote file.") from exc

    def decrypt_vote_file(self, vote_path: Path) -> Dict[str, Any]:
        envelope = self.load_vote_file(vote_path)
        return self.decrypt_envelope(envelope)
