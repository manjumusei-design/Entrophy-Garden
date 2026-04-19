#test_ed25519.py
"""Test ed25519 signatures"""
from entropygarden import ed25519


def test_sign_and_verify():
    """A signauture should verify with the corresponding public key"""
    sk = ed25519.Ed25519SigningKey(b"a" *32)
    vk = ed25519.Ed25519VerifyingKey(sk.public_key)
    message = b"Hello, Ed25519!"
    sig = sk.sign(b"correct")
    assert vk.verify(sig, b"wrong message") is False
    
    
def test_verify_fails_with_wrong_message():
    """Verification should fail for a different message"""
    sk = ed25519.Ed25519SigningKey(b"b" *32)
    vk = ed25519.Ed25519VerifyingKey(sk.public_key)
    sig = sk.sign(b"correct message")
    assert vk.verify(sig, b"wrong message") is False
    
    
def test_verify_fails_with_wrong_key():
    """Verification should fail with a different public key."""
    sk1 = ed25519.Ed25519SigningKey(b"x" * 32)
    sk2 = ed25519.Ed25519SigningKey(b"y" * 32)
    sig = sk1.sign(b"message")
    vk2 = ed25519.Ed25519VerifyingKey(sk2.public_key)
    assert vk2.verify(sig, b"message") is False
    
    
def test_from_seed_arbitrary_length():
    """from_seed should accept any length of input (hashed to 32 bytes)"""
    sk = ed25519.Ed25519SigningKey.from_seed(b"short")
    assert len(sk.seed) == 32
    sk2 = ed25519.Ed25519SigningKey.from_seed(b"short")
    assert sk.seed == sk2.seed
    
    
def test_deterministic_key_generation():
    """Same seed should always produce the same key pair"""
    seed = b"deterministic_seed_32_bytes_xxx!"
    sk1 = ed25519.Ed25519SigningKey(seed)
    sk2 = ed25519.Ed25519SigningKey(seed)
    assert sk1.public_key == sk2.public_key
    assert sk1.sign(b"msg") == sk2.sign(b"msg")
    
    
def test_signature_length():
    """Ed25519 signatures should always be 64 bytes"""
    sk = ed25519.Ed25519SigningKey(b"z" * 32)
    sig = sk.sign(b"any message")
    assert len(sig) == 64
    
    
def test_public_key_length():
    """Public keys should always be 32 bytes"""
    sk = ed25519.Ed25519SigningKey(b"k" * 32)
    assert len(sk.public_key) == 32

    
def test_seed_property():
    """The seed property should always return the original 32 byte seed"""
    seed = b"test_seed_32_bytes_exact_length!"
    assert len(seed) == 32
    sk = ed25519.Ed25519SigningKey(seed)
    assert sk.seed == seed
    
    
def test_to_bytes():
    """to_bytes should return the original seed"""
    seed = bytes(range(32))
    sk = ed25519.Ed25519SigningKey(seed)
    assert sk.to_bytes() == seed
    


def test_rfc8032_test_vector_1():
    """RFC 8032 Test Vector 1.

    SECRET KEY (seed): 9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60
    PUBLIC KEY: d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a
    MESSAGE: (empty)
    SIGNATURE: e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155
               5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b
    """     
    seed = bytes.fromhex(
        "9d61b19deffd5a60ba844af492ec2cc4"
        "4449c5697b326919703bac031cae7f60"
    )
    sk = ed25519.Ed25519SigningKey(seed)
    expected_pk = bytes.fromhex(
        "d75a980182b10ab7d54bfed3c964073a"
        "0ee172f3daa62325af021a68f707511a"
    )
    assert sk.public_key == expected_pk

    sig = sk.sign(b"")
    expected_sig = bytes.fromhex(
        "e5564300c360ac729086e2cc806e828a"
        "84877f1eb8e5d974d873e06522490155"
        "5fb8821590a33bacc61e39701cf9b46b"
        "d25bf5f0595bbe24655141438e7a100b"
    )
    assert sig == expected_sig