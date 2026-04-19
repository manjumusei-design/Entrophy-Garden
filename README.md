# EntropyGarden

**Derive cryptographic keys from image entropy using RFC-compliant cryptography**

## The Problem It Solves

**Key Distribution Without Communication** — This project solves a fundamental cryptography challenge: How can two parties establish shared secret keys when they can exchange a physical object (photograph, QR code, printout) but cannot safely transmit cryptographic material over networks?

Traditional key distribution requires either:
- Exchanging the key directly (eavesdropping risk)
- Using Diffie-Hellman key exchange (network required, man-in-the-middle risk)
- Pre-shared keys (doesn't scale)

EntropyGarden provides an alternative: **Both parties derive identical keys from a shared image deterministically**. Same image + same derivation path = same 32-byte key, every time. This eliminates the key-exchange problem entirely.

**Use Cases:**
- **Air-gapped key generation** — Generate cryptographic keys offline from photographs
- **Physical key agreement** — Two parties meet, take or choose a photo together, both derive identical keys
- **Visual entropy capture** — Convert chaotic natural patterns from the metadata of the photo into cryptographic randomness
- **Cryptography education** — Reference implementation of elliptic curves without black boxes

**Implementation Advantage: No Dependencies**

Every cryptographic primitive is implemented purely in Python without external dependencies and rewritten by yours truly after reading spec sheets and stack overflow:
- **Ed25519 signatures** (RFC 8032) — 450 lines of pure Python elliptic curve math
- **X25519 key exchange** (RFC 7748) — 350+ lines of Montgomery ladder implementation  
- **Curve25519 field arithmetic** — Complete elliptic curve operations from scratch
- **HKDF key derivation** (RFC 5869) — Hierarchical deterministic derivation
- **QR code generation** — Full Reed-Solomon error correction codec, no external libs
- **PPM image parsing** — Image entropy extraction without PIL/image libraries
- **SSH format encoding** — OpenSSH key compatibility without cryptography library

This means:
- **Zero startup overhead** — No pip install required for core functionality
- **Single 50MB executable** — PyInstaller builds standalone .exe for distribution
- **Complete auditability** — All code is visible, no opaque C/C++ extensions or whatever security issues that may be present


## What It Does

EntropyGarden generates deterministic cryptographic keys from image entropy:

1. **Load any image** (PPM/RGB format for now)
2. **Extract entropy** from pixel values
3. **Derive keys** using hierarchical HKDF (RFC 5869)
4. **Generate signatures** using Ed25519 (RFC 8032)
5. **Key exchange** using X25519 (RFC 7748)
6. **Export** in PEM, SSH, JSON, JWK, QR (ASCII/PNG), or Binary formats

## Quick Start

### Installation

1. Just open up the .exe in releases
2. Copy a path of an image
3. Interact with it! 

#› Test Workflow for ShipWrights (ignore if youre reading the README) 
    Use a clean scratch folder so the rebuilt .exe doesnt mix outputs with old files.

    $Root = "C:\Users\User\Desktop\Entrophy-Garden\EntrophyGarden"
    $Exe = Join-Path $Root "dist\EntropyGarden.exe"
    $Img = "C:\Users\User\Desktop\Entrophy-Garden\NewTux.png"
    $TestDir = Join-Path $Root "ship-test"
    New-Item -ItemType Directory -Force -Path $TestDir | Out-Null
    Set-Location $TestDir

    For the interactive menu run these flows in order.

    1. Generate Ed25519 keypair from the sample image

    1. Choose [2]
    2. Choose [1]
    3. Enter $Img
    4. Save keypair: y
    5. Exit with [0]

    You should get files like:

    - ed25519_priv_*.pem
    - ed25519_pub_*.pub

    Check:

    Get-ChildItem ed25519_* | Select-Object Name,Length

    2. Sign a message with the generated Ed25519 private key
    Find the private key path:

    $EdPriv = (Get-ChildItem ed25519_priv_*.pem | Select-Object -First 1).FullName
    $EdPub = (Get-ChildItem ed25519_pub_*.pub | Select-Object -First 1).FullName
    $Message = "EntropyGarden ship test"

    Interactive flow:

    1. Choose [4]
    2. Enter $EdPriv
    3. Enter $Message
    4. Save signature: y
    5. Exit or continue

    Then:

    $SigFile = (Get-ChildItem signature*.sig | Select-Object -First 1).FullName
    Get-Content $SigFile

    3. Verify the signature with the generated public key
    Copy the base64 signature from the .sig file and run:

    1. Choose [5]
    2. Enter $EdPub
    3. Enter the same message: EntropyGarden ship test
    4. Paste the signature contents
    5. Confirm it says verification succeeded

    This proves users can generate, save, reload, sign, and verify their own keys.

    4. Export SSH public key from the generated private key

    1. Choose [9]
    2. Enter $EdPriv
    3. Choose [2] for SSH
    4. Choose [0] to finish
    5. Exit

    Check the export:

    Get-ChildItem key_*.pub | Select-Object Name,Length
    Get-Content (Get-ChildItem key_*.pub | Select-Object -First 1).FullName

    Expected: line starts with ssh-ed25519

    5. Export QR-PNG from the generated private key

    1. Choose [9]
    2. Enter $EdPriv
    3. Choose [6] for QR-PNG
    4. Choose [0]
    5. Exit

    Check:

    Get-ChildItem *.qr.png | Select-Object Name,Length

    You should see a non-empty PNG file.

    6. Rotate the generated private key

    1. Choose [6]
    2. Enter $EdPriv
    3. Enter reason: ship test
    4. Save rotated key: y
    5. Exit

    Check:

    Get-ChildItem rotated_key_*.key, rotated_key_*.pem, rotated_key_* | Select-Object Name,Length

    Expected: a new readable key file exists.

    7. HMAC challenge/response with a self-generated key
    Create a shared key first from the image using menu option [1] or reuse a PEM key created by the program. The
  simplest
    is to use the generated Ed25519 private key path as the key input for the HMAC menu, since the app now parses saved
    key files correctly.

    Generate challenge:

    1. Choose [7]
    2. Choose [1]
    3. Enter $EdPriv
    4. Save challenge: y

    Check:

    $Challenge = (Get-ChildItem challenge*.json | Select-Object -First 1).FullName
    Get-Content $Challenge

    Respond to challenge:

    1. Choose [7]
    2. Choose [2]
    3. Enter $EdPriv
    4. Enter $Challenge
    5. Save response if prompted

    If saved:

    $Response = (Get-ChildItem response*.txt | Select-Object -First 1).FullName
    Get-Content $Response

    Verify response:

    1. Choose [7]
    2. Choose [3]
    3. Enter $EdPriv
    4. Enter $Challenge
    5. Paste the saved response text
    6. Confirm it says verified

    That proves users can generate and verify their own proof-of-key-ownership flow.

    8. Generate X25519 keypair and confirm files are created

    1. Choose [3]
    2. Choose [1]
    3. Enter $Img
    4. Save keypair: y

    Check:

    Get-ChildItem x25519_* | Select-Object Name,Length

    You should see private and public files created without error.

    9. View info for saved keys

    1. Choose [8]
    2. Enter $EdPriv
    3. Decline hex dump unless you want it

    Expected: JSON-style metadata and checksum/fingerprint are shown.
