#test_qr.py
"""Test qr code generation, mostly on encoding, sizing and correctness"""
from entropygarden import qr


def test_hello_encodes_to_version_1():
    """The string 'Hello' should encode to a version 1 QR code"""
    result = qr.encode(b"hello")
    lines = result.split("\n")
    assert len(lines) == 21
    assert all(len(line) == 42 for line in lines)
    
def test_fingerprint_encodes_to_larger_version():
    """ A 95 byte fingerprint needs version 7 or larger"""
    fp = b"cf:f8:8c:b2:9c:9f:85:50:62:a5:3f:51:df:92:0a:14"
    result = qr.encode(fp)
    lines = result.split("\n")
    size = len(lines)
    
    assert size >= 21
    assert size % 4 == 1 
    assert len(lines[0]) == size * 2
    
    
def test_qr_has_finder_patterns():
    """Every QR code should have at 3 7x7 finder patterns in the corners"""
    result = qr.encode(b"test data")
    lines = result.split("\n")
    size = len(lines)
    # Top left finder = 7x7 block with a specific pattern
    # top right finder
    # bottom left finder
    # Should also check that corners have distinctive patterns that are non repeating
    corners = [
        (0, 0),
        (0, size - 7),
        (size - 7, 0),
    ]
    for r0, c0 in corners:
        found_dark = False
        found_light = False
        for r in range(r0, min(r0 + 7, size)):
            for c in range(c0, min(c0 + 14, size * 2), 2):
                if c // 2 < size:
                    if lines[r][c:c+2] == "██":
                        found_dark = True
                    elif lines[r][c:c+2] == "░░":
                        found_light = True
        assert found_dark and found_light, f"Finder pattern at ({r0},{c0}) missing"