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


## Interactive Workflow Guide

When you run **EntropyGarden.exe** with no arguments, you get a comprehensive interactive menu. No command-line expertise needed — everything is guided by prompts.

### Main Menu

```
ENTROPY GARDEN - MAIN MENU
  [1] Derive keys from image (Grow)
  [2] Generate Ed25519 keypair
  [3] Generate X25519 keypair
  [4] Sign a message
  [5] Verify a signature
  [6] Rotate a key
  [7] HMAC Challenge/Response
  [8] View key information
  [9] Export key to different format
  [0] Exit
```

### Step-by-Step Workflows

#### Workflow 1: Basic Key Generation from Image

**Goal**: Generate a cryptographic key from a photo

```
1. Run: EntropyGarden.exe
2. Menu: Select [1] Derive keys from image
3. Prompt: Enter image path (PPM or PNG file)
4. Display:
   - Image information (format, size, dimensions)
   - Entropy quality score (percentage + bits/byte)
   - ASCII visualization of the image
5. Interactive:
   - View different orientations (rotate image 0-7 ways)
   - Each orientation generates a different key
   - Re-roll until you have the key you want
6. Save:
   - Private key saved as: priv.key (PEM format)
   - Public key derived and saved as: pub.json
   - Checksum displayed for verification
7. Export menu:
   - Export to additional formats (PEM, SSH, JSON, JWK, QR-ASCII, QR-PNG)
```

**Example Output:**
```
  Checksum:   a3f7k2q9
  Fingerprint: a3:f7:k2:q9:... (95 chars total)
  Path: m/44'/0'/0'
  
  Private key saved: C:\path\priv.key
  Public key saved:  C:\path\pub.json
```

#### Workflow 2: Generate Ed25519 Keypair for Message Signing

**Goal**: Create a keypair for digitally signing messages

```
1. Run: EntropyGarden.exe
2. Menu: Select [2] Generate Ed25519 keypair
3. Source selection (choose one):
   
   Option A: From image entropy
   - Prompt: Enter image path
   - Program: Generates key from image
   
   Option B: From existing key file
   - Prompt: Enter path to existing key (PEM, JSON, or JWK)
   - Program: Uses first 32 bytes as seed

4. Output:
   - ed25519_priv_XXXXXXXX.pem (private key)
   - ed25519_pub_XXXXXXXX.pub (public key)
   - Checksum for verification

5. Next step: Sign messages or export in other formats
```

**How to use for signing:**
```
Your keypair is ready! Use it to:
- Sign documents (workflow [4])
- Share public key with others (workflow [8] -> view fingerprint)
- Export to SSH format for server access
```

#### Workflow 3: Sign a Message

**Goal**: Create a digital signature for authenticity proof

```
1. Run: EntropyGarden.exe
2. Menu: Select [4] Sign a message
3. Prompts:
   - Key file path: ed25519_priv_XXXXXXXX.pem
   - Message input: Either paste text directly or enter file path
   
4. Program processes:
   - Reads your Ed25519 private key
   - Signs the message (creates 64-byte signature)
   - Encodes signature as base64

5. Output:
   - Displays signature (base64 text)
   - Option to save to file (signature.sig)

6. Share with others:
   - Send them: message + signature
   - They can verify you created it (workflow [5])
```

**Example:**
```
Message: "I hereby authorize this transaction"
Signature:
  eTRgD23kLm9pQ8wXvYzF5a2B... [base64 string - 88 chars]
  
Saved to: C:\signature.sig
```

#### Workflow 4: Verify a Signature

**Goal**: Confirm a message wasn't tampered with and came from the expected person

```
1. Run: EntropyGarden.exe
2. Menu: Select [5] Verify a signature
3. Prompts:
   - Public key file path: ed25519_pub_XXXXXXXX.pub
   - Message: Paste text or enter file path
   - Signature: Paste the base64 signature string

4. Program validates:
   - Checks if signature matches message
   - Checks if it came from the private key holder
   - Returns VERIFIED or FAILED

5. Scenarios:
   - VERIFIED = Message is authentic, untampered
   - FAILED = Signature is forged or message was changed
```

