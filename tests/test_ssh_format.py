#test_ssh_format.py
"""Test SSH pubkey formatting and PKCS#8 PEM exports for keys"""
import base64
from entropygarden import ssh_format


def test_ssh_public_key_format():
    """SSH ed25519 public key should start with SSH ed25510 and base64 encoded blob"""
    pub_key = bytes([0x3d, 0x40, 0x17, 0xc3] + [0] * 28)
    result = ssh_format.to_ssh_public_key(pub_key, "test@example.com")
    parts = result.split()
    assert parts[0] == "ssh-ed25519"
    #The blob should decode to the correct SSH string format
    blob = base64.b64decode(parts[1])
    #SSH string is a 4 byte length + "ssh-ed25519"
    assert blob[4:15] == b"ssh-ed25519"
    assert parts[2] == "test@example.com"
    
    
def test_ssh_public_key_no_comment():
    """SSH pubkey without comment should have only 2 parts"""
    pub_key = bytes([0x3d] * 32)
    result = ssh_format.to_ssh_public_key(pub_key)
    parts = result.split()
    assert len(parts) == 2
    assert parts[0] == "ssh-ed25519"
    
    
def test_pkcs8_pem_format():
    """PKCS#8 PEM should have a begin and end private key header and footer"""
    seed = bytes(32)
    result = ssh_format.to_pkcs8_pem(seed)
    assert "-----BEGIN PRIVATE KEY-----" in result
    assert "-----END PRIVATE KEY-----" in result
    
    
def test_subject_public_key_info_pem():
    """SubjectPublicKeyInfo PEM should have begin and end public key markers"""
    pub_key = bytes([0x3d] * 32)
    result = ssh_format.to_subject_public_key_info_pem(pub_key)
    assert "-----BEGIN PUBLIC KEY-----" in result
    assert "-----END PUBLIC KEY-----" in result
    
    
def test_pkcs8_invalid_seed_length():
    """PKCS#8 export should reject non 32 byte seeds""" 
    try:
        ssh_format.to_pkcs8_pem(bytes(16))
        assert False, "Should have raise ValueError"
    except ValueError:
        pass
    