"""My pure python Curve25519 implementation.
It implements field arithmetic mod p = 2^255 - 19, twisted Edwards
curve -x^2 + y^2 = 1 + d*x^2*y^2, and point operations for Ed25519.
All big-integer math in pure Python with no external dependencies."""

import hashlib


# p = 2^255 - 19
PRIME_MODULUS = 2**255 - 19
GROUP_ORDER = 2**252 + 27742317777372353535851937790883648493
# d = -121665/121666 mod p (curve parameter for Edwards curve)
CURVE_D = (-121665 * pow(121666, PRIME_MODULUS - 2, PRIME_MODULUS)) % PRIME_MODULUS
# 2*d mod p (precomputed for addition)
_D2_PRECOMPUTED = (2 * CURVE_D) % PRIME_MODULUS
# I = sqrt(-1) mod p
SQRT_NEG_ONE = pow(2, (PRIME_MODULUS - 1) // 4, PRIME_MODULUS)

P = PRIME_MODULUS
L = GROUP_ORDER
D = CURVE_D
_D2 = _D2_PRECOMPUTED
I = SQRT_NEG_ONE


def _inv(x):
    """Modular inverse mod PRIME_MODULUS using Fermat's little theorem"""
    return pow(x, PRIME_MODULUS - 2, PRIME_MODULUS)


def _recover_x(y, sign):
    """ Solves the Edwards curve equation -x^2 + y^2 = 1 + d*x^2*y^2 for x."""
    x2 = (y * y - 1) * _inv(CURVE_D * y * y + 1) % PRIME_MODULUS
    if x2 == 0:
        if sign:
            raise ValueError("Invalid point")
        return 0
    # Modular square root: x = x2^((p+3)/8) mod p
    x = pow(x2, (PRIME_MODULUS + 3) // 8, PRIME_MODULUS)
    if (x * x - x2) % PRIME_MODULUS != 0:
        x = (x * SQRT_NEG_ONE) % PRIME_MODULUS
    if (x * x - x2) % PRIME_MODULUS != 0:
        raise ValueError("No square root exists")
    if x % 2 != sign % 2:
        x = PRIME_MODULUS - x
    return x

# Base point B for ED25519
# y = 4/5 mod p, x is recovered with the positive sign bit
_BY = (4 * _inv(5)) % PRIME_MODULUS
_BX = _recover_x(_BY, 0)
B = (_BX, _BY, 1, (_BX * _BY) % PRIME_MODULUS)


def point_add(p1, p2):
    X1, Y1, Z1, T1 = p1
    X2, Y2, Z2, T2 = p2

    A = ((Y1 - X1) % PRIME_MODULUS) * ((Y2 - X2) % PRIME_MODULUS) % PRIME_MODULUS
    B = ((Y1 + X1) % PRIME_MODULUS) * ((Y2 + X2) % PRIME_MODULUS) % PRIME_MODULUS
    C = (_D2_PRECOMPUTED * T1 % PRIME_MODULUS) * T2 % PRIME_MODULUS
    D = (2 * Z1 % PRIME_MODULUS) * Z2 % PRIME_MODULUS
    E = (B - A) % PRIME_MODULUS
    F = (D - C) % PRIME_MODULUS
    G = (D + C) % PRIME_MODULUS
    H = (B + A) % PRIME_MODULUS

    return (E * F % PRIME_MODULUS, G * H % PRIME_MODULUS, F * G % PRIME_MODULUS, E * H % PRIME_MODULUS)


def point_double(p1):
    X1, Y1, Z1, _ = p1

    A = (X1 * X1) % PRIME_MODULUS
    B = (Y1 * Y1) % PRIME_MODULUS
    C = (2 * Z1 * Z1) % PRIME_MODULUS
    D = (PRIME_MODULUS - A) % PRIME_MODULUS  # -A mod p
    E = ((X1 + Y1) * (X1 + Y1) - A - B) % PRIME_MODULUS
    G = (D + B) % PRIME_MODULUS
    F = (G - C) % PRIME_MODULUS
    H = (D - B) % PRIME_MODULUS

    return (E * F % PRIME_MODULUS, G * H % PRIME_MODULUS, F * G % PRIME_MODULUS, E * H % PRIME_MODULUS)


def scalar_mult(s, point):
    if s == 0:
        return (0, 1, 1, 0)  # identity point

    bit = 255
    while bit >= 0 and not (s & (1 << bit)):
        bit -= 1

    result = point
    bit -= 1

    while bit >= 0:
        result = point_double(result)
        if s & (1 << bit):
            result = point_add(result, point)
        bit -= 1

    return result
    
    
def point_to_bytes(point):
    X, Y, Z, _ = point
    zi = _inv(Z)
    x = X * zi % PRIME_MODULUS
    y = Y * zi % PRIME_MODULUS
    # Encode y in little endian and set bit 255 to x parity
    encoded = y.to_bytes(32, "little")
    arr = bytearray(encoded)
    arr[31] |= (x & 1) << 7
    return bytes(arr)


def bytes_to_point(b):
    if len(b) != 32:
        raise ValueError("Invalid point encoding: expected 32 bytes")
    arr = bytearray(b)
    sign = (arr[31] >> 7) & 1
    arr[31] &= 0x7F
    y = int.from_bytes(arr, "little")
    x = _recover_x(y, sign)
    return (x, y, 1, (x * y) % PRIME_MODULUS)


def clamp_scalar(scalar_bytes):
    arr = bytearray(scalar_bytes)
    arr[0] &= 248    # Clear lowest 3 bits
    arr[31] &= 127   # Clear highest bit
    arr[31] |= 64    # Set second-highest bit
    return int.from_bytes(arr, "little")


def encode_int_le(n, length=32):
    return n.to_bytes(length, "little")








    
     



    