# cli_output.py

import sys
from typing import Optional

COLORS = {
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "cyan": "\033[36m",
    "reset": "\033[0m",
    "dim": "\033[2m",
    "bold": "\033[1m",
}

_quiet = False


def set_quiet(val: bool) -> None:
    """Enable or disable quiet mode"""
    global _quiet
    _quiet = val
    

def is_quiet() -> bool:
    """Return whether quiet mode is active"""
    return _quiet


def log(msg: str, level: str = "info", color: Optional[str] = None) -> None:
    """Print a colored log message to stderr. Suppressed in quiet mode."""
    if _quiet:
        return
    c = COLORS.get(color or ("green" if level == "info" else "yellow"), "")
    r = COLORS["reset"]
    prefix = "[INFO]" if level == "info" else "[WARN]"
    print(f"{c}{prefix} {msg}{r}", file=sys.stderr)
    
    
def error_msg(msg: str) -> None:
    """Print an error message to stderr and exit"""
    if _quiet:
        return
    r = COLORS["reset"]
    print(f"{COLORS['red']}[ERROR] {msg}{r}", file=sys.stderr)
    
    
def format_error(exc: Exception) -> str:
    """Format an exception as a clean error message"""
    return f"{type(exc).__name__}:{exc}"


def human_size(n: int) -> str:
    """Format byte count as human-readable string (B, KB, MB, GB)."""
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    if n < 1024 ** 3:
        return f"{n / 1024 ** 2:.1f} MB"
    return f"{n / 1024 ** 3:.1f} GB"


def print_banner() -> None:
    """Print the application banner"""
    if _quiet:
        return
    art = (
        "  +------------------------------+\n"
        "  |  Entropy Garden v1.0.0       |\n"
        "  |  Cryptographic key derivation |\n"
        "  |  from image entropy           |\n"
        "  +------------------------------+"
    )
    print(f"\n{COLORS['cyan']}{art}{COLORS['reset']}")
    
    
def print_complete(checksum: str) -> None:
    """Print a completion message with the key checksum"""
    if _quiet:
        return
    print(f"\n{COLORS['green']}Checksum: {checksum}{COLORS['reset']}")