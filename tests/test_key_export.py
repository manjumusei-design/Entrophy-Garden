#test_key_export.py
"""Test key export in PEM, JSOn, JWK, BINARY and QR formats"""
import base64
import json
import os
import tempfile
from entropygarden import key_export, key_derive


def test_to_pem_returns_valid_block():
    """PEM output should have BEGIN/END markers and base64 content"""
    key = b"a" * 32
    meta = {"path": "m/44'/0'/0'", "algorithm": "sha3_512"}
    result = key_export.to_pem(key, "PRIVATE KEY", meta)
    assert "-----BEGIN PRIVATE KEY-----" in result
    assert "-----END PRIVATE KEY-----" in result
    
    
def test_to_pem_includes_orientation():
    """PEM output should include orientation when provided in metadata"""
    key = b"b" * 32
    meta = {"path": "m/44'/0'/0'", "orientation": "rotate 90 CW", "source": "test.png"}
    result = key_export.to_pem(key, "PRIVATE KEY", meta)
    assert "# Orientation: rotate 90 CW" in result
    assert "# Source: test.png" in result
    
    
def test_to_json_returns_valid_json():
    """ Json output should be valid and contain the fields of the key"""
    key = b"c" * 32
    meta = {"path": "m/44'/0'/0'"}
    result = key_export.to_json(key, meta)
    data = json.loads(result)
    assert "key" in data
    assert "checksum" in data
    assert "created_at" in data
    
    
def test_to_jwk_returns_valid_jwk():
    """JWK output should be a valid JSON"""
    key = b"d" * 32
    meta = {"path": "m/44'/0'/0'", "source": "test.png"}
    result = key_export.to_jwk(key, meta)
    data = json.loads(result)
    assert data["kty"] == "oct"
    assert "k" in data
    assert data["alg"] == "HS512"
    assert "key_ops" in data
    
    
def test_to_jwk_base64url_encoding():
    """JWK k field should use base64url encoding without padding"""
    key = b"e" * 32
    meta = {}
    result = key_export.to_jwk(key, meta)
    data = json.loads(result)
    assert "=" not in data["k"]
    padded = data["k"] + "=" * (4 - len(data["k"]) % 4)
    decoded = base64.urlsafe_b64decode(padded)
    assert decoded == key
    
    
def test_write_key_json(tmp_path):
    """Wrie_key should be creating a JWK file at the given path"""
    key = b"g" * 32
    path = str(tmp_path / "test.jwk")
    key_export.write_key(key, path, "jwk", {"path": "m/44'/0'/0'"})
    assert os.path.exists(path)
    data = json.loads(open(path).read())
    assert data["kty"] == "oct"
    
    
def test_write_key_unknown_format_raises():
    """Write_key should raise ValueError for unknown formats"""
    try:
        key_export.write_key(b"x", "/dev/null", "xml", {})
        assert False, "Should have raised ValueError"
    except ValueError:
        pass 


def test_write_key_ssh(tmp_path):
    """SSH export should write a valid OpenSSH public key."""
    from entropygarden import ed25519

    seed = b"s" * 32
    public_key = ed25519.Ed25519SigningKey(seed).public_key
    path = str(tmp_path / "test_ssh.pub")
    key_export.write_key(public_key, path, "ssh", {"comment": "test"})
    content = open(path, encoding="utf-8").read().strip()
    assert content.startswith("ssh-ed25519 ")


def test_to_qr_png_returns_valid_png():
    """QR PNG export shouldd return a PNG byte stream without extra dependencies."""
    from entropygarden import image_parser

    png = key_export.to_qr_png("hello world")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(png)
        f.flush()
        pixels, w, h = image_parser.parse_png(f.name)
    os.unlink(f.name)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert w > 0
    assert h > 0
    assert len(pixels) > 0
