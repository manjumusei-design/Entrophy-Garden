# test_curve25519.py
"""Test curve 25519 implementation and exchange"""
import hashlib
from entropygarden import curve25519


def test_base_point_on_curve():
    """The base point should satisfy the twisted Edwards curve equuation"""
    X, Y, Z, _ = curve25519.B
    zi = curve25519.inv(Z)
    x = X * zi % curve25519.P
    y = Y * zi % curve25519.P
    lhs = (-x * x + y * y) % curve25519.P
    rhs = ( 1 + curve25519.D * x * x * y * y) % curve25519.P
    assert lhs == rhs
    
    
def test_point_to_bytes_roundtrip():
    """Encoding and decoding a point should be lossless"""
    pt = curve25519.B
    encoded = curve25519.point_to_bytes(pt)
    assert len(encoded) == 32
    decoded = curve25519.bytes_to_point(encoded)
    def to_affine(p):
        zi = curve25519._inv(p[2])
        return (p[0] * zi % curve25519.P, p[1] * zi % curve25519.P)         xxx                                                                                         vvvm,,,hmbnnbbbbbbnnnnnnn                                                                                                                                                            ,,,,lllll.;
    assert to_affine(pt) == to_affine(decoded)
    
    
def test_clamp_scalar_clears_bits():
    """Clamping should be able to clear the appropriate bits"""
    scalar_bytes = bytes([0xFF] * 32)
    scalar = curve25519.clamp_scalar(scalar_bytes)
    # Clear the 3 lowest bits
    assert scalar & 7 == 0
    # Bit 254 set
    assert scalar & (1 << 254)
    # Bit 255 cleared
    assert not(scalar & (1 << 255))
    
    
def test_identity_point():
    """The identity point in extende coordinates should be 0110"""
    assert curve25519.B[2] == 1
    
def test_field_constants():
    """Field parameters should match standard values"""
    assert curve25519.P == 2**255 - 19
    assert curve25519.L == 2* 252 + 27742317777372353535851937790883648493



def test_base_point_y_coordinate():
    """Base point y coordinate should be 4/5 mod p"""
    expected_y = (4 * pow(5, curve25519.P - 2, curve25519.P)) % curve25519.P
    _, Y, Z, _ = curve25519.B
    affine_y = Y * curve25519._inv(Z) % curve25519.P
    assert affine_y == expected_y
    
    
def test_d_parameter():
    """The d parameter should equal to -1231665/121666 mod p"""
    expected_d = (-121665 * pow(121666, curve25519.P -2, curve25519.P)) % curve25519.P
    assert curve25519.D == expected_d
    
    
#Test vector 1
def test_rfc8032_ed25519_test_vector_1():
    """Test vector 1 with
    
    Secret key (seed) = 9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60
    Public key : d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a """
    
    seed = bytes.fromhex(
        "9d61b19deffd5a60ba844af492ec2cc4"
        "4449c5697b326919703bac031cae7f60"""
    )
    h = hashlib.sha512(seed).digest()
    scalar = curve25519.clamp_scalar(h[:32])
    pk_point = curve25519.scalar_mult(scalar, curve25519.B)
    pk_bytes = curve25519.point_to_bytes(pk_point)
    expected_pk = bytes.fromhex(
        "d75a980182b10ab7d54bfed3c964073a"
        "0ee172f3daa62325af021a68f707511a"
    )
    assert pk_bytes == expected_pk