"""ED25519 digital signatures that uses the cryptography library when available but also has a pure python implementation for 
failback usage which is my own implementation of the ed25519 DS"""

import hashlib
import os

_HAS_CRYPTOGRAPHY = False
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    _HAS_CRYPTOGRAPHY = True
except ImportError:
    pass


class Ed25519SigningKey:
    def __init__(self, seed: bytes):
        if len(seed) !=32:
            raise ValueError("Seed must be 32 bytes")
        self._seed = seed
        
        if _HAS_CRYPTOGRAPHY:
            self._crypto_key = Ed25519PrivateKey.from_private_bytes(seed)
            self._public_key_bytes = self._crypto_key.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
        else:
            self._public_key_bytes = _pure_python_public_key(seed)
            
    @classmethod
    def from_seed(cls, seed: bytes) -> "Ed25519SigningKey":
        if len(seed) == 32:
            return cls(seed)
        return cls(hashlib.sha256(seed).digest())
    
    @property
    def seed(self) -> bytes:
        return self._seed
    
    @property
    def public_key(self) -> bytes:
        return self._public_key_bytes
    
    def sign(self, message: bytes) -> bytes:
        if _HAS_CRYPTOGRAPHY:
            return self._crypto_key.sign(message)
        return _pure_python_sign(self.seed, message)
    
    def to_bytes(self) -> bytes:
        return self._seed
    
    
class Ed25519VerifyingKey:
    def __init__(self, public_key: bytes):
        if len(public_key) != 32: 
            raise ValueError("Public key must be 32 bytes")
        self._public_key = public_key
        if _HAS_CRYPTOGRAPHY:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            self._crypto_key = Ed25519PublicKey.from_public_bytes(public_key)
            
    def verify(self, signature: bytes, message: bytes) -> bool:
        if len(signature) != 64:
            return False
        if _HAS_CRYPTOGRAPHY:
            try:
                self._crypto_key.verify(signature, message)
                return True
            except Exception:
                return False
        return _pure_python_verify(self._public_key, signature, message)
    
    def to_bytes(self) -> bytes:
        return self._public_key
    
    
def generate_signing_key(seed: bytes = None) -> Ed25519SigningKey:
    if seed is None:
        seed = os.urandom(32)
    return Ed25519SigningKey(seed)


# Pure Python fallback implementation (my invention and interpretation)

def _pure_python_public_key(seed:bytes) -> bytes:
    from . import curve25519
    h = hashlib.sha512(seed).digest()
    scalar = curve25519.clamp_scalar(h[:32])
    pk_point = curve25519.scalar_mult(scalar,curve25519.B)
    return curve25519.point_to_bytes(pk_point)
    

def _pure_python_sign(seed: bytes, message: bytes) -> bytes:
    from . import curve25519
    h = hashlib.sha512(seed).digest()
    scalar = curve25519.clamp_scalar(h[:32])
    prefix = h[32:]
    pk_point = curve25519.scalar_mult(scalar, curve25519.B)
    pk_bytes = curve25519.point_to_bytes(pk_point)
    r = int.from_bytes(hashlib.sha512(prefix + message).digest(), "little") % curve25519.L
    R = curve25519.scalar_mult(r, curve25519.B)
    R_bytes = curve25519.point_to_bytes(R)
    k = int.from_bytes(
        hashlib.sha512(R_bytes + pk_bytes + message).digest(), "little"
    ) % curve25519.L
    S = (r + k * scalar) % curve25519.L
    return R_bytes + curve25519.encode_int_le(S)


def _pure_python_verify(public_key: bytes, signature: bytes, message: bytes) -> bool:
    from . import curve25519
    try:
        A = curve25519.bytes_to_point(public_key)
    except ValueError:
        return False
    R_bytes = signature[:32]
    S = int.from_bytes(signature[32:], "little")
    if S >= curve25519.L:
        return False
    try:
        R = curve25519.bytes_to_point(R_bytes)
    except ValueError:
        return False
    k = int.from_bytes(
        hashlib.sha512(R_bytes+ public_key + message).digest(), "little"
    ) % curve25519.L
    lhs = curve25519.scalar_mult((8 * S) % curve25519.L, curve25519.B)
    rhs = curve25519.point_add(
        curve25519.scalar_mult(8, R),
        curve25519.scalar_mult((8 *k) % curve25519.L, A)
    )
    return curve25519.point_to_bytes(lhs) == curve25519.point_to_bytes(rhs)
