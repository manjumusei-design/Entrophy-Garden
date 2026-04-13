#test_verify.py
"""Test verify module : challenge generation and response verification"""
import base64
import hashlib
import hmac as _hmac

from entropygarden import verify


def test_generate_challenge_returns_dict():
    """challenge should contain nonce and expected"""
    key = b"test key for challenge"
    result = verify.generate_challenge(key)
    assert "nonce" in result
    assert "expected" in result
    assert isinstance(result["nonce"], str)
    assert isinstance(result["expected"], str)
    
    
def test_generate_challenge_is_random():
    """Each challenge should have a unique nonce"""
    key = b"test key"
    c1 = verify.generate_challenge(key)
    c2 = verify.generate_challenge(key)
    assert c1["nonce"] != c2["nonce"]
    
    
def test_verify_response_true_with_correct_answer():
    """Correct response should pass the verification"""
    key = b"test key"
    chal = verify.generate_challenge(key)
    nonce = base64.b64decode(chal["nonce"])
    response = _hmac.new(key, nonce, hashlib.sha3_256).digest()
    provided = base64.b64encode(response).decode()
    assert verify.verify_response(key, chal, provided) is True
    
    
def test_verify_response_false_with_wrong_answer():
    """Wrong response should fail the verification duh """
    key = b"test key"
    chal = verify.generate_challenge(key)
    assert verify.verify_response(key, chal, "d3JvbmdhbnN3ZXI=") is False
    