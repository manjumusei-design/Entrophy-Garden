from datetime import datetime, timezone
from typing import Dict, List, Tuple

from . import key_derive


def parse_path(path: str) -> List[Tuple[int, bool]]:
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
    key = key_derive.derive_child(parent, path)
    now = datetime.now(timezone.utc).isoformat()
    return {
        "key": key,
        "path": path,
        "expires": expires,
        "created_at": now,
        "checksum": key_derive.compute_checksum(key),
    }
    
    
def rotate_key(old_key: bytes, reason: str) -> Dict[str, object]:
    new_key = key_derive.hkdf_expand(old_key, b"entropygarden:rotate", 32)
    now = datetime.now(timezone.utc).isoformat()
    from .cli_output import log
    log(f"Key rotated: {reason}", level="warn", color="yellow")
    return {
        "key": new_key,
        "reason": reason,
        "rotated_at": now,
        "checksum": key_derive.compute_checksum(new_key),
    }
    