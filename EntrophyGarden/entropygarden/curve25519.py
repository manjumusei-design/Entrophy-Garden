# entropygarden/curve25519.py

"""My pure python Curve25519 implementation.
Implements field arithmetic mod p = 2^255 - 19, twisted Edwards
curve -x^2 + y^2 = 1 + d*x^2*y^2, and point operations for Ed25519.
All big-integer math in pure Python with no external dependencies."""

import hashlib


# p = 2^255 - 19
P = 2**255 - 19
# Group order
L = 2**252 + 27742317777372353535851937790883648493
# d = -121665/121666 mod p
D = (-121665 * pow(121666, P - 2, P)) % P
# 2*d mod p (precomputed for addition)
_D2 = (2 * D) % P
# I = sqrt(-1) mod p
I = pow(2, (P - 1) // 4, P)


def _inv(x):
    """Moduar inverse mod P using fermats little theorem"""
    return pow(x, P - 2, P)


def _recover_x(y, sign):
    """Recover x coordinate from y and sign bit on the twisted edvards curve"""
    x2 = (y * y - 1) * _inv(D * y * y + 1) % P
    if x2 == 0:
        if sign:
            raise ValueError("Invalid point")
        return 0
    # Modular square root: x = x2^((p+3)/8) mod p
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P != 0:
        x = (x * I) % P
    if (x * x - x2) % P != 0:
        raise ValueError("No square root exists")
    if x % 2 != sign % 2:
        x = P - x
    return x

# Base point B for ED25519
# y = 4/5 mod p, x is recovered with the positive sign bit
_BY = (4 * _inv(5)) % P
_BX = _recover_x(_BY, 0)
# Extended coordinates (X:Y:Z:T) where x=X/Z, y=Y/Z, xy=T/Z
B = (_BX, _BY, 1, (_BX * _BY) % P)


def point_add(p1, p2):
    """ Add 2 points in extended coordinates
    
    Uses the unified addition formula valid for any 2 points including the
    identity and point doubling characterestics
    """
    X1, Y1, Z1, T1 = p1
    X2, Y2, Z2, T2 = p2

    A = ((Y1 - X1) % P) * ((Y2 - X2) % P) % P
    B = ((Y1 + X1) % P) * ((Y2 + X2) % P) % P
    C = (_D2 * T1 % P) * T2 % P
    D = (2 * Z1 % P) * Z2 % P
    E = (B - A) % P
    F = (D - C) % P
    G = (D + C) % P
    H = (B + A) % P

    return (E * F % P, G * H % P, F * G % P, E * H % P)


def point_double(p1):
    """Double a point in extended coordinates"""
    X1, Y1, Z1, _ = p1

    A = (X1 * X1) % P
    B = (Y1 * Y1) % P
    C = (2 * Z1 * Z1) % P
    D = (P - A) % P  # -A mod p
    E = ((X1 + Y1) * (X1 + Y1) - A - B) % P
    G = (D + B) % P
    F = (G - C) % P
    H = (D - B) % P

    return (E * F % P, G * H % P, F * G % P, E * H % P)


def scalar_mult(s, point):
    """Scalar multiplication via left to right trad binary method, errrr
    
s: integer scalar
point: (X, Y, Z, T) in extended coordinates
Returns: (X, Y, Z, T) = s * point"""
    if s == 0:
        return(0, 1, 1, 0) # identity point
              

    # Find the hgihest set bit and start from there 
    bit = 255
    while bit >= 0 and not (s & (1 << bit)):
        bit -= 1
        
    # Start with the point for the highest set bit
    result = point
    bit -= 1

    while bit >= 0:
        result = point_double(result)
        if s & (1 << bit):
            result = point_add(result, point)
        bit -= 1

    return result
    
    
def point_to_bytes(point):
    """Encode a point to 32 bytes (Ed25519 encoding : y with x sign bit)"""
    X, Y, Z, _ = point
    zi = _inv(Z)
    x = X * zi % P
    y = Y * zi % P
    # Encode y in little endian and set 255 bites to x parity
    encoded = y.to_bytes(32, "little")
    arr =  bytearray (encoded)
    arr[31] |= (x & 1) << 7
    return bytes(arr)


def bytes_to_point(b):
    """Decode 32 byte to a point"""
    if len(b) != 32:
        raise ValueError("Invalid point encoding: expected 32 bytes")
    arr = bytearray(b)
    sign = (arr[31] >> 7) & 1
    arr[31] &= 0x7F
    y = int.from_bytes(arr, "little")
    x = _recover_x(y, sign)
    return (x, y, 1, (x * y) % P)


def clamp_scalar(scalar_bytes):
    """Clamp a 32 byte scalar for usage in the ed25519 spec"""
    arr = bytearray(scalar_bytes)
    arr[0] &= 248    # Clear lowest 3 bits
    arr[31] &= 127   # Clear highest bit
    arr[31] |= 64    # Set second-highest bit
    return int.from_bytes(arr, "little")


def encode_int_le(n, length=32):
    """Encode an integer as little endian bytes of x length"""
    return n.to_bytes(length, "little")








    
     



    