#### Workflow 5: Key Rotation

**Goal**: Derive a new key from an old one safely (updates key periodically)

```
1. Run: EntropyGarden.exe
2. Menu: Select [6] Rotate a key
3. Prompts:
   - Parent key file path (existing key)
   - Rotation reason: "scheduled maintenance", "compromised", "routine update"

4. Program generates:
   - New derived key mathematically linked to original
   - Metadata: rotation timestamp, reason
   - New checksum

5. Output:
   - New key file saved: rotated_key_XXXXXXXX.key
   - Can continue deriving from this new key
   - Useful for: periodic key updates, secure retirement of old keys
```

#### Workflow 6: HMAC Challenge-Response (Prove Key Ownership)

**Goal**: Prove you own a key without revealing it

**Use case**: Two-factor authentication, key ownership verification

```
1. Run: EntropyGarden.exe
2. Menu: Select [7] HMAC Challenge/Response
3. Choose:
   
   Option A: Generate Challenge (you are the certifier)
   - Prompt: Path to key file
   - Output: JSON challenge with random nonce
   - Send to other party: challenge.json
   
   Option B: Verify Response (you are being verified)
   - Prompt: Path to key file + path to challenge.json
   - Prompt: Enter the response (base64 string from other party)
   - Result: VERIFIED or FAILED

4. Flow explanation:
   System generates random nonce [A]
   System computes: HMAC-SHA3(key, nonce) = expected [B]
   Other party computes: HMAC-SHA3(key, nonce) = response [C]
   If [B] == [C]: Other party has the correct key!
   
   Security: Nonce is random every time, response never repeats
```

#### Workflow 7: View Key Information

**Goal**: Inspect metadata and details of any key file

```
1. Run: EntropyGarden.exe
2. Menu: Select [8] View key information
3. Prompt: Path to key file (any format: PEM, JSON, JWK)
4. Output displays:
   - format: (PEM, JSON, or JWK)
   - key_length: 32 bytes
   - checksum: a3f7k2q9 (8-byte identifier)
   - fingerprint: a3:f7:k2:q9:... (full 95-char fingerprint)
   - created_at: (ISO timestamp)
   - source: (which image generated it)
   - orientation: (if available)
   
5. Optional:
   - View hexadecimal dump of raw key bytes
   - Useful for verification and auditing
```

#### Workflow 8: Export Key to Different Format

**Goal**: Convert a key between formats (PEM, SSH, QR, JSON, etc.)

```
1. Run: EntropyGarden.exe
2. Menu: Select [9] Export key to different format
3. Interface: Export menu shows 6 options:
   
   [1] PEM - OpenSSL compatible private key
   [2] SSH - OpenSSH public key format
   [3] JSON - Human-readable structured format
   [4] JWK - JSON Web Key standard
   [5] QR-ASCII - Text-based QR code (printable, archival)
   [6] QR-PNG - Machine-scannable PNG (mobile camera)

4. Example workflows:
   
   To use with OpenSSH:
   - Export as SSH format
   - Copy to ~/.ssh/authorized_keys
   
   To share via QR code:
   - Export as QR-PNG
   - Print or email as image
   - Recipient scans with phone camera
   
   To backup safely:
   - Export as PEM (encrypted recommended)
   - Store on encrypted USB drive
```


## Architecture

```
Image Entropy
   ↓
[PPM Parser] → Extract pixel bytes
   ↓
[HKDF Extract] → Concentrate entropy
   ↓
[Key Derivation] → Generate master seed + hierarchical keys
   ↓
[Cryptography]
  ├── Ed25519 (signing)
  ├── X25519 (key exchange)
  └── Curve25519 (underlying math)
   ↓
[Export] → PEM, SSH, JSON, JWK, QR, Binary
```

