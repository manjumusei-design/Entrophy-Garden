import hashlib
import os
import struct
import zlib
from typing import Dict, Tuple


ORIENTATIONS = [
    "normal",
    "rotate 90 CW",
    "rotate 180",
    "rotate 270 CW",
    "flip horizontal",
    "flip vertical",
    "transpose (flip + rotate 90)",
    "transverse (flip + rotate 270)",
]


def parse_ppm(path: str) -> Tuple[bytes, int, int]:
    """Read P3 ASCII or p6 binary PPM files and return pixel data such as width and height"""
    with open(path, "rb") as f:
        magic = f.readline().strip()
    if magic not in (b"P3", b"P6"):
        raise ValueError(f"Not a PPM file: {magic.decode(errors='replace')}")
    with open(path, "rb") as f:
        f.readline()
        while True:
            line = f.readline().decode().strip()
            if line and not line.startswith("#"):
                dims = line.split()
                if len(dims) == 2:
                    w, h = int(dims[0]), int(dims[1])
                    break
        maxval = int(f.readline().decode().strip())
        if magic == b"P6":
            return f.read(w * h * 3), w, h
        else:
            data = f.read().decode().split()
            return bytes(int(x) for x in data), w, h

        
def parse_png(path: str) -> Tuple[bytes, int, int]:
    with open(path, "rb") as f:
        sig = f.read(8)
        if sig[:4] != b"\x89PNG":
            raise ValueError("Not a PNG file")
        f.read(4)  # IHDR length
        f.read(4)  # IHDR type
        ihdr = f.read(13)
        f.read(4)  # CRC
        width = struct.unpack(">I", ihdr[0:4])[0]
        height = struct.unpack(">I", ihdr[4:8])[0]
        bit_depth = ihdr[8]
        color_type = ihdr[9]
        idat_data = b""
        while True:
            try:
                length = struct.unpack(">I", f.read(4))[0]
            except struct.error:
                break
            chunk_type = f.read(4)
            if len(chunk_type) < 4:
                break
            data = f.read(length)
            f.read(4)  # CRC
            if chunk_type == b"IEND":
                break
            if chunk_type == b"IDAT":
                idat_data += data

    if not idat_data:
        raise ValueError("No IDAT data in PNG")

    try:
        raw = zlib.decompress(idat_data)
    except zlib.error:
        raise ValueError("Cannot decompress PNG IDAT data")

    if color_type == 0:  # Grayscale
        channels = 1
    elif color_type == 2:  # RGB
        channels = 3
    elif color_type == 3:  # Indexed
        channels = 1
    elif color_type == 4:  # Grayscale + alpha
        channels = 2
    elif color_type == 6:  # RGBA
        channels = 4
    else:
        raise ValueError(f"Unsupported PNG color type: {color_type}")

    bytes_per_pixel = channels * bit_depth // 8
    row_bytes = width * bytes_per_pixel

    decoded = bytearray(width * height * bytes_per_pixel)
    decode_pos = 0
    prev_row = b"\x00" * row_bytes
    pos = 0
    for row_idx in range(height):
        if pos >= len(raw):
            break
        filter_type = raw[pos]
        pos += 1
        row = bytearray(raw[pos:pos + row_bytes])
        pos += row_bytes

        if filter_type == 0:  # None
            pass
        elif filter_type == 1:  # Sub
            for i in range(row_bytes):
                a = row[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                row[i] = (row[i] + a) & 0xFF
        elif filter_type == 2:  # Up
            for i in range(row_bytes):
                b = prev_row[i]
                row[i] = (row[i] + b) & 0xFF
        elif filter_type == 3:  # Average
            for i in range(row_bytes):
                a = row[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                b = prev_row[i]
                row[i] = (row[i] + (a + b) // 2) & 0xFF
        elif filter_type == 4:  # Paeth
            for i in range(row_bytes):
                a = row[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                b = prev_row[i]
                c = prev_row[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                p = a + b - c
                pa = abs(p - a)
                pb = abs(p - b)
                pc = abs(p - c)
                if pa <= pb and pa <= pc:
                    pr = a
                elif pb <= pc:
                    pr = b
                else:
                    pr = c
                row[i] = (row[i] + pr) & 0xFF

        decoded[decode_pos:decode_pos + row_bytes] = row
        decode_pos += row_bytes
        prev_row = bytes(row)
    decoded = decoded[:decode_pos]
    
    rgb = bytearray()
    if color_type == 0:  # Grayscale → RGB
        for i in range(0, len(decoded), channels):
            v = decoded[i]
            rgb.extend([v, v, v])
    elif color_type == 2:  # Already RGB
        rgb = decoded
    elif color_type == 3:  # Indexed → need palette (skip, treat as grayscale)
        for i in range(0, len(decoded), channels):
            v = decoded[i]
            rgb.extend([v, v, v])
    elif color_type == 4:  # Grayscale + alpha → RGB
        for i in range(0, len(decoded), channels):
            v = decoded[i]
            rgb.extend([v, v, v])
    elif color_type == 6:  # RGBA → RGB (drop alpha)
        for i in range(0, len(decoded), channels):
            rgb.extend(decoded[i:i + 3])

    return bytes(rgb), width, height

        
        
def get_image(path: str) -> Tuple[bytes, int, int]:
    with open(path, "rb") as f:
        header = f.read(8)
    if header[:4] == b"\x89PNG":
        return parse_png(path)
    if header[:2] in (b"P3", b"P6"):
        return parse_ppm(path)
    try:
        return parse_ppm(path)
    except ValueError:
        raise ValueError(f"Unsupported image format: {path}")
        
def get_image_info(path: str) -> Dict[str, object]:
    file_size = os.path.getsize(path)
    with open(path, "rb") as f:
        header = f.read(8)

    if header[:4] == b"\x89PNG":
        with open(path, "rb") as f:
            f.read(8)
            f.read(4)
            f.read(4)
            ihdr = f.read(13)
        w = struct.unpack(">I", ihdr[0:4])[0]
        h = struct.unpack(">I", ihdr[4:8])[0]
        return {"format": "PNG", "width": w, "height": h, "file_size": file_size}

    if header[:2] in (b"P3", b"P6"):
        with open(path, "rb") as f:
            f.readline()
            while True:
                line = f.readline().decode().strip()
                if line and not line.startswith("#"):
                    dims = line.split()
                    if len(dims) == 2:
                        w, h = int(dims[0]), int(dims[1])
                        break
        return {"format": "PPM", "width": w, "height": h, "file_size": file_size}

    return {"format": "unknown", "width": 0, "height": 0, "file_size": file_size}


def _get_rotated_coords(x: int, y: int, orientation: int,
                       width: int, height: int) -> Tuple[int, int]:
    if orientation == 0:
        return x, y
    elif orientation == 1:
        return height - 1 - y, x
    elif orientation == 2:
        return width - 1 - x, height - 1 - y
    elif orientation == 3:
        return y, width - 1 - x
    elif orientation == 4:
        return width - 1 - x, y
    elif orientation == 5:
        return x, height - 1 - y
    elif orientation == 6:
        return y, x
    elif orientation == 7:
        return height - 1 - y, width - 1 - x
    else:
        raise ValueError(f"Orientation must be 0-7, got {orientation}")


def rotate_pixels(pixel_data: bytes, orientation: int,
                  width: int, height: int) -> Tuple[bytes, int, int]:
    if orientation < 0 or orientation > 7:
        raise ValueError(f"Orientation must be 0-7, got {orientation}")
    if orientation == 0:  # No rotation needed
        return pixel_data, width, height
    pixels = list(pixel_data)
    bpp = 3  # bytes per pixel
    
    def get_pixel(x, y):
        idx = (y * width + x) * bpp
        return pixels[idx:idx + bpp]
    
    # Determine output dimensions
    if orientation in (1, 3, 6, 7):
        new_w, new_h = height, width
    else:
        new_w, new_h = width, height

    out = bytearray(new_w * new_h * bpp)
    for y in range(height):
        for x in range(width):
            nx, ny = _get_rotated_coords(x, y, orientation, width, height)
            src = get_pixel(x, y)
            idx = (ny * new_w + nx) * bpp
            out[idx:idx + bpp] = src
    
    return bytes(out), new_w, new_h



_HASH_FUNCTIONS = {
    "sha3_512": hashlib.sha3_512,
    "blake2b": hashlib.blake2b,
    "sha3_256": hashlib.sha3_256,
}


def extract_entropy(data: bytes, algorithm: str = "sha3_512") -> bytes:
    """Return crypto hash digest of data"""
    hash_func = _HASH_FUNCTIONS.get(algorithm)
    if not hash_func:
        raise ValueError(f"Unknown algorithm: {algorithm}. Supported: {', '.join(_HASH_FUNCTIONS.keys())}")
    return hash_func(data).digest()


def entropy_quality_test(data: bytes) -> Dict[str, object]:
    """Compute byte frequency distribtuion and return chi square test result against the uniform dist"""
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    n = len(data)
    expected = n / 256.0
    chi2 = sum((f - expected) ** 2 / expected for f in freq if expected > 0)
    bits = min(8.0, max(0.0, 8.0 - chi2 / (n * 256) * 8))
    return {
        "score": round(100 - min(100, chi2 / n * 100), 2),
        "bits_per_byte": round(bits, 4),
        "distribution": freq,
    }