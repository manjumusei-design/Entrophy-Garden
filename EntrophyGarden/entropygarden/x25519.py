# x25519.py
"""X25519 diffie hellman key exchange and secret generation

This module has a pure python montgomery ladder implementation that i have coded myself"""


import os

_HAS_CRYPTOGRAPHY = False
try:
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
    _HAS_CRYPTOGRAPHY = True
except ImportError:
    pass


def generate_public_key(private_key: bytes) -> bytes:
    """Generate a x25519 pk from a 32 byte private key"""
    if len(private_key) != 32:
        raise ValueError("Private key must be 32 bytes")

    if _HAS_CRYPTOGRAPHY:
        crypto_priv = X25519PrivateKey.from_private_bytes(private_key)
        return crypto_priv.public_key().public_bytes_raw()

    return _pure_python_public_key(private_key)


def compute_shared_secret(private_key: bytes, peer_public: bytes) -> bytes:
    """Compute a x5519 shared secret which is the DH"""
    if _HAS_CRYPTOGRAPHY:
        crypto_priv = X25519PrivateKey.from_private_bytes(private_key)
        crypto_peer = X25519PublicKey.from_public_bytes(peer_public)
        return crypto_priv.exchange(crypto_peer)

    return _pure_python_shared_secret(private_key, peer_public)


# Python fallback (my invention and intepretation)

def _pure_python_public_key(private_key: bytes) -> bytes:
    """Generate public key using pure-Python Montgomery ladder."""
    from EntrophyGarden.entropygarden import curve25519
    scalar = curve25519.clamp_scalar(private_key)
    u = _montgomery_ladder(scalar, 9)
    return curve25519.encode_int_le(u)


def _pure_python_shared_secret(private_key: bytes, peer_public: bytes) -> bytes:
    """Compute shared secret using the montgomery ladder."""
    from EntrophyGarden.entropygarden import curve25519
    scalar = curve25519.clamp_scalar(private_key)
    u = int.from_bytes(peer_public, "little")
    result = _montgomery_ladder(scalar, u)
    return curve25519.encode_int_le(result)


def _montgomery_ladder(scalar: int, u: int) -> int:
    """Montgomery ladder for X25519 curve where v^2 = U^3 = 486662u^2 + u
    
    Uses only X and Z coordinates then returns the U coordinate"""
    
    
    P = curve25519.P
    A24 = 121666  # (486662 + 2) / 4

    x1 = u
    x2, z2 = 1, 0  # identity point (1:0) in XZ coordinates
    x3, z3 = u, 1  # the point itself

    for i in range(254, -1, -1):
        bit = (scalar >> i) & 1

        # Conditional swap
        if bit:
            x2, x3 = x3, x2
            z2, z3 = z3, z2

        # Ladder step (RFC 7748)
        a = (x2 + z2) % P
        aa = (a * a) % P
        b = (x2 - z2) % P
        bb = (b * b) % P
        e = (aa - bb) % P
        c = (x3 + z3) % P
        d = (x3 - z3) % P
        da = (d * a) % P
        cb = (c * b) % P
        x3 = ((da + cb) * (da + cb)) % P
        z3 = (x1 * (da - cb) * (da - cb)) % P
        x2 = (aa * bb) % P
        z2 = (e * (aa + A24 * e)) % P

        # Conditional swap
        if bit:
            x2, x3 = x3, x2
            z2, z3 = z3, z2

    # Convert to affine coordinate
    zi = pow(z2, P - 2, P)
    return (x2 * zi) % P


# Import curve25519 at the bottom to avoid circular imports during loading and initialization 
from EntrophyGarden.entropygarden import curve25519