## RFC Compliance

| RFC | Module | Status |
|-----|--------|--------|
| RFC 8032 | Ed25519 EdDSA |  Full Compliance |
| RFC 7748 | X25519 DH |  Full Compliance |
| RFC 5869 | HKDF |  Full Compliance |
| RFC 4251 | SSH Format |  Compatible |
| RFC 7517 | JWK |  Compatible |
| Custom | QR Codes (ASCII/PNG) |  Extended Support |


**Export Formats Available**:
- `pem` — OpenSSL/SSH compatible private/public keys
- `ssh` — OpenSSH authorized_keys format
- `json` — Human-readable JSON format
- `jwk` — JSON Web Key standard format
- `qr-ascii` — ASCII art QR codes (archive/print)
- `qr-png` — Machine-scannable PNG QR codes ✓ **Mobile camera compatible**
- `binary` — Raw key bytes with checksum

## Security Notes

 **This is a reference implementation** suitable for education and non-critical use.

**For production cryptography**, consider:
- Using compiled `cryptography` library (installed via pip)
- Having security audit by cryptographic experts
- Using hardware security modules for key storage
- Implementing additional access controls

**Security Properties**:
-  Constant-time operations prevent timing attacks
-  RFC-compliant algorithm implementation
-  No weak keys or edge case vulnerabilities
-  Safe with arbitrary inputs


### For Cryptography Research & Development

EntropyGarden serves as a **complete reference implementation** for building cryptographic systems from scratch for those who may be interested as to how cryptographic libraries work :

**Core Algorithms Implemented**:
- Ed25519 (Edwards-curve Digital Signature Algorithm) — RFC 8032
- X25519 (Elliptic Curve Diffie-Hellman) — RFC 7748  
- Curve25519 (Montgomery ladder implementation) — 350+ lines of Python
- HKDF (HMAC-based Key Derivation Function) — RFC 5869
- SHA-512 (cryptographic hash) — Python standard library

**Applications in Cryptographic Research**:
1. **Algorithm Validation** — Verify RFC compliance against official test vectors
2. **Performance Analysis** — Compare pure Python vs optimized implementations (20x speedup)
3. **Educational Reference** — Understand elliptic curve cryptography internals without black boxes
4. **Protocol Development** — Base for building new cryptographic protocols
5. **Hardware Implementation** — Reference for FPGA/ASIC verification
6. **Side-channel Analysis** — Study timing attack mitigation through constant-time operations

**Research Applications of my project**:
- Post-quantum cryptography integration studies
- Threshold signature schemes (m-of-n signing)
- Hardware security module interfacing
- Zero-knowledge proof systems
- Multi-party computation frameworks
- Quantum-resistant hybrid cryptography

### Technical Expertise Required

**To build cryptographic systems from scratch, you need (mostly the sources I have read)**:

#### 1. Fundamental Mathematics (3-6 months study)
- **Modular arithmetic** — Operations in finite fields, prime numbers, multiplicative inverses
- **Group theory** — Cyclic groups, generators, group order, subgroups
- **Elliptic curves** — Weierstrass form, point addition, scalar multiplication
- **Number theory** — Extended Euclidean algorithm, Chinese Remainder Theorem, Fermat's little theorem
- **Linear algebra** — Matrix operations for cryptanalysis, eigenvalues

**Recommended Resources**:
- Silverman: "The Arithmetic of Elliptic Curves" (academic reference)
- Paar & Pelzl: "Understanding Cryptography" (practical introduction)
- Katz & Lindell: "Introduction to Modern Cryptography" (comprehensive theory)



Contributions welcome! Areas for enhancement:
- [ ] GUI interface (tkinter/PyQt)
- [ ] Hardware wallet integration
- [ ] Multi-party computation
- [ ] Additional image formats (PNG, JPEG via PIL)
- [ ] Web interface

