# Qr.PY
"""This is my own implementation of QR code generation which produces QR codes as ASCII text using block characters"""





# GALOIS Field 256 artihmetic  

_GF_EXP = [0] * 512
_GF_LOG = [0] * 256

def _gf_init():
    """Pre compute the GF 256 log/exp tables with a primitive polynomial 0x11d"""
    x = 1
    for i in range(255):
        _GF_EXP[i] = x
        _GF_LOG[x] = i
        x <<= 1
        if x >= 256:
            x ^= 0x11d
    for i in range(255, 512):
        _GF_EXP[i] = _GF_EXP[i - 255]
_gf_init()


def _gf_mul(a, b):
    """Multiply 2 GF 256 elements"""
    if a == 0 or b == 0:
        return 0
    return _GF_EXP[_GF_LOG[a] + _GF_LOG[b]]


def _gf_poly_mul(p, q):
    """Multiply two polynomials over GF256"""
    r = [0] * (len(p) + len(q) - 1)
    for j, q_coeff in enumerate(q):
        for i, p_coeff in enumerate(p):
            r[i + j] ^= _gf_mul(p_coeff, q_coeff)
    return r


# Reed the solomon error correction

def _rs_generator_poly(nsym):
    """Generate the RS geneator polynomial for nsym error coderwords"""
    g = [1]
    for i in range(nsym):
        g = _gf_poly_mul(g, [1, _GF_EXP[i]])
    return g


def _rs_encode(data,nsym):
    """Reed solomon encode data bytes with nsym error correction codeword"""
    gen = _rs_generator_poly(nsym)
    remainder = list(data) + [0] * nsym
    for i in range(len(data)):
        coeff = remainder[i]
        if coeff != 0:
            for j in range(len(gen)):
                remainder[i + j] ^= _gf_mul(gen[j], coeff)
    return remainder[len(data):]


# QR capacity table (byte mode)

# We only support version 1 to 10 instead of 1 to 40 
_QR_VERSIONS = {
    1:  (16,  10, 1),
    2:  (32,  16, 1),
    3:  (53,  26, 1),
    4:  (78,  18, 2),
    5:  (106, 24, 2),
    6:  (134, 16, 4),
    7:  (154, 18, 4),
    8:  (192, 22, 2),
    9:  (230, 22, 3),
    10: (271, 26, 4),
}


# Alignment pattern positions per version
_QR_ALIGNMENT = {
    1: [],
    2: [6, 18],
    3: [6, 22],
    4: [6, 26],
    5: [6, 30],
    6: [6, 34],
    7: [6, 22, 38],
    8: [6, 24, 42],
    9: [6, 26, 46],
    10: [6, 28, 50],
}

# Format info bits for EC level M with the mask pattern gong 0 to 7
_QR_FORMAT_BITS = [
    0x5412, 0x5125, 0x5E7C, 0x5B4B, 0x45F9, 0x40CE, 0x4F97, 0x4AA0,
]


# Core encoding function

def _choose_version(data_len):
    """Pick smallest qr version that fits the data length in byte mode"""
    for v in range(1, 11):
        data_codewords, _, _ = _QR_VERSIONS[v]
        # Byte mode : 4 bit mode + char count + data + terminator
        char_count_bits = 8 if v<= 9 else 16
        bits_needed = 4 + char_count_bits + data_len * 8 + 4
        bytes_needed = (bits_needed + 7) // 8
        if bytes_needed <= data_codewords:
            return v
    raise ValueError(f"Data too long for QR versions 1 to 10: {data_len} bytes")


def _encode_byte_mode(data, version):
    """Encode byte data into a bit stream for QR."""
    data_codewords, _, _ = _QR_VERSIONS[version]
    bits = []
    # Mode indicator: 0100 for byte mode
    bits.extend([0, 1, 0, 0])
    # Character count
    char_count_bits = 8 if version <= 9 else 16
    for i in range(char_count_bits - 1, -1, -1):
        bits.append((len(data) >> i) & 1)
    # Data
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    # Terminator
    max_bits = data_codewords * 8
    for _ in range(min(4, max_bits - len(bits))):
        bits.append(0)
    # Pad to byte boundary
    while len(bits) % 8 != 0:
        bits.append(0)
    # Pad codewords
    pad = [0xEC, 0x11]
    pi = 0
    while len(bits) < max_bits:
        for i in range(7, -1, -1):
            bits.append((pad[pi] >> i) & 1)
        pi = 1 - pi
    # Convert to bytes
    codewords = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        codewords.append(byte)
    return bytes(codewords)


