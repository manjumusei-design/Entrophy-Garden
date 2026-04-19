import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any

DEFAULTS: Dict[str, Any] = {
    "algorithm": "sha3_512",
    "animation": False,
    "format" : "pem",
    "quiet": False,
    "theme": "default",
}

VALID_ALGORITHMS = ("sha3_512", "blake2b", "sha3_256")


def load(path: str = "~/.entropygarden/config.json") -> Dict[str, Any]:
    cfg = dict(DEFAULTS)
    p = Path(path).expanduser()
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                user = json.load(f)
            cfg.update({k: v for k, v in user.items() if k in DEFAULTS})
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save(config: Dict[str, Any], path: str) -> None:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix =".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(config, f, indent =2)
        os.replace(tmp, str(p))
    except OSError as e:
        from entropygarden.whisper import error_msg
        error_msg(str(e))
        raise SystemExit(1)
    