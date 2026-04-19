import hashlib
import hmac as _hmac
from typing import List, Tuple


def derive_master(seed: bytes) -> bytes:
    return hashlib.sha3_256(seed + b"entropygarden:master").digest()


def _parse_path(path: str) -> List[Tuple[int, bool]]:
    parts = path.strip().split("/")
    if parts[0] != "m":
        raise ValueError(f"Path must start with 'm', got: {path}")
    result = []
    for p in parts [1:]:
        hardened = p.endswith("'")
        idx = int(p.rstrip("'"))
        if hardened:
            idx |= 0x80000000
        result.append((idx, hardened))
    return result


def derive_child(parent: bytes, path: str) -> bytes:
    indices = _parse_path(path)
    current = parent
    for idx, _ in indices:
        child_bytes = idx.to_bytes(4, "big")
        current = _hmac.new(
            current, current + b"\x00" + child_bytes, hashlib.sha256
        ).digest()
    return current[:32]


def hkdf_expand(seed: bytes, info: bytes, length: int) -> bytes:
    """HKDF expand via iterative hmac sha 3 256"""
    n = (length + 31) // 32
    okm = b""
    t_prev = b""
    for i in range(1, n + 1):
        t_prev = _hmac.new(
            seed, t_prev + info + bytes([i]), hashlib.sha3_256
        ).digest()
        okm += t_prev
    return okm[:length]


def compute_checksum(key: bytes) -> str:
    return hashlib.sha3_256(key).hexdigest()[:8]


def key_fingerprint(key: bytes) -> str:
    h = hashlib.sha3_256(key).hexdigest()
    return ":".join(h[i:i + 2] for i in range(0, len(h), 2))
