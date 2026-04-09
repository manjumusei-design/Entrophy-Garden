# Curve 25519
""" This is my own implementation of the 25519 Curve which is a specific eliptic curve 
used for cryptographic purposes. It is designed to be fast and secure, making it popular
such as cryptography, and in this case key exchange and digital signatures. 
The curve is defined by the equation: y^2 = x^3 + 486662x^2 + x over the finite field of prime order 2^255 - 19. """


import hashlib

# p = 2^255 -19
P = 2**255 -19
# The order of the base point
L = 2**252 + 27742317777372353535851937790883648493
# d = -121665/121666 mod 
D = (-121665 * pow(121666, P -2, P)) % P
# I = sqrt(-1) mod p = 2^((p-1)/4) mod p
I = pow(2, (P - 1) // 4, P)


def _recover_x(y, sign):
    """Recover x from y on the twisted edwards curve"""
    x2 = (y * y -1) * pow(D * y * y + 1, P - 2, P) % P
    if x2 == 0:
        if sign:
            raise ValueError("Invalid point")
        return 0 
    # Mod square root
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P != 0:
        x = (x * I) % P
    if (x * x - x2) % P != 0:
        raise ValueError("No square root exists")
    if x % 2 != sign % 2:
        x = P - x
    return x


def _inv(x):
    """Modular inverse and mod P value using the Fermat little theorem"""
    return pow(x, P - 2, P)


# Base Point B (recovered X coordinate , y = 4/5)
_BY = (4* pow(5, P - 2, P)) % P
_BX = _recover_x(_BY, I)
# Extedned coordinates for B which are X Y Z and T
B = (_BX % P, _BY% P, 1, (_BX * _BY) % P)


def point_add(p1, p2):
    """ add 2 points in extended coordinates which are x y z and t"""
    X1, Y1, Z1, T1 = p1
    X2, Y2, Z2, T2 = p2
    a = (Y1 - X1) * (Y2 - X2) % P
    b = (Y1 + X1) * (Y2 + X2) % P
    c = 2 * T1 * T2 * D % P
    d = 2 * Z1 * Z2 % P
    e = b - a
    f = d - c
    g = d + c
    h = b + a
    X3 = e * f % P
    Y3 = g * h % P
    Z3 = f * g % P
    T3 = e * h % P
    return X3, Y3, Z3, T3


def point_double(p1):
    """Double a point in extended coordinates"""
    X1, Y1, Z1, _ = p1
    a = X1 * X1 % P
    b = Y1 * Y1 % P
    c = 2 * Z1 * Z1 % P
    d = -a % P
    e = ((X1 + Y1) * (X1 + Y1) - a - b) % P
    g = d + b
    f = g - c
    h = d - b
    X3 = e * f % P
    Y3 = g * h % P
    Z3 = f * g % P
    T3 = e * h % P
    return X3, Y3, Z3, T3


def scalar_mult(s, point):
    """Scalar muiltipliocation via left to right binary bethod where uh
    
    s serves as the integer scalar 
    point x y z t in extended coordinates should return the result of s * point"""


    q = (0, 1, 1, 0) # Identity point
    for i in range(255, -1, -1):
        q = point_double(q)
        if s & (1 << i):
            q = point_add(q, point)
    return q


def point_to_bytes(point):
    """Encode a point to 32 bytes and with the Ed25519 format where it encodes with y with x sign bit"""
    X, Y, Z, _ = point
    zi = _inv(Z)
    x = X * zi % P
    y = Y * zi % P
    # Encodes Y with bit 255 will become X parity 
    encoded = y.to_bytes(32, "little")
    arr = bytearray(encoded)
    arr[31] |= (x & 1) << 7
    return bytes(arr)


def bytes_to_point(b):
    """Decode 32 bytes to a point on the curve"""
    if len(b) != 32:
        raise ValueError("Invalid point encoding")
    arr = bytearray(b)
    sign = (arr[31] >> 7) & 1
    arr[31] &= 0x7F
    y = int.from_bytes(arr, "little")
    x = _recover_x(y, sign)
    return x, y, 1, (x * y) % P


def clamp_scalar(scalar_bytes):
    """Clamp a 32 byte scalar as per the Ed25519 spec sheet"""
    arr = bytearray(scalar_bytes)
    arr [0] &= 248
    arr[31] &= 127
    arr[31] |= 64
    return int.from_bytes(arr,"little")


def encode_int_le(n, length=32):
    """Encode an integer as little endian bytes of a specified length"""
    return n.to_bytes(length, "little")

    