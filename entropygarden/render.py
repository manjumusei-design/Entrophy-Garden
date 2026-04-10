#render.py
"""ASCII/ANSI visualization and image rendering"""
import os
import subprocess
from typing import Dict, List

# Gradient
GLYPHS = " .:-=+*#%@"
HEAT_COLORS = [
    "\033[32m", "\033[32m", "\033[92m", "\033[93m",
    "\033[33m", "\033[93m", "\033[31m", "\033[91m",
]
RESET = "\033[0m"


def detect_terminal() -> Dict[str, int]:
    """Detect the terminal size as well as colour support"""
    try:
        cols, rows = os.get_terminal_size()
    except OSError:
        cols, rows = 80, 24
    colors = 256
    try:
        r = subprocess.run(["tput", "colors"], capture_output=True,
                           text=True, timeout =5)
        colors = int(r.stdout.strip()) if r.returncode == 0 else 256
    except (OSError, ValueError, FileNotFoundError):
        pass
    return {"width": cols, "height": rows, "colors": colors}


def map_to_glyph(value: int) -> str:
    """Map a byte value from 0 to 255 to an ASCII glyph by density"""
    idx = min(len(GLYPHS) - 1, value * len(GLYPHS) // 256)
    return GLYPHS[idx]


def render_image_as_ascii(pixel_data: bytes, img_w: int, img_h: int,
                          term_w: int, term_h: int) -> List[str]:
    """Render raw pixel data as ASCII art that resembles the image"""
    """The way I did this is by downsampling the image to the terminal grid by averaging 
the pixel blocks, camputing the luminance, and mapping to glyphs. Characters are roughly twice
as tall as wide so we account for that in the aspect ratio"""


# Account for character aspect ratio (2:1)
    effective_h = term_h
    effective_w = term_w * 2 
    
    # Pixel block size
    block_w = max(1, img_w // effective_w)
    block_h = max(1, img_h // effective_h)
    
    lines = []
    for gy in range(effective_h):
        line = ""
        for gx in range(term_w):
            # Average the pixels in this block
            r_sum, g_sum, b_sum = 0, 0, 0
            count = 0
            for dy in range(block_h):
                py = gy * block_h + dy
                if py >= img_h:
                    break
                for dx in range(block_w * 2):  
                    px = gx * block_w * 2 + dx
                    if px >= img_w:
                        break
                    idx = (py * img_w + px) * 3
                    r_sum += pixel_data[idx]
                    g_sum += pixel_data[idx + 1]
                    b_sum += pixel_data[idx + 2]
                    count += 1
            if count > 0:

                lum = int(0.299 * (r_sum / count) +
                          0.587 * (g_sum / count) +
                          0.114 * (b_sum / count))
                # Invert: dark pixels get space, bright get @
                line += map_to_glyph(255 - lum)
            else:
                line += " "
        lines.append(line)
    return lines[:term_h]


def render_raw_bytes(data: bytes, width: int, height: int) -> List[str]:
    """Render raw bytes as ASCII art for non image data"""
    lines = []
    tiles = (data * ((width * height) // len(data) +1))[:width * height]
    for row in range(height):
        line = ""
        for col in range(width):
            val = tiled[row * width + col]
            line += map_to_glyph(val)
        lines.append(line)
    return lines [:height]


def render_heatmap(data: bytes, width: int, height: int) -> List[str]:
    """Render data bytes as a heatmap with ANSI colors"""
    lines = []
    tiled = (data * ((width * height) // len(data) + 1))[:width * height]
    for row in range(height):
        line = ""
        for col in range(width):
            val = tiled[row * width + col]
            ci = min(len(HEAT_COLORS) -1, val * len(HEAT_COLORS) // 256)
            line += f"{HEAT_COLORS[ci]}█{RESET}"
        lines.append(line)
    return lines[:height]


def hex_dump(data: bytes, width: int = 32) -> List[str]:
    """Return formatted hex dump lines in 16 bytes a row idk i might have to change this in the future"""
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{i:08x}  {hex_part:<{width}}  |{ascii_part}|")
    return lines