def _interleave_with_ec(data_codewords, version):
    """Split data into blocks, and then add Reed solomon EC and interleave"""
    data_total, ec_per_block, num_blocks = _QR_VERSIONS[version]
    data_per_block = data_total // num_blocks
    remainder = data_total % num_blocks

    # Split it into blocks
    blocks = []
    offset = 0
    for i in range(num_blocks):
        size = data_per_block + (1 if i < remainder else 0)
        blocks.append(data_codewords[offset:offset + size])
        offset += size
        
        # Encode each block
    ec_blocks = [_rs_encode(block, ec_per_block) for block in blocks]
        
    # Interleave data codewords
    interleaved = bytearray()
    max_block = max(len(b) for b in blocks)
    for i in range(max_block):
        for block in blocks:
            if i < len(block):
                interleaved.append(block[i])
    
    # Interleave EC codewords
    for i in range(ec_per_block):
        for block in ec_blocks:
            if i < len(block):
                interleaved.append(block[i])

    return bytes(interleaved)


# Matrix construction + rendering

def _make_matrix(version):
    """Create empty qr matrix and reserve function patterns"""
    size = 17 + 4 * version
    matrix = [[None] * size for _ in range(size)]
    reserved = [[False] * size for _ in range(size)]
    
    def set_module(r, c, val):
        if 0 <= r < size and 0 <= c < size:
            matrix[r][c] = val
            reserved[r][c] = True
            
    # Finder patterns (7x7) + separator (8x8)
    for r0, c0 in [(0, 0), (0, size - 7), (size - 7, 0)]:
        for r in range(8):
            for c in range(8):
                if 0 <= r0 + r < size and 0 <= c0 + c < size:
                    set_module(r0 + r, c0 + c, 0)
                if (r in (0, 6) or c in (0, 6) or
                    (2 <= r <= 4 and 2 <= c <= 4)):
                    set_module(r0 + r, c0 + c, 1)

    # Alignment patterns
    positions = _QR_ALIGNMENT.get(version, [])
    for r_pos in positions:
        for c_pos in positions:
            # Skip if it overlaps with finder patterns
            if (r_pos <= 8 and c_pos <= 8):
                continue
            if (r_pos <= 8 and c_pos >= size - 8):
                continue
            if (r_pos >= size - 8 and c_pos <= 8):
                continue
            for r in range(-2, 3):
                for c in range(-2, 3):
                    val = 1 if (abs(r) == 2 or abs(c) == 2 or
                                (r == 0 and c == 0)) else 0
                    set_module(r_pos + r, c_pos + c, val)
                
    # Timing patterns
    for i in range(8, size - 8):
        val = 1 if (i % 2 == 0) else 0
        set_module(6, i, val)
        set_module(i, 6, val)
        
    # Dark space module
    set_module(4 * version + 9, 8, 1)
    
    # Reserve format information areas
    for i in range(8):
        set_module(8, i, 0)
        set_module(i, 8, 0)
        set_module(8, size - 1 - i, 0)
        set_module(size - 1 - i, 8, 0)
    set_module(8, 8, 0)  # Format info bit
    
    # Reserve version information areas for 7 and above
    if version >= 7:
        for i in range(6):
            for j in range(3):
                set_module(i, size - 11 + j, 0)
                set_module(size - 11 + j, i, 0)
    
    return matrix, reserved


def _is_data_cell(r, c, size, version):
    """Check if a cell is a data cell which is not reserved for the function patterns"""
    # Finder + seperator cores
    if r < 9 and c < 9:
        return False
    if r < 9 and c >= size -8:
        return False
    if r == 6 or c == 6:
        return False
    # Timing
    if r == 6 or c == 6:
        return False
    # Format info
    if r == 8 or c == 8:
        return False
    # Dark module
    if r == 4 * version + 9 and c == 8:
        return False
    # Alignment patterns
    positions = _QR_ALIGNMENT.get(version,[])
    for rp in positions:
        for cp in positions:
            if abs(r - rp) <= 2 and abs(c - cp) <= 2:
                return False
    # Return info
    if version >= 7:
        if r < 6 and c >= size -11:
            return False
        if r >= size - 11 and c < 6:
            return False
    return True


def _place_data(matrix , reserved, data, version):
    """Place encoded data bits into the QR matrix along the snake path"""
    size = len(matrix)
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)

    bit_idx = 0
    col = size - 1
    upward = True

    while col >= 0:
        if col == 6:
            col -= 1
            continue
        for row_idx in range(size):
            row = size - 1 - row_idx if upward else row_idx
            for dc in (0, -1):
                c = col + dc
                if c < 0 or c >= size:
                    continue
                if reserved[row][c]:
                    continue
                if bit_idx < len(bits):
                    matrix[row][c] = bits[bit_idx]
                    bit_idx += 1
                else:
                    matrix[row][c] = 0
        upward = not upward
        col -= 2
        
    
# Masking

def _mask_function(mask_pattern, r, c):
    """Evaluate mask condition for a given pattern number"""
    patterns = [
        lambda r, c: (r + c) % 2 == 0,
        lambda r, c: r % 2 == 0,
        lambda r, c: c % 3 == 0,
        lambda r, c: (r + c) % 3 == 0,
        lambda r, c: (r // 2 + c // 3) % 2 == 0,
        lambda r, c: ((r * c) % 2 + (r * c) % 3) == 0,
        lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
        lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
    ]
    return patterns[mask_pattern](r, c)


def _apply_mask_and_format(matrix, version, mask_pattern):
    """Apply mask pattern and place format info in one pass."""
    size = len(matrix)
    format_bits = _QR_FORMAT_BITS[mask_pattern]

    # Apply mask to data cells
    for r in range(size):
        for c in range(size):
            if _is_data_cell(r, c, size, version):
                if _mask_function(mask_pattern, r, c):
                    matrix[r][c] ^= 1

    # Place format info bits
    format_bits_list = [(format_bits >> i) & 1 for i in range(14, -1, -1)]
    positions_row = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7),
                      (8, 8), (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
    positions_col = [(size - 1, 8), (size - 2, 8), (size - 3, 8),
                      (size - 4, 8), (size - 5, 8), (size - 6, 8), (size - 7, 8)]

    for i, (r, c) in enumerate(positions_row):
        matrix[r][c] = format_bits_list[i]
    for i, (r, c) in enumerate(positions_col):
        matrix[r][c] = format_bits_list[14 - i]

        
def _penalty_score(matrix, size):
    """Calculate QR code penalty score"""
    score = 0
    # Rule 1 : 5 or more of the same colour (probs have to tune)
    for r in range(size):
        run = 1
        for c in range(1, size):
            if matrix[r][c] == matrix[r][c - 1]:
                run += 1
            else:
                if run >=5:
                    score += run - 2
                run = 1
        if run >= 5:
            score += run -2
    for c in range(size):
        run = 1
        for r in range(1, size):
            if matrix[r][c] == matrix[r - 1][c]:
                run += 1
            else:
                if run >= 5:
                    score += run - 2
                run = 1
        if run >= 5:
            score += run - 2
    # Rule 2 : 2x2 blocks of the same colour
    for r in range(size -1):
        for c in range(size - 1):
            if matrix [r][c] == matrix[r][c+1] == matrix[r+1][c] == matrix[r+1][c+1]:
                score += 3
    return score


#Pub API

def encode(data: bytes) -> str:
    """Generate a scannable QR code from bytes as ASCII art
    
    Should use byte mode encoding and the smallest version possible 
    then return a string of block cahracters that an be scanned by any qr reader
    """
    if len(data) == 0:
        data = b"\x00"

    version = _choose_version(len(data))

    # Encode data
    data_codewords = _encode_byte_mode(data, version)

    # Add error correction and interleave
    full_codewords = _interleave_with_ec(data_codewords, version)

    # Build matrix
    matrix, reserved = _make_matrix(version)

    # Place data
    _place_data(matrix, reserved, full_codewords, version)

    # Find best mask pattern
    best_score = float('inf')
    best_matrix = None

    for mask in range(8):
        # Clone matrix and fill None cells
        test_matrix = [row[:] for row in matrix]
        size = len(test_matrix)
        for r in range(size):
            for c in range(size):
                if test_matrix[r][c] is None:
                    test_matrix[r][c] = 0

        _apply_mask_and_format(test_matrix, version, mask)

        score = _penalty_score(test_matrix, size)
        if score < best_score:
            best_score = score
            best_matrix = test_matrix
            
    # Render as ASCII (each module = 2 chars wide for square-ish appearance)
    size = len(best_matrix)
    lines = []
    for r in range(size):
        line = ""
        for c in range(size):
            line += "██" if best_matrix[r][c] else "░░"
        lines.append(line)
    return "\n".join(lines)
            