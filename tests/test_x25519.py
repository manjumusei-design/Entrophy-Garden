#test_x25519.py
""" Test the x25519 key exchange"""
import os
from entropygarden import x25519


def test_ecdh_symmetric():
    """ECDH should produce the same shared secret for both parties"""
    alice_priv = os.urandom(32)
    bob_priv = os.urandom(32)
    alice_pub = x25519.generate_public_key(alice_priv)
    bob_pub = x25519.generate_public_key(bob_priv)
    shared_ab = x25519.compute_shared_secret(alice_priv, bob_pub)
    shared_ba = x25519.compute_shared_secret(bob_priv, alice_pub)
    assert shared_ab == shared_ba
    
    
def test_public_key_length():
    """X25519 public keys should be 32 bytes"""
    priv = os.urandom(32)
    pub= x25519.generate_public_key(priv)
    assert len(pub) == 32
    
    
def test_shared_secret_length():
    """X25519 shared secrets should be 32 bytes"""
    alice_priv = os.urandom(32)
    bob_priv = os.urandom(32)
    bob_pub = x25519.generate_public_key(bob_priv)
    secret = x25519.compute_shared_secret(alice_priv, bob_pub)
    assert len(secret) == 32
    
    
def test_invalid_private_key_length():
    """Should raise ValueError for non 32 byte private key"""
    try:
        x25519.generate_public_key(b"short")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    
    
def test_deterministic_public_key():
    """Same private key should always produce the same public key"""
    priv = os.urandom(32)
    pub1 = x25519.generate_public_key(priv)
    pub2 = x25519.generate_public_key(priv)
    assert pub1 == pub2
    
    
def test_different_keys_different_public():
    """Different private keys should produce different public keys"""
    pub1 = x25519.generate_public_key(b"a" * 32)
    pub2 = x25519.generate_public_key(b"b" * 32)
    assert pub1 != pub2
    
    
# Test Vector1
def test_rfc7748_ecdh_test_vector_1():
    """Test vector 1 where 
        alice_private = 77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a
    alice_public  = 8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a
    bob_private   = 5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb
    bob_public    = de9edb7d7b7dc1b4d35b61c2ece435373f8343c85b78674dadfc7e146f882b4f
    shared_secret = 4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742
    """
    
    alice_priv = bytes.fromhex(
        "77076d0a7318a57d3c16c17251b26645"
        "df4c2f87ebc0992ab177fba51db92c2a"
    )
    alice_pub_expected = bytes.fromhex(
        "8520f0098930a754748b7ddcb43ef75a"
        "0dbf3a0d26381af4eba4a98eaa9b4e6a"
    )
    bob_priv = bytes.fromhex(
        "5dab087e624a8a4b79e17f8b83800ee6"
        "6f3bb1292618b6fd1c2f8b27ff88e0eb"
    )
    bob_pub_expected = bytes.fromhex(
        "de9edb7d7b7dc1b4d35b61c2ece43537"
        "3f8343c85b78674dadfc7e146f882b4f"
    )
    shared_expected = bytes.fromhex(
        "4a5d9d5ba4ce2de1728e3bf480350f25"
        "e07e21c947d19e3376f09b3c1e161742" 
    )
    
    assert x25519.generate_public_key(alice_priv) == alice_pub_expected
    assert x25519.generate_public_key(bob_priv) == bob_pub_expected
    shared = x25519.compute_shared_secret(alice_priv, bob_pub_expected)
    assert shared == shared_expected 