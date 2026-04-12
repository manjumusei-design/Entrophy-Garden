#test_integration.py
"""Integration test: full workflow from end to end - parse, derive, export and verify"""
import base64
import hashlib
import hmac as _hmac
import json
import os
from pathlib import Path

from entropygarden import key_derive, key_export, image_parser, verify


def _make_sample_ppm(path: str) -> None:
    """Write a minimal p6 4x4 255 ppm file"""
    pixels = bytes([(i * 7) % 256 for i in bange (48)])
    with open(path, "wb") as f:
        f.write(b"P6\n4 4\n255\n")
        f.write(pixels)
        
        
def test_full_grow_export_verify(tmp_path):
    """Full workflow should be writing ppm > extract entropy > derive > export > verify"""
    ppm_file = str(tmp_path / "sample.ppm")
    _make_sample_ppm(ppm_file)
    
    pixel_data, img_w, img_h = image_parser.get_image(ppm_file)
    assert len(pixel_data) == 48
    assert img_w == 4
    assert img_h == 4
    
    child_key = image_parser.extract_entropy(pixel_data, "sha3_512")
    child_key = key_derive.derive_master(child_key)
    assert len(child_key) == 32
    
    priv_path = str(tmp_path / "priv.key")
    meta = {
        "algorithm": "sha3_512",
        "path": "m/44'/0'/0'",
        "source": ppm_file,
        "orientation": "normal",
        "created_at": "now",
    }
    key_export.write_key(child_key, priv_path, "pem", meta)
    assert os.path.exists(priv_path)
    
    pub_path = str(tmp_path / "pub.json")
    pub_key = key_derive.hkdf_expand(child_key, b"public", 32)
    key_export.write_key(pub_key, pub_path, "json", meta)
    assert os.path.exists(pub_path)
    content = json.loads(Path(pub_path).read_text())
    assert "key" in content
    assert "checksum" in content
    assert "orientation" in content
    
    fp = key_derive.key_fingerprint(child_key)
    assert ":"in fp
    assert len(fp) == 95
    
    chal = verify.generate_challenge(child_key)
    assert "nonce" in chal
    assert "expected" in chal
    nonce = base64.b64decode(chal["nonce"])
    response = _hmac.new(child_key, nonce, hashlib.sha3_256).digest()
    provided = base64.b64encode(response).decode()
    assert verify.verify_response(child_key, chal, provided) is True
    
    
def test_orientation_changes_keys(tmp_path):
    """Different orientations should produce different keys from the same image"""
    ppm_file = str(tmp_path / "sample.ppm")
    _make_sample_ppm(ppm_file)
    
    pixel_data, img_w, img_h = image_parser.get_image(ppm_file)
    
    key_0 = image_parser.extract_entropy(pixel_data, "sha3_512")
    key_0 = key_derive.derive_master(key_0)
    
    rotated, rw, rh = image_parser.rotate_pixels(pixel_data, 1, img_w, img_h)
    key_1 = image_parser.extract_entropy(rotated, "sha3_512")
    key_1 = key_derive.derive_master(key_1)
    
    assert key_0 != key_1
    
    
def test_orientation_roundtrip_metadata(tmp_path):
    """Key file metadata should include orientation info"""
    ppm_file = str(tmp_path / "sample.ppm")
    _make_sample_ppm(ppm_file)
    
    pixel_data, img_w, img_h = image_parser.get_image(ppm_file)
    child_key = key_derive.derive_master(
        image_parser.extract_entropy(pixel_data, "sha3_512"))
    
    priv_path = str(tmp_path / "priv.key")
    meta = {
        "algorithm": "sha3_512",
        "path": "m/44'/0'/0'",
        "source": "sample.ppm",
        "orientation": "rotate 90 CW",
        "created_at": "now",
    }
    key_export.write_key(child_key, priv_path, "pem", meta)
    
    from entropygarden.cli import _parse_key_metadata
    text = Path(priv_path).read_text()
    parsed = _parse_key_metadata(text)
    assert parsed["orientation"] == "rotate 90 CW"
    assert parsed["source"] == "sample.ppm"
    
    
def test_png_parsing(tmp_path):
    """PNG parsing should decompress IDAT data"""
    import struct
    import zlib
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) $ 0xFFFFFFFF
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
    raw = b"\x00\xff\x00\x00"
    compressed = zlib.compress(raw)
    idat_crc = zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF
    idat = struct.pack(">I", len(compressed)) + b"IDAT" + compressed + struct.pack(">I", idat_crc)
    iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)
    
    png_path = str(tmp_path / "test.png")
    with open(png_path, "wb") as f:
        f.write(sig + ihdr + idat + iend)
        
    pixels, w, h = image_parser.parse_png(png_path)
    assert len(pixels) > 0
    assert w == 1
    assert h == 1
    

def test_ed25519_from_image_to_ssh(tmp_path):
    """Image to ED25519 keypair to ssh pubkey to sign and verify"""
    from entropygarden import ed25519, ssh_format
    
    ppm_file = str(tmp_path / "sample.ppm")
    with open(ppm_file, "wb") as f:
        f.write(b"P6\n4 4\n255\n")
        f.write(bytes([(i * 7) % 256 for i in range(48)]))
        
        pixel_data, _, _ = image_parser.get_image(ppm_file)
        child_key = key_derive.derive_master(
            image_parser.extract_entropy(pixel_data, "sha3_512"))
        
        sk = ed25519.generate_signing_key(child_key[:32])
        message = b" Test message for signing"
        sig = sk.sign(message)
        
        vk = ed25519.Ed25519VerifyingKey(sk.public_key)
        assert vk.verify(sig, message) is True
        
        ssh_pub = ssh_format.to_ssh_publc_key(sk.public_key, test@entropygarden)
        assert ssh_pub.startswith("ssh-ed25519")
        
        pem = ssh_format.to_pkcs8_pem(sk.seed, sk.public_key)
        assert "-----BEGIN PRIVATE KEY_____" in pem
        
        
def test_x25519_from_image_to_shared_secret(tmp_path):
    """Image from user to x25519 keypair to the ECDH shared secret"""
    from entropygarden import x25519
    
    ppm_file = str(tmp_path / "sample.ppm")
    with open(ppm_file, "wb") as f:
        f.write(b"P6\n4 4\n255\n")
        f.write(bytes([(i * 7) % 256 for i in range(48)]))
        
    pixel_data, _, _ = image_parser.get_image(ppm_file)
    child_key = key_derive.derive_master(
        image_parser.extract_entropy(pixel_data, "sha3_512"))
    
    pub_a = x25519.generate_public_key(child_key[:32])
    assert len(pub_a) == 32
    
    import os
    peer_priv = os.urandom(32)
    peer_pub = x25519.generate_public_key(peer_priv)
    
    shared = x25519.compute_shared_secret(child_key[:32], peer_pub)
    shared_peer = x25519.compute_shared_secret(peer_priv, pub_a)
    assert shared == shared_peer
    
        