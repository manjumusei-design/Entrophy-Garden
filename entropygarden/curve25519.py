# entropygarden/curve25519.py

"""My pure python Curve25519 implementation.
Implements field arithmetic mod p = 2^255 - 19, twisted Edwards
curve -x^2 + y^2 = 1 + d*x^2*y^2, and point operations for Ed25519.
All big-integer math in pure Python with no external dependencies."""
import hashlib


# p = 2^255 - 19
P = 2**255 -19
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
    # Mod square root : x = x2 ^ ((p+3)/8) mod p
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P ! = 0:
        x = (x * I) % P
    if (x * x - x2) % P != 0:
        raise ValueError("No square root exists")
    if x % 2 != sign % 2:
        x = p - x
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
    



    