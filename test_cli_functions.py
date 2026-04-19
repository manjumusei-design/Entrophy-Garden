import os
import sys
import tempfile
import json
from pathlib import Path
from io import StringIO
from unittest.mock import patch, MagicMock

# Add EntropyGarden to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'EntrophyGarden'))

from entropygarden import (
    cli, ed25519, x25519, key_derive, key_export, image_parser, 
    verify, key_rotation, ssh_format
)

def test_ed25519_keygen():
    """Test ED25519 keypair generation"""
    print("\n" + "="*60)
    print("TEST: ED25519 Keypair Generation")
    print("="*60)
    
    # Seed must be EXACTLY 32 bytes
    seed = bytes(32)  # 32 zero bytes
    sk = ed25519.Ed25519SigningKey(seed)
    
    assert len(sk.seed) == 32
    assert len(sk.public_key) == 32
    
    print(f" Generated ED25519 keypair")
    print(f"  Seed length: {len(sk.seed)} bytes")
    print(f"  Public key length: {len(sk.public_key)} bytes")
    
    return True

def test_x25519_keygen():
    """Test the X25519 keypair generation"""
    print("\n" + "="*60)
    print("TEST: X25519 Keypair Generation")
    print("="*60)
    
    # Must be EXACTLY 32 bytes
    seed = bytes(32)
    pub_key = x25519.generate_public_key(seed)
    
    assert len(seed) == 32
    assert len(pub_key) == 32
    
    print(f" Generated X25519 keypair")
    print(f"  Private key length: {len(seed)} bytes")
    print(f"  Public key length: {len(pub_key)} bytes")
    
    return True

def test_sign_message():
    """Test message signing"""
    print("\n" + "="*60)
    print("TEST: Message Signing")
    print("="*60)
    
    # Must be EXACTLY 32 bytes
    seed = b"A" * 32
    sk = ed25519.Ed25519SigningKey(seed)
    
    message = b"Hello, EntropyGarden!"
    signature = sk.sign(message)
    
    assert len(signature) == 64
    print(f" Signed message successfully")
    print(f"  Message: {message.decode()}")
    print(f"  Signature length: {len(signature)} bytes")
    print(f"  Signature (base64): {__import__('base64').b64encode(signature).decode()[:50]}...")
    
    return True

def test_verify_signature():
    """Test signature verification"""
    print("\n" + "="*60)
    print("TEST: Signature Verification")
    print("="*60)
    
    # Must be EXACTLY 32 bytes
    seed = b"B" * 32
    sk = ed25519.Ed25519SigningKey(seed)
    vk = ed25519.Ed25519VerifyingKey(sk.public_key)
    
    message = b"Test message for verification"
    signature = sk.sign(message)
    
    # Test for valid signature
    result = vk.verify(signature, message)
    assert result is True
    print(f" Valid signature verified successfully")
    
    # Test invalid signature
    result = vk.verify(signature, b"Wrong message")
    assert result is False
    print(f" Invalid signature rejected correctly")
    
    return True

def test_key_rotation():
    """Test key rotation"""
    print("\n" + "="*60)
    print("TEST: Key Rotation")
    print("="*60)
    
    # Must be EXACTLY 32 bytes
    seed = b"C" * 32
    master_key = seed
    
    # Derive keys at different paths
    key1 = key_derive.derive_child(master_key, "m/44'/0'/0'/0'/0'")
    key2 = key_derive.derive_child(master_key, "m/44'/0'/0'/0'/1'")
    
    assert key1 != key2
    assert len(key1) == 32
    assert len(key2) == 32
    
    print(f" Key rotation working")
    print(f"  Key at path m/44'/0'/0'/0'/0': {key1.hex()[:32]}...")
    print(f"  Key at path m/44'/0'/0'/0'/1': {key2.hex()[:32]}...")
    
    return True

def test_hmac_challenge():
    """Test HMAC challenge/response"""
    print("\n" + "="*60)
    print("TEST: HMAC Challenge/Response")
    print("="*60)
    
    # Must be EXACTLY 32 bytes
    key = b"D" * 32
    
    # Generate challenge
    challenge = verify.generate_challenge(key)
    assert "nonce" in challenge
    assert "expected" in challenge
    
    print(f" Generated HMAC challenge")
    print(f"  Nonce: {challenge['nonce'][:20]}...")
    print(f"  Expected: {challenge['expected'][:20]}...")
    
    # Verify correct response
    result = verify.verify_response(key, challenge, challenge["expected"])
    assert result is True
    print(f" Valid HMAC response verified")
    
    # Verify wrong response fails
    result = verify.verify_response(key, challenge, "wrong_response")
    assert result is False
    print(f" Invalid HMAC response rejected")
    
    return True

def test_key_export():
    """Test key export in various formats"""
    print("\n" + "="*60)
    print("TEST: Key Export (PEM, JSON, JWK)")
    print("="*60)
    
    # Must be EXACTLY 32 bytes
    key = b"E" * 32
    meta = {
        "created_at": "2026-04-15T00:00:00Z",
        "algorithm": "sha3_512"
    }
    
    # Test PEM export
    pem = key_export.to_pem(key, "PRIVATE KEY", meta)
    assert "-----BEGIN PRIVATE KEY-----" in pem
    print(f" PEM export successful")
    
    # Test JSON export
    json_data = key_export.to_json(key, meta)
    data = json.loads(json_data)
    assert "key" in data
    assert "checksum" in data
    print(f" JSON export successful")
    
    # Test JWK export
    jwk = key_export.to_jwk(key, meta)
    jwk_data = json.loads(jwk)
    assert jwk_data["kty"] == "oct"
    print(f" JWK export successful")
    
    return True

def test_key_info():
    """Test key information display"""
    print("\n" + "="*60)
    print("TEST: Key Information Display")
    print("="*60)
    
    # Must be EXACTLY 32 bytes
    key = b"F" * 32
    checksum = key_derive.compute_checksum(key)
    
    assert isinstance(checksum, str)
    assert len(checksum) > 0
    print(f" Key checksum computed")
    print(f"  Key: {key.hex()[:32]}...")
    print(f"  Checksum: {checksum}")
    
    return True

def test_image_entropy():
    """Test image entropy extraction"""
    print("\n" + "="*60)
    print("TEST: Image Entropy Extraction")
    print("="*60)
    
    # Create a simple PPM image with proper data
    ppm_data = b"P6\n4 4\n255\n"
    ppm_data += bytes([(i * 7) % 256 for i in range(48)])  # 4x4 RGB = 48 bytes
    
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.ppm', delete=False) as f:
        f.write(ppm_data)
        ppm_file = f.name
    
    try:
        # Test image parsing
        pixels, w, h = image_parser.get_image(ppm_file)
        assert len(pixels) == 48
        assert w == 4
        assert h == 4
        print(f" Image parsed successfully")
        print(f"  File: {ppm_file}")
        print(f"  Dimensions: {w}x{h}")
        print(f"  Pixel data size: {len(pixels)} bytes")
        
        # Test entropy extraction
        entropy = image_parser.extract_entropy(pixels, "sha3_512")
        assert len(entropy) == 64  # SHA3-512 produces 64 bytes
        print(f" Entropy extracted successfully")
        print(f"  Algorithm: sha3_512")
        print(f"  Entropy length: {len(entropy)} bytes")
        
        # Derive master key from entropy
        master_key = key_derive.derive_master(entropy)
        assert len(master_key) == 32
        print(f" Master key derived from entropy")
        print(f"  Master key: {master_key.hex()[:32]}...")
        
        return True
    finally:
        import os
        os.unlink(ppm_file)

def test_ed25519_ssh_export():
    """Test ED25519 to SSH format export"""
    print("\n" + "="*60)
    print("TEST: ED25519 SSH Format Export")
    print("="*60)
    
    # Must be EXACTLY 32 bytes
    seed = b"G" * 32
    sk = ed25519.Ed25519SigningKey(seed)
    
    # Generate SSH public key
    ssh_pub = ssh_format.to_ssh_public_key(sk.public_key, "test_key")
    assert ssh_pub.startswith("ssh-ed25519")
    print(f" SSH public key generated")
    print(f"  Format: {ssh_pub[:40]}...")
    
    # Generate PKCS8 PEM
    pkcs8 = ssh_format.to_pkcs8_pem(seed, sk.public_key)
    assert "-----BEGIN PRIVATE KEY-----" in pkcs8
    print(f" PKCS8 PEM generated")
    
    # Generate Subject Public Key Info PEM
    spki = ssh_format.to_subject_public_key_info_pem(sk.public_key)
    assert "-----BEGIN PUBLIC KEY-----" in spki
    print(f" Subject Public Key Info PEM generated")
    
    return True

def test_x25519_ecdh():
    """Test X25519 ECDH agreement"""
    print("\n" + "="*60)
    print("TEST: X25519 ECDH Key Agreement")
    print("="*60)
    
    # Generate two key pairs that must be EXACTLY 32 bytes each
    alice_priv = b"H" * 32
    bob_priv = b"I" * 32
    
    alice_pub = x25519.generate_public_key(alice_priv)
    bob_pub = x25519.generate_public_key(bob_priv)
    
    # Compute shared secrets
    alice_shared = x25519.compute_shared_secret(alice_priv, bob_pub)
    bob_shared = x25519.compute_shared_secret(bob_priv, alice_pub)
    
    # Shared secrets should match
    assert alice_shared == bob_shared
    assert len(alice_shared) == 32
    
    print(f" X25519 ECDH successful")
    print(f"  Alice public key: {alice_pub.hex()[:32]}...")
    print(f"  Bob public key: {bob_pub.hex()[:32]}...")
    print(f"  Shared secret: {alice_shared.hex()[:32]}...")
    
    return True

def test_cli_key_reading():
    """Test CLI key file reading"""
    print("\n" + "="*60)
    print("TEST: CLI Key File Reading")
    print("="*60)
    
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Must be EXACTLY 32 bytes
        key = b"J" * 32
        
        # Test with PEM format
        pem_content = key_export.to_pem(key, "PRIVATE KEY", {})
        pem_file = os.path.join(tmpdir, "test_pem.key")
        with open(pem_file, "w") as f:
            f.write(pem_content)
        
        read_key = cli._read_key_file(pem_file)
        assert read_key == key
        print(f" PEM format key read successfully")
        
        # Test with JSON format
        json_content = key_export.to_json(key, {})
        json_file = os.path.join(tmpdir, "test_json.json")
        with open(json_file, "w") as f:
            f.write(json_content)
        
        read_key = cli._read_key_file(json_file)
        assert read_key == key
        print(f" JSON format key read successfully")
        
        # Test with JWK format
        jwk_content = key_export.to_jwk(key, {})
        jwk_file = os.path.join(tmpdir, "test_jwk.json")
        with open(jwk_file, "w") as f:
            f.write(jwk_content)
        
        read_key = cli._read_key_file(jwk_file)
        assert read_key == key
        print(f" JWK format key read successfully")
        
        return True

def test_cli_ssh_key_reading():
    """Test CLI SSH format key reading"""
    print("\n" + "="*60)
    print("TEST: CLI SSH Format Key Reading")
    print("="*60)
    
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Must be EXACTLY 32 bytes
        seed = b"K" * 32
        sk = ed25519.Ed25519SigningKey(seed)
        
        # Write SSH public key
        ssh_pub = ssh_format.to_ssh_public_key(sk.public_key, "test")
        ssh_file = os.path.join(tmpdir, "test_ssh.pub")
        with open(ssh_file, "w") as f:
            f.write(ssh_pub)
        
        # Read it back through CLI function
        read_key = cli._read_key_file(ssh_file)
        assert read_key == sk.public_key
        print(f" SSH format key read successfully")
        print(f"  SSH key: {ssh_pub[:50]}...")
        print(f"  Recovered public key: {read_key.hex()[:32]}...")
        
        return True

def main():
    """Run all CLI function tests"""
    print("\n" + "="*60)
    print("ENTROPYGARDEN CLI FUNCTION TESTS")
    print("="*60)
    
    tests = [
        ("ED25519 Keypair Generation", test_ed25519_keygen),
        ("X25519 Keypair Generation", test_x25519_keygen),
        ("Message Signing", test_sign_message),
        ("Signature Verification", test_verify_signature),
        ("Key Rotation", test_key_rotation),
        ("HMAC Challenge/Response", test_hmac_challenge),
        ("Key Export Formats", test_key_export),
        ("Key Information", test_key_info),
        ("Image Entropy Extraction", test_image_entropy),
        ("ED25519 SSH Export", test_ed25519_ssh_export),
        ("X25519 ECDH Agreement", test_x25519_ecdh),
        ("CLI Key File Reading", test_cli_key_reading),
        ("CLI SSH Key Reading", test_cli_ssh_key_reading),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"\n✗ FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed} ")
    print(f"Failed: {failed} ✗")
    print("="*60)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
