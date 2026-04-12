#test_render.py
"""Test rendering for image to ascii , raw bytes and hex dump"""
from entropygarden import render


def test_detect_terminal_returns_dict():
    """Terminal detection should return with the width height and colours"""
    result = render.detect_terminal()
    assert "width" in result
    assert "height" in result
    assert "colors" in result
    assert isinstance(result["width"], int)
    
    
def test_map_to_glyph_returns_single_char():
    """Each byte value should map to exacty one glypth character"""
    for val in [0, 64, 128, 192, 255]:
        g = render.map_to_glyph(val)
        assert len(g) == 1
        assert g in render.GLYPHS
        
        
def test_render_image_as_ascii_returns_list_of_strings():
    """render_image_as_ascii should return list of strings"""
    #4x2 RGB image (8 pixels and 24 bytes)
    pixels = bytes([i % 256 for i in range(24)])
    result = render.render_image_as_ascii(pixels, 4, 2, 20, 2)
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(line, str) for line in result)
    
    
def test_render_image_as_ascii_respects_height():
    """render_image_as_ascii should not exceed the requested height"""
    pixels = bytes([128] * 300)
    result = render.render_image_as_ascii(pixels, 10, 10, 20, 3)
    assert len(result) <= 3
    
    
def test_render_image_as_ascii_different_brightness():
    """Dark pixels should map to lighter glyphs, bright to darker"""
    # All black image or pixels
    black = bytes([0] * 36)
    black_result = render.render_image_as_ascii(black, 6, 2, 6, 2)
    # All white image or pixels
    white = bytes([255] * 36)
    white_result = render.render_image_as_ascii(white, 6, 2, 6, 2)
    # The test result should be both different
    assert black_result != white_result


def test_render_raw_bytes_returns_list_of_strings():
    """render_raw_bytes should return a list of string"""
    data = bytes(range(64))
    result = render.render_raw_bytes(data, 8, 8)
    assert isinstance(result, list)
    assert len(result) == 8
    assert all(len(line) == 8 for line in result)
    
    
def test_render_heatmap_returns_list_of_strings():
    """Heatmap rendring should return a list of ANSI coloured strings"""
    data = bytes(range(64))
    result = render.render_heatmap(data, 8, 4)
    assert isinstance(result, list)
    assert len(result) == 4
    assert all(isinstance(line, str) for line in result)
    
    
def test_hex_dump_returns_formatted_lines():
    """Hex dump should return formatted hex + ascii lines"""
    data = bytes(range(32))
    result = render.hex_dump(data)
    assert len(result) == 2
    assert "00000000" in result[0]
    assert "|" in result[0]
    
    
    