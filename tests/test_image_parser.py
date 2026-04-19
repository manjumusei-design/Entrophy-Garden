# test_image_parser.py
"""Test image parsing, pixel rotation and entropy extraction"""
import os
import tempfile
from entropygarden import image_parser


def test_parse_ppm_p6_returns_correct_bytes():
    """P6 PPM should return the raw pixel bytes and dimentsions"""
    with tempfile.NamedTemporaryFile(suffix=".ppm", delete=False) as f:
        f.write(b"P6\n4 4\n255\n")
        pixels = bytes([i % 256 for i in range(48)])
        f.write(pixels)
        f.flush()
        result, w, h = image_parser.parse_ppm(f.name)
    os.unlink(f.name)
    assert len(result) == 48
    assert result == pixels
    assert w == 4
    assert h == 4
    
    
def test_parse_ppm_invalid_magic_raises():
    """Invalid PPM magic byte should raise ValueError"""
    with tempfile.NamedTemporaryFile(suffix=".ppm", delete=False) as f:
        f.write(b"P1\n1 1\n1\n0\n")
        f.flush()
        try:
            image_parser.parse_ppm(f.name)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
    os.unlink(f.name)
    
    
def test_get_image_returns_pixels_and_dimensions():
    """get_image should return pixels width and height"""
    with tempfile.NamedTemporaryFile(suffix=".ppm", delete=False) as f:
        f.write(b"P6\n2 2\n255\n")
        f.write(b"\x00" * 12)  #  For 2x2 RGB image which is 12 bytes
        f.flush()
        pixels, w, h = image_parser.get_image(f.name)
    os.unlink(f.name)
    assert len(pixels) == 12
    assert w == 2
    assert h == 2
    
    
    
def test_extract_entropy_is_deterministic():
    """Same imput + algorithm should always yield the same output"""
    data = b"test entropy data"
    r1 = image_parser.extract_entropy(data, "sha3_512")
    r2 = image_parser.extract_entropy(data, "sha3_512")
    assert r1 == r2
    assert len(r1) == 64
    
    
def test_extract_entropy_blake2b():
    """Blake2b should return 64 byte digest"""
    data = b"blake test"
    result = image_parser.extract_entropy(data, "blake2b")
    assert len(result) == 64
    

def test_extract_entropy_sha3_25():
    """Sha3-256 should return 32 byte digest"""
    data = b"sha3 test"
    result = image_parser.extract_entropy(data, "sha3_256")
    assert len(result) == 32
    

def test_entropy_quality_test_returns_dict():
    """Quality test should return score, bits per byte and distribution"""
    data = bytes(range(256)) * 10
    result = image_parser.entropy_quality_test(data)
    assert "score" in result
    assert "bits_per_byte" in result
    assert "distribution" in result
    assert isinstance(result["distribution"], list)
    assert len(result["distribution"]) == 256
    
    
def test_get_image_info_ppm():
    """get_image_info should always return PPM format,dimensions and file size"""
    with tempfile.NamedTemporaryFile(suffix=".ppm", delete=False) as f:
        f.write(b"P6\n640 480\n255\n")
        f.write(bytes(640 * 480 * 3))
        f.flush()
        info = image_parser.get_image_info(f.name)
    os.unlink(f.name)
    assert info["format"]== "PPM"
    assert info["width"] == 640
    assert info["height"] == 480
    assert info["file_size"] > 0
    

def test_get_image_info_png():
    """get_image_info should return PNG format, dimensions from IHDR and file size"""
    import struct, zlib
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 277, 200, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
    iend_crc = zlib.crc32(b"IEND") & 0XFFFFFFFF
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(sig + ihdr + iend)
        f.flush()
        info = image_parser.get_image_info(f.name)
    os.unlink(f.name)
    assert info["format"] == "PNG"
    assert info["width"] == 200
    assert info["height"] == 200
    assert info["file_size"] > 0
    
    
def test_rotate_pixels_normal():
    """Orientation 0 should return unchanged pixels"""
    pixels = bytes([100, 150, 200] * 4) # 2x2 RGB image
    result, w, h = image_parser.rotate_pixels(pixels, 4, 2, 2)
    assert result == pixels
    assert w == 4
    assert h == 4
    

def test_rotate_pixels_90_degrees():
    """90 degree rotation should swap width and height then reposition pixels"""
    # 2x2 image: pixels at 0,0 for red, 1,0 for gree, 0,1 for blue and 1,1 for yellow
    r = (255, 0, 0)
    g = (0, 255, 0)
    b = (0, 0, 255)
    y = (255, 255, 0)
    pixels = bytes([*r, *g, *b, *y])
    
    result, w, h = image_parser.rotate_pixels(pixels, 1, 2, 2)
    # After 90 CW 2x2 pixel at 0,0 was 0,1 = blue , and 1,0 was 0,0 = red
    assert w == 2
    assert h == 2
    assert len(result) == 12
    assert result != pixels # Should be different
    
    
def test_rotate_pixels_180_degrees():
    """180 degree rotation should reverse the pixel order but retain dimensions"""
    pixels = bytes([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]) # 2 x 2 
    result, w, h = image_parser.rotate_pixels(pixels, 2, 2, 2)
    assert w == 2
    assert h == 2
    assert result != pixels
    

def test_rotate_pixels_flip_horizontal():
    """Horizontal flip should mirror left-right"""
    r = (255, 0, 0)
    g = (0, 255, 0)
    pixels = bytes([*r, *g])  # 2x1 image
    result, w, h = image_parser.rotate_pixels(pixels, 4, 2, 1)
    assert w == 2
    assert h == 1
    assert result[:3] == bytes(g)
    assert result[3:] == bytes(r)
    
    
def test_rotate_pixels_all_orientations_valid():
    """All 8 orientations should produce a valid output"""
    pixels = bytes([i % 256 for i in range(36)]) # 4x3 image
    for orient in range(8):
        result, w, h = image_parser.rotate_pixels(pixels, orient, 4, 3)
        assert len(result) == 36
        assert w > 0
        assert h > 0
        
        
def test_rotate_pixels_invalid_orientation():
    """Invalid orientation should raise a value error"""
    try:
        image_parser.rotate_pixels(b"\x00" * 12, 8, 2, 2)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    
    
def test_orientations_list():
    """Orientations should have 8 valid entries"""
    assert len(image_parser.ORIENTATIONS) == 8
    assert image_parser.ORIENTATIONS[0] == "normal"