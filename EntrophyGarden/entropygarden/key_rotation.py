# key_rotation.py
"""This is for key path parsing, expiration metadata and key rotation"""
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from EntrophyGarden.entropygarden import key_derive


def parse_path(path: str) -> List[Tuple[int, bool]]:
    """Parse m/44/0/0 into a list of (index, hardened_flag) tuples"""
    parts = path.strip().split("/")
    if parts [0] != "m":
        raise ValueError(f"Path must start with 'm': {path}")
    result = []
    for p in parts[1:]:
        hardened = p.endswith("'")
        idx = int(p.rstrip("'"))
        result.append((idx, hardened))
    return result


def derive_with_expiration(parent: bytes, path: str,
                           expires: str) -> Dict[str, object]:
    """Derive the child key with expiration and creation timestamps"""
    key = key_derive.derive(parent,path)
    now = datetime.now(timezone.utc).isoformat()
    return {
        "key": key,
        "path": path,
        "expires": expires,
        "created_at": now,
        "checksum": key_derive.compute_checksum(key),
    }
    
    
def rotate_key(old_key: bytes, reason: str) -> Dict[str, object]:
    """Derive a new key via hkdf expand and to return the rotation metadata"""
    new_key = key_derive.hkdf_expand(old_key, b"entropygarden:rotate", 32)
    now = datetime.now(timezone.utc).isoformat()
    from EntrophyGarden.entropygarden.cli_output import log
    log(f"Key rotated: {reason}", level="warn", color="yellow")
    return {
        "key": new_key,
        "reason": reason,
        "rotated_at": now,
        "checksum": key_derive.compute_checksum(new_key),
    }
    