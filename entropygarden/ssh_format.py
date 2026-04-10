#ssh_format.py
"""SSH pub key formatting and PEM export for the keys generated in ED25519 keys"""

"""This module provides 'ssh-ed25519 AAAA....' strings and standard PKCS#8 PEM blocks"""

import base64
from typing import Tuple


def _encode_ssh_string(data: bytes) -> bytes:
    """Encode data as a ssh string which is 4 byte length + data"""
    return len(data).to_bytes(4, "big") + data


def to_ssh_public_key(public_key: bytes, comment: str = "") -> str:
    """Format and produce a 32 byte ed25519 public key as an ssh public key string
    
    Returns: 'shh-ed25519 AAAA ... [COMMENT}'
    """
    if len(public_key) != 32:
        raise ValueError("Ed25519 public key must be 32 bytes")
    blob = _encode_ssh_string(b"ssh-ed25519") + _encode_ssh_string(public_key)
    b64 = base64.b64encode(blob).decode()
    if comment:
        return f"ssh-ed25519 {b64} {comment}"
    return f"ssh-ed25519 {b64}"


# Minimal ASN 1 DER encoding for PKCS 8 format


def _der_length(length: int) -> bytes:
    """Encode a DER length field."""
    if length < 0x80:
        return bytes([length])
    elif length < 0x100:
        return bytes([0x81, length])
    else:
        return bytes([0x82, length >> 8, length & 0xFF])
    
    
def _der_sequence(contents: bytes) -> bytes:
    """Wrap contents in a der sequence"""
    return b"\x30" + _der_length(len(contents)) + contents


def _der_octet_string(data: bytes) -> bytes:
    """Encode as DER OCTET STRING."""
    return b"\x04" + _der_length(len(data)) + data


def _der_bit_string(data: bytes) -> bytes:
    """Encode as DER BIT STRING (0 unused bits prefix)."""
    inner = b"\x00" + data
    return b"\x03" + _der_length(len(inner)) + inner


def _der_integer(value: int) -> bytes:
    """ Encode as DER INTEGER"""
    if value == 0:
        return b"\x02\x01\x00"
    enc = b""
    v = value
    while v > 0:
        enc = bytes([v & 0xFF]) + enc
        v >>= 8
    if enc[0] & 0x80:
        enc = b"\x00" + enc
    return b"\x02" + _der_length(len(enc)) + enc


def _der_oid(oid_bytes: bytes) -> bytes:
    """Encode as der object identifier."""
    return b"\x06" + _der_length(len(oid_bytes)) + oid_bytes


# Ed25519 OID: 1.3.101.112 -> DER: 2b 65 70
_ED25519_OID = bytes([0x2B, 0x65, 0x70])


def to_pkcs8_pem(seed : bytes, public_key: bytes = None) -> str:
    """Export ed25519 pk as pkcs8 PEM where
    
    Seed is the 32 byte private key seed
    public key is a 32 byte encoded public key and is optional"""
    
    if len(seed) != 32:
        raise ValueError("Seed must be 32 bytes")
    
    # Algorithm identifier 
    alg_id = _der_sequence(_der_oid(_ED25519_OID))
    
    if public_key:
        #pkcs8 v1 with public key
        priv_key_octet = _der_octet_string(seed)
        pub_key_bits = _der_bit_string(b"\x00" + public_key)
        inner = (
            _der_integer(0)
            + alg_id
            + _der_octet_string(priv_key_octet)
            + _der_bit_string(public_key)
        )
        
        
        
        inner = _der_integer(0) + alg_id + _der_octet_string(seed)
    else:
        inner = _der_integer(0) + alg_id + _der_octet_string(seed)
        
    der = _der_sequence(inner)
    b64 = base64.b64encode(der).decode()
    lines = [b64[i:i + 64] for i in range(0, len(b64), 64)]
    return (
        "-----BEGIN PRIVATE KEY-----\n"
        + "\n".join(lines)
        + "\n-----END PRIVATE KEY-----"
    )
    

def to_subject_public_key_info_pem(public_key: bytes) -> str:
    """Export ed22519 pubkey as SubjetPublicKeyInfo PEM"""
    if len(public_key) != 32:
        raise ValueError("Public key must be 32 bytes")
    
    alg_id = _der_sequence(_der_oid(_ED25519_OID))
    spki = _der_sequence(alg_id + _der_bit_string(public_key))
    b64 = base64.b64encode(spki).decode()
    lines = [b64[i:i + 64] for i in range(0, len(b64), 64)]
    return (
        "-----BEGIN PUBLIC KEY-----\n"
        + "\n".join(lines)
        + "\n-----END PUBLIC KEY-----"
    )