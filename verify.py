#verify.py
"""HMAC Challenge/response key verification"""
import base64
import hashlib
import hmac
import os
from typing import Dict


def generate_challenge(key: bytes) -> Dict [str,str]:
    """Generate a hmac sha3 256 challenge with a random nonce"""
    nonce = os.urandom(16)
    response = hmac.new(key, nonce, hashlib.sha3_256).digest()
    return {
        "nonce": base64.b64encode(nonce).decode(),
        "expected": base64.b64encode(response).decode(),
    }
    
    
def verify_response(key: bytes, challenge: Dict[str, str],
                    provided: str) -> bool:
    """Constant time verify of a challenge response that returns true or false"""
    nonce = base64.b64decode(challenge["nonce"])
    expected = hmac.new(key, nonce, hashlib.sha3_256).digest()
    try:
        provided_bytes = base64.b64decode(provided)
    except Exception:
        return False
    return hmac.compare_digest(expected, provided_bytes)
