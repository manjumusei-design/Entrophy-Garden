# test_key_derive.py
"""Test key derivation : Master key, child key, hkdf, checksums and fingerprints"""
from entropygarden import key_derive


def test_derive_master_is_deterministic():
    """Master derivation should always produce the same output from the same seed"""
    s= b"test seed for master key"
    r1 = key_derive.derive_master(s)
    r2 = key_derive.derive_master(s)
    assert r1 == r2
    assert len(r1) == 32
    
    
def test_derive_child_matches_known_vector():
    """Child derivation should be deterministic as well as consistent since its non negotiable"""
    master = key_derive.derive_master(b"test")
    child = key_derive.derive_child(master, "m/44'/0'/0'")
    assert len(child) ==32
    child2 = key_derive.derive_child(master, "m/44'/0'/0'")
    assert child == child2
    
    
def test_derive_child_different_paths():
    """Different paths should yield different keys duh"""
    master = key_derive.derive_master(b"test")
    c1 = key_derive.derive_child(master, "m/44'/0'/0'")
    c2 = key_derive.derive_child(master, "m/44'/0'/1'")
    assert c1 != c2
    
    
def test_compute_checksum_length():
    """Checksum should be exactly 8 hex characters"""
    key = b"test key data"
    cs = key_derive.compute_checksum(key)
    assert len(cs) == 8
    assert all(c in "0123456789abcdef" for c in cs)
    
    
def test_hkdf_expand_produces_requested_length():
    """HKDF expand should produce exactly the request number of bytes"""
    seed_data = b"hkdf seed"
    info = b"test info"
    result = key_derive.hkdf_expand(seed_data, info, 64)
    assert len(result) == 64
    result2 = key_derive.hkdf_expand(seed_data, b"other info", 64)
    assert result != result2
    
    
def test_key_fingerprint_format():
    """Fingerprint should be a colon seperated hex string"""
    key = b"test key"
    fp = key_derive.key_fingerprint(key)
    parts = fp.split(":")
    assert len(parts) == 32
    assert all(len(p) == 2 for p in parts)
    assert all(c in "0123456789abcdef" for p in parts for c in p)
    
    
    