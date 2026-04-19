"""Rewrittten CLI entry point, which is interactive and has scripting capabilities for the more advanced"""
import argparse
import base64
import glob
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from entropygarden import key_derive, config, render, key_export, image_parser, verify, key_rotation
from entropygarden.image_parser import ORIENTATIONS
from entropygarden.cli_output import (print_banner, print_complete,
                                      log, error_msg, set_quiet, human_size)

# Terminal UI constants (extracted from magic numbers for maintainability)
MIN_ART_WIDTH = 10
MAX_ART_WIDTH = 60
MIN_ART_HEIGHT = 3
MAX_ART_HEIGHT = 14
TERMINAL_MARGIN_WIDTH = 2
TERMINAL_MARGIN_HEIGHT = 12

# Key export format extensions (consolidated from duplicates)
FORMAT_EXTENSIONS = {
    "pem": "pem",
    "ssh": "pub",
    "json": "json",
    "jwk": "jwk",
    "qr": "qr.txt",
    "qr-ascii": "qr.txt",
    "qr-png": "qr.png",
}


def _ask(prompt: str, default_val: str = "y") -> bool:
    """Ask a yes or no question, returns true for yes (duh)"""
    default_label = "[Y/n]" if default_val == "y" else "[y/N]"
    try:
        answer = input(f"  {prompt} {default_label} ").strip().lower()
        if not answer:
            return default_val == "y"
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    
    
def _find_image_in_dir(directory: str) -> str: 
    """Find the first image file ppm or png in the directory (uses already-imported glob)."""
    for ext in ("*.ppm", "*.png", "*.PPM", "*.PNG"):
        matches = glob.glob(os.path.join(directory, ext))
        if matches:
            return matches[0]
    return ""


def _derive_keys(pixel_data: bytes, algorithm: str) -> bytes:
    """Derive a 32-byte key from pixel data."""
    entropy = image_parser.extract_entropy(pixel_data, algorithm)
    return key_derive.derive_master(entropy)


def _show_image_art(pixel_data: bytes, img_w: int, img_h: int,
                    term_w: int, term_h: int) -> None:
    """Render and print the image as ASCII art"""
    lines = render.render_image_as_ascii(pixel_data, img_w, img_h, term_w, term_h)
    for line in lines:
        print(f"  {line}")


def _read_text_or_file(user_input: str) -> str:
    """Return trimmed literal text or the trimmed contents of a text file."""
    value = user_input.strip().strip('"').strip("'")
    if not value:
        return ""
    if os.path.isfile(value):
        return Path(value).read_text(encoding="utf-8").strip()
    return value


def _show_export_menu(key_path: str, checksum: str) -> None:
    """Show interactive menu for exporting keys in different formats."""
    print("\n" + "="*60)
    print("  EXPORT OPTIONS")
    print("="*60)
    print(f"\n  Key: {checksum}\n")
    
    formats = [
        ("pem", "PEM Format (OpenSSL/SSH compatible)"),
        ("ssh", "SSH Format (OpenSSH public key)"),
        ("json", "JSON Format (human-readable)"),
        ("jwk", "JWK Format (JSON Web Key standard)"),
        ("qr-ascii", "QR Code - Native ASCII that cannot be scanned most of the time (text-based, archival)"),
        ("qr-png", "[RECOMMENDED] QR Code - PNG based off the native ASCII (mobile-scannable!)"),
    ]
    
    while True:
        print("  Select export format:")
        for i, (fmt, desc) in enumerate(formats, 1):
            marker = ">>" if fmt == "qr-png" else "  "
            print(f"    {marker} [{i}] {desc}")
        print(f"    [0] Done (no more exports)")
        print()
        
        try:
            choice = input("  Enter choice (0-6): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        
        if choice == "0":
            break
        
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(formats):
                error_msg("Invalid choice. Please select 0-6.")
                continue
        except ValueError:
            error_msg("Please enter a number.")
            continue
        
        fmt, desc = formats[idx]
        _export_key_interactive(key_path, fmt, checksum)
        print()


def _handle_filename_collision(base_path: str, fmt: str) -> str:
    """Generate unique filename by appending counter if file exists for edge cases by users"""
    output_path = base_path
    if not os.path.exists(output_path):
        return output_path
    
    counter = 1
    # Logic of how to append counter based on format
    if fmt == "qr-png" or base_path.endswith(".qr.png"):
        stem = base_path[:-7] if base_path.endswith(".qr.png") else Path(base_path).stem
        ext = ".qr.png"
    elif fmt in ("qr", "qr-ascii") or base_path.endswith(".qr.txt"):
        stem = base_path[:-7] if base_path.endswith(".qr.txt") else Path(base_path).stem
        ext = ".qr.txt"
    else:
        p = Path(base_path)
        stem = p.stem
        ext = "".join(p.suffixes)  # Preserve all suffixes
    
    while os.path.exists(output_path):
        output_path = f"{stem}_{counter}{ext}"
        counter += 1
    
    return output_path


def _export_key_interactive(key_path: str, fmt: str, checksum: str) -> None:
    """Export key in specified format with automatic filename.
    
    Uses consolidated FORMAT_EXTENSIONS constant and extracted collision handler.
    """
    # Suggest output filename
    if fmt == "qr-png":
        output_path = f"key_{checksum[:8]}.qr.png"
    elif fmt == "qr" or fmt == "qr-ascii":
        output_path = f"key_{checksum[:8]}.qr.txt"
    else:
        ext = FORMAT_EXTENSIONS.get(fmt, fmt)
        output_path = f"key_{checksum[:8]}.{ext}"

    output_path = _handle_filename_collision(output_path, fmt)
    
    try:
        print(f"\n  Exporting as {fmt.upper()}...")
        meta = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "format": fmt,
        }

        key_bytes = _prepare_key_for_export(key_path, fmt)
        key_export.write_key(key_bytes, output_path, fmt, meta)

        actual_output_path = output_path
        if fmt == "qr" or fmt == "qr-ascii":
            if not actual_output_path.endswith(".qr.txt"):
                actual_output_path = str(Path(actual_output_path).with_name(Path(actual_output_path).stem + ".qr.txt"))
        elif fmt == "qr-png":
            if not actual_output_path.endswith(".qr.png"):
                actual_output_path = str(Path(actual_output_path).with_name(Path(actual_output_path).stem + ".qr.png"))
        elif fmt == "ssh" and not actual_output_path.endswith(".pub"):
            actual_output_path = str(Path(actual_output_path).with_name(Path(actual_output_path).stem + ".pub"))

        print(f"  [OK] Exported to: {os.path.abspath(actual_output_path)}")
        
        # Special message for QR
        if fmt == "qr":
            size = os.path.getsize(output_path)
            print(f"  [QR] Code is scannable! Size: {human_size(size)}")

        
        log(f"Successfully exported {fmt} format")
    except Exception as e:
        error_msg(f"Export failed: {e}")

        
def _process_one_image(cfg: dict) -> bool:
    """Process a single image: prompt for path, show art, derive keys, offer save.

    Returns True if the user wants to process another image.
    """
    print()
    print("  Copy and paste or type the path here.")
    print("  (PPM and PNG files supported for now, maybe more in the future?)")
    print()

    try:
        image_path = input("  Image path: ").strip().strip('"').strip("'")
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    if not image_path:
        found = _find_image_in_dir(".")
        if found:
            image_path = found
            log(f"Found image: {found}")
        else:
            error_msg("No image specified and none found in current directory.")
            return False

    if not os.path.isfile(image_path):
        error_msg(f"File not found: {image_path}")
        return False

    # Load image
    try:
        pixel_data, img_w, img_h = image_parser.get_image(image_path)
    except ValueError as e:
        error_msg(str(e))
        return False

    # Show metadata
    info = image_parser.get_image_info(image_path)
    print(f"\n  Image: {os.path.basename(image_path)}")
    print(f"  Format: {info['format']}  |  Size: {human_size(info['file_size'])}  |  "
          f"Dimensions: {img_w}x{img_h}")

    quality = image_parser.entropy_quality_test(pixel_data)
    print(f"  Entropy score: {quality['score']}%  |  Bits/byte: {quality['bits_per_byte']}")

    algorithm = cfg.get("algorithm", "sha3_512")

    # Terminal dimensions for art renders
    term = render.detect_terminal()
    art_w = min(term["width"] - TERMINAL_MARGIN_WIDTH, MAX_ART_WIDTH)
    art_h = min(term["height"] - TERMINAL_MARGIN_HEIGHT, MAX_ART_HEIGHT)
    if art_h < MIN_ART_HEIGHT:
        art_h = MIN_ART_HEIGHT
    if art_w < MIN_ART_WIDTH:
        art_w = MIN_ART_WIDTH

    # Initial orientation
    orientation = 0

    while True:
        # Rotate pixels for current orientation
        if orientation == 0:
            display_pixels = pixel_data
            display_w, display_h = img_w, img_h
        else:
            display_pixels, display_w, display_h = image_parser.rotate_pixels(
                pixel_data, orientation, img_w, img_h)

        # Show art
        print()
        label = f"Orientation: {ORIENTATIONS[orientation]} ({display_w}x{display_h})"
        print(f"  {label}")
        _show_image_art(display_pixels, display_w, display_h, art_w, art_h)

        # Derive keys from the oriented pixel data
        child_key = _derive_keys(display_pixels, algorithm)
        fp = key_derive.key_fingerprint(child_key)
        cs = key_derive.compute_checksum(child_key)

        print(f"\n  Path:       m/44'/0'/0'")
        print(f"  Checksum:   {cs}")
        print(f"  Fingerprint: {fp}")

        if _ask("Reroll with different orientation?", default_val="y"):
            orientation = (orientation + 1) % len(ORIENTATIONS)
            print(f"\n  --- Reroll: {ORIENTATIONS[orientation]} ---")
            continue
        break

    # Save keys
    print()
    if _ask("Save key pair to current folder?", default_val="y"):
        meta = {
            "algorithm": algorithm,
            "path": "m/44'/0'/0'",
            "source": os.path.basename(image_path),
            "orientation": ORIENTATIONS[orientation],
            "orientation_index": orientation,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        priv_path = "priv.key"
        pub_path = "pub.json"

        counter = 1
        while os.path.exists(priv_path):
            priv_path = f"priv_{counter}.key"
            pub_path = f"pub_{counter}.json"
            counter += 1

        key_export.write_key(child_key, priv_path, "pem", meta)
        pub_key = key_derive.hkdf_expand(child_key, b"public", 32)
        key_export.write_key(pub_key, pub_path, "json", meta)

        print(f"\n  Private key saved: {os.path.abspath(priv_path)}")
        print(f"  Public key saved:  {os.path.abspath(pub_path)}")
        print_complete(cs)
        
        # Show export menu for additional formats
        print()
        if _ask("Export key in additional formats?", default_val="y"):
            _show_export_menu(priv_path, cs)
    else:
        print("\n  Keys not saved.")

    print()
    return _ask("Process another image?", default_val="n")


def _interactive_ed25519_keygen() -> None:
    """Interactive Ed25519 keypair generation from seed or image."""
    print("\n" + "="*60)
    print("  ED25519 KEYPAIR GENERATION")
    print("="*60)
    
    print("\n  Source options:")
    print("    [1] From image entropy")
    print("    [2] From existing key file")
    print("    [0] Cancel")
    
    try:
        choice = input("\n  Select source (0-2): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    
    if choice == "0":
        return
    
    from entropygarden import ed25519, ssh_format
    
    if choice == "1":
        # Derive from image
        print("\n  Copy and paste or type the path to your image (PPM/PNG):")
        try:
            image_path = input("  Image path: ").strip().strip('"').strip("'")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        
        if not image_path or not os.path.isfile(image_path):
            error_msg("Image file not found.")
            return
        
        try:
            pixel_data, img_w, img_h = image_parser.get_image(image_path)
            child_key = _derive_keys(pixel_data, "sha3_512")
        except ValueError as e:
            error_msg(str(e))
            return
    
    elif choice == "2":
        # From existing key file
        print("\n  Enter path to key file (PEM, JSON, or JWK):")
        try:
            key_path = input("  Key file path: ").strip().strip('"').strip("'")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        
        if not key_path or not os.path.isfile(key_path):
            error_msg("Key file not found.")
            return
        
        try:
            child_key = _read_key_file(key_path)
        except ValueError as e:
            error_msg(str(e))
            return
    else:
        error_msg("Invalid choice.")
        return
    
    # Generate Ed25519 keypair
    try:
        sk = ed25519.generate_signing_key(child_key[:32])
    except Exception as e:
        error_msg(f"Failed to generate keypair: {e}")
        return
    
    checksum = key_derive.compute_checksum(sk.seed)
    print(f"\n  [OK] Ed25519 keypair generated")
    print(f"  Checksum: {checksum}")
    
    # Export options
    if _ask("\n  Save keypair to files?", default_val="y"):
        priv_path = f"ed25519_priv_{checksum[:8]}.pem"
        pub_path = f"ed25519_pub_{checksum[:8]}.pub"
        
        counter = 1
        while os.path.exists(priv_path):
            priv_path = f"ed25519_priv_{checksum[:8]}_{counter}.pem"
            pub_path = f"ed25519_pub_{checksum[:8]}_{counter}.pub"
            counter += 1
        
        meta = {"created_at": datetime.now(timezone.utc).isoformat()}
        key_export.write_ed25519_keypair(sk.seed, priv_path, pub_path, meta)
        print(f"  Private key: {os.path.abspath(priv_path)}")
        print(f"  Public key:  {os.path.abspath(pub_path)}")


def _interactive_x25519_keygen() -> None:
    """Interactive X25519 keypair generation from seed or image."""
    print("\n" + "="*60)
    print("  X25519 KEYPAIR GENERATION")
    print("="*60)
    
    print("\n  Source options:")
    print("    [1] From image entropy")
    print("    [2] From existing key file")
    print("    [0] Cancel")
    
    try:
        choice = input("\n  Select source (0-2): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    
    if choice == "0":
        return
    
    from entropygarden import x25519
    
    if choice == "1":
        # Derive from image
        print("\n  Copy and paste or type the path to your image (PPM/PNG):")
        try:
            image_path = input("  Image path: ").strip().strip('"').strip("'")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        
        if not image_path or not os.path.isfile(image_path):
            error_msg("Image file not found.")
            return
        
        try:
            pixel_data, img_w, img_h = image_parser.get_image(image_path)
            child_key = _derive_keys(pixel_data, "sha3_512")
        except ValueError as e:
            error_msg(str(e))
            return
    
    elif choice == "2":
        # From existing key file
        print("\n  Enter path to key file (PEM, JSON, or JWK):")
        try:
            key_path = input("  Key file path: ").strip().strip('"').strip("'")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        
        if not key_path or not os.path.isfile(key_path):
            error_msg("Key file not found.")
            return
        
        try:
            child_key = _read_key_file(key_path)
        except ValueError as e:
            error_msg(str(e))
            return
    else:
        error_msg("Invalid choice.")
        return
    
    # Generate X25519 keypair
    checksum = key_derive.compute_checksum(child_key[:32])
    print(f"\n  [OK] X25519 keypair generated")
    print(f"  Checksum: {checksum}")
    
    # Export options
    if _ask("\n  Save keypair to files?", default_val="y"):
        priv_path = f"x25519_priv_{checksum[:8]}.pem"
        pub_path = f"x25519_pub_{checksum[:8]}.pub"
        
        counter = 1
        while os.path.exists(priv_path):
            priv_path = f"x25519_priv_{checksum[:8]}_{counter}.pem"
            pub_path = f"x25519_pub_{checksum[:8]}_{counter}.pub"
            counter += 1
        
        meta = {"created_at": datetime.now(timezone.utc).isoformat()}
        key_export.write_x25519_keypair(child_key[:32], priv_path, pub_path, meta)
        print(f"  Private key: {os.path.abspath(priv_path)}")
        print(f"  Public key:  {os.path.abspath(pub_path)}")


def _interactive_sign_message() -> None:
    """Interactive message signing."""
    print("\n" + "="*60)
    print("  SIGN MESSAGE")
    print("="*60)
    
    print("\n  Enter path to Ed25519 private key file:")
    try:
        key_path = input("  Key file path: ").strip().strip('"').strip("'")
    except (EOFError, KeyboardInterrupt):
        print()
        return
    
    if not key_path or not os.path.isfile(key_path):
        error_msg("Key file not found.")
        return
    
    try:
        key_bytes = _read_key_file(key_path)
    except ValueError as e:
        error_msg(str(e))
        return
    
    from entropygarden import ed25519
    
    try:
        sk = ed25519.generate_signing_key(key_bytes[:32])
    except Exception as e:
        error_msg(f"Invalid key: {e}")
        return
    
    print("\n  Enter message to sign (or path to file):")
    try:
        msg_input = input("  Message: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    
    # Try to read as file first
    message = None
    if os.path.isfile(msg_input):
        try:
            message = Path(msg_input).read_bytes()
            log(f"Read message from file: {msg_input}")
        except Exception:
            message = msg_input.encode()
    else:
        message = msg_input.encode()
    
    try:
        sig = sk.sign(message)
        sig_b64 = base64.b64encode(sig).decode()
        
        print(f"\n  [OK] Message signed")
        print(f"  Signature (base64):")
        print(f"  {sig_b64}")
        
        # Ask to save
        if _ask("\n  Save signature to file?", default_val="y"):
            output_path = "signature.sig"
            counter = 1
            while os.path.exists(output_path):
                output_path = f"signature_{counter}.sig"
                counter += 1
            
            Path(output_path).write_text(sig_b64)
            print(f"  Saved to: {os.path.abspath(output_path)}")
    except Exception as e:
        error_msg(f"Signing failed: {e}")


def _interactive_verify_signature() -> None:
    """Interactive signature verification."""
    print("\n" + "="*60)
    print("  VERIFY SIGNATURE")
    print("="*60)
    
    print("\n  Enter path to Ed25519 public key file:")
    try:
        key_path = input("  Key file path: ").strip().strip('"').strip("'")
    except (EOFError, KeyboardInterrupt):
        print()
        return
    
    if not key_path or not os.path.isfile(key_path):
        error_msg("Key file not found.")
        return
    
    try:
        pub_key = _read_key_file(key_path)
    except ValueError as e:
        error_msg(str(e))
        return
    
    from entropygarden import ed25519
    
    try:
        vk = ed25519.Ed25519VerifyingKey(pub_key[:32])
    except Exception as e:
        error_msg(f"Invalid public key: {e}")
        return
    
    print("\n  Enter message (or path to file):")
    try:
        msg_input = input("  Message: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    
    message = None
    if os.path.isfile(msg_input):
        try:
            message = Path(msg_input).read_bytes()
            log(f"Read message from file: {msg_input}")
        except Exception:
            message = msg_input.encode()
    else:
        message = msg_input.encode()
    
    print("\n  Enter signature (base64 or path to signature file):")
    try:
        sig_input = input("  Signature: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    
    try:
        sig_b64 = _read_text_or_file(sig_input)
        sig = base64.b64decode(sig_b64)
    except Exception:
        error_msg("Invalid base64 signature.")
        return
    
    try:
        result = vk.verify(sig, message)
        if result:
            log("Signature VERIFIED - Message is authentic", color="green")
        else:
            error_msg("Verification FAILED - Signature is invalid")
    except Exception as e:
        error_msg(f"Verification error: {e}")


def _interactive_key_rotation() -> None:
    """Interactive key rotation."""
    print("\n" + "="*60)
    print("  KEY ROTATION")
    print("="*60)
    
    print("\n  Enter path to parent key file:")
    try:
        key_path = input("  Key file path: ").strip().strip('"').strip("'")
    except (EOFError, KeyboardInterrupt):
        print()
        return
    
    if not key_path or not os.path.isfile(key_path):
        error_msg("Key file not found.")
        return
    
    try:
        parent_key = _read_key_file(key_path)
    except Exception as e:
        error_msg(f"Failed to read key: {e}")
        return
    
    print("\n  Enter rotation reason (e.g., 'scheduled rotation', 'compromised')")
    try:
        reason = input("  Reason: ").strip() or "manual rotation"
    except (EOFError, KeyboardInterrupt):
        print()
        return
    
    try:
        result = key_rotation.rotate_key(parent_key, reason)
        new_checksum = result["checksum"]
        
        print(f"\n  [OK] Key rotated successfully")
        print(f"  New checksum: {new_checksum}")
        print(f"  Reason: {reason}")
        
        # Ask to save
        if _ask("\n  Save rotated key to file?", default_val="y"):
            output_path = f"rotated_key_{checksum[:8]}.key" # Had to change extension to.key to avoid confusion with original key file 
            counter = 1
            while os.path.exists(output_path):
                output_path = f"rotated_key_{checksum[:8]}_{counter}.key"
                counter += 1

            meta = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "algorithm": "sha3_512",
                "source": os.path.basename(key_path),
                "rotation_reason": reason,
            }
            key_export.write_key(result["key"], output_path, "pem", meta)
            print(f"  Saved to: {os.path.abspath(output_path)}")
    except Exception as e:
        error_msg(f"Key rotation failed: {e}")


def _interactive_hmac_challenge() -> None:
    """Interactive HMAC challenge-response verification."""
    print("\n" + "=" * 60) # Possible render issue here hm but shouldnt affect functionality 
    print("  HMAC CHALLENGE/RESPONSE")
    print("=" * 60)
    
    print("\n  Options:")
    print("    [1] Generate challenge (prove key ownership)")
    print("    [2] Respond to challenge")
    print("    [3] Verify response")
    print("    [0] Cancel")
    
    try:
        choice = input("\n  Select option (0-3): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    
    if choice == "0":
        return
    
    print("\n  Enter path to key file:")
    try:
        key_path = input("  Key file path: ").strip().strip('"').strip("'")
    except (EOFError, KeyboardInterrupt):
        print()
        return
    
    if not key_path or not os.path.isfile(key_path):
        error_msg("Key file not found.")
        return
    
    try:
        key = _read_key_file(key_path)
    except ValueError as e:
        error_msg(str(e))
        return
    
    if choice == "1":
        # Generate challenge
        try:
            chal = verify.generate_challenge(key)
            
            print(f"\n  [OK] Challenge generated")
            print(f"\n  Challenge (JSON):")
            print(json.dumps(chal, indent=2))
            
            # Ask to save
            if _ask("\n  Save challenge to file?", default_val="y"):
                output_path = "challenge.json"
                counter = 1
                while os.path.exists(output_path):
                    output_path = f"challenge_{counter}.json"
                    counter += 1
                
                Path(output_path).write_text(json.dumps(chal, indent=2))
                print(f"  Saved to: {os.path.abspath(output_path)}")
        except Exception as e:
            error_msg(f"Challenge generation failed: {e}")
    
    elif choice == "2":
        print("\n  Enter path to challenge JSON file:")
        try:
            chal_path = input("  Challenge file: ").strip().strip('"').strip("'")
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not chal_path or not os.path.isfile(chal_path):
            error_msg("Challenge file not found.")
            return

        try:
            chal = json.loads(Path(chal_path).read_text())
        except Exception as e:
            error_msg(f"Failed to read challenge: {e}")
            return

        try:
            response = verify.compute_response(key, chal)
            print(f"\n  [OK] Response computed")
            print(f"\n  Response (base64):")
            print(f"  {response}")

            if _ask("\n  Save response to file?", default_val="y"):
                output_path = "response.txt"
                counter = 1
                while os.path.exists(output_path):
                    output_path = f"response_{counter}.txt"
                    counter += 1

                Path(output_path).write_text(response, encoding="utf-8")
                print(f"  Saved to: {os.path.abspath(output_path)}")
        except Exception as e:
            error_msg(f"Response generation failed: {e}")

    elif choice == "3":
        # Verify the response
        print("\n  Enter path to challenge JSON file:")
        try:
            chal_path = input("  Challenge file: ").strip().strip('"').strip("'")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        
        if not chal_path or not os.path.isfile(chal_path):
            error_msg("Challenge file not found.")
            return
        
        try:
            chal = json.loads(Path(chal_path).read_text())
        except Exception as e:
            error_msg(f"Failed to read challenge: {e}")
            return
        
        print("\n  Enter response (base64 or path to response file):")
        try:
            response = _read_text_or_file(input("  Response: ").strip())
        except (EOFError, KeyboardInterrupt):
            print()
            return
        
        try:
            ok = verify.verify_response(key, chal, response)
            if ok:
                log("Response VERIFIED - Key ownership confirmed", color="green")
            else:
                error_msg("Verification FAILED - Invalid response")
        except Exception as e:
            error_msg(f"Verification error: {e}")


def _interactive_key_info() -> None:
    """Interactive key information display."""
    print("\n" + "="*60)
    print("  KEY INFORMATION")
    print("="*60)
    
    print("\n  Enter path to key file:")
    try:
        key_path = input("  Key file path: ").strip().strip('"').strip("'")
    except (EOFError, KeyboardInterrupt):
        print()
        return
    
    if not key_path or not os.path.isfile(key_path):
        error_msg("Key file not found.")
        return
    
    try:
        text = Path(key_path).read_text(encoding="utf-8")
        key = _read_key_file(key_path)
    except Exception as e:
        error_msg(f"Failed to read key: {e}")
        return
    
    meta = _parse_key_metadata(text)
    meta["key_length"] = len(key)
    meta["checksum"] = key_derive.compute_checksum(key)
    meta["fingerprint"] = key_derive.key_fingerprint(key)
    
    print("\n  Key Information:")
    print(json.dumps(meta, indent=2, default=str))
    
    if _ask("\n  Show hex dump?", default_val="n"):
        print()
        for line in render.hex_dump(key):
            print(line)


def _interactive_main_menu() -> None:
    """Main interactive menu with all features."""
    set_quiet(False)
    
    while True:
        print("\n" + "="*60)
        print("  ENTROPY GARDEN - MAIN MENU")
        print("="*60)
        print("\n  [1] Derive keys from image (Grow)")
        print("  [2] Generate Ed25519 keypair")
        print("  [3] Generate X25519 keypair")
        print("  [4] Sign a message")
        print("  [5] Verify a signature")
        print("  [6] Rotate a key")
        print("  [7] HMAC Challenge/Response")
        print("  [8] View key information")
        print("  [9] Export key to different format")
        print("  [0] Exit")
        print()
        
        try:
            choice = input("  Enter choice (0-9): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        
        if choice == "0":
            print("\n  Goodbye!\n")
            break
        elif choice == "1":
            cfg = config.load()
            _interactive_grow(cfg)
        elif choice == "2":
            _interactive_ed25519_keygen()
        elif choice == "3":
            _interactive_x25519_keygen()
        elif choice == "4":
            _interactive_sign_message()
        elif choice == "5":
            _interactive_verify_signature()
        elif choice == "6":
            _interactive_key_rotation()
        elif choice == "7":
            _interactive_hmac_challenge()
        elif choice == "8":
            _interactive_key_info()
        elif choice == "9":
            print("\n  Enter path to key file:")
            try:
                key_path = input("  Key file path: ").strip().strip('"').strip("'")
            except (EOFError, KeyboardInterrupt):
                print()
                continue
            
            if key_path and os.path.isfile(key_path):
                _show_export_menu(key_path, key_derive.compute_checksum(_read_key_file(key_path)))
        else:
            error_msg("Invalid choice. Please select 0-9.")


def _interactive_grow(cfg: dict) -> None:
    """Interactive flow where we want to process images in a loop until the user stops or quits the program"""
    set_quiet(False)
    images_processed = 0
    keys_generated = 0
    
    while True:
        more = _process_one_image(cfg)
        images_processed += 1
        keys_generated += 1
        if not more:
            break
        
    if images_processed > 0:
        print(f"\n  Session complete: {images_processed} image(s) processed, "
              f"{keys_generated} key pair(s) generated.")
        
    
def _build_parser() -> argparse.ArgumentParser:
    """Build argument parser with all subcommands."""
    p = argparse.ArgumentParser(
        description="Entropy Garden — derive cryptographic keys from image entropy")
    sub = p.add_subparsers(dest="command", help="Available commands")

    g = sub.add_parser("grow", help="Derive key hierarchy from an image (non-interactive)")
    g.add_argument("--input", required=True, action="append",
                   help="image file path (PPM/PNG)")
    g.add_argument("--path", default="m/44'/0'/0'", help="derivation path")
    g.add_argument("--output-private", help="private key output path")
    g.add_argument("--output-public", help="public key output path")
    g.add_argument("--algorithm", default="sha3_512",
                   choices=("sha3_512", "blake2b", "sha3_256"))
    g.add_argument("--key-type", default="symmetric",
                   choices=("symmetric", "ed25519", "x25519"),
                   help="key type (default: symmetric)")
    g.add_argument("--orientation", type=int, default=0,
                   choices=range(8),
                   help="image orientation 0-7 (default: 0=normal)")
    g.add_argument("--animate", action="store_true", help="animate visualization")
    g.add_argument("--dry-run", action="store_true", help="preview without writing")
    g.add_argument("--fingerprint", action="store_true", help="show key fingerprint")
    g.add_argument("--hex-dump", action="store_true", help="show hex dump of key")
    g.add_argument("--quality", action="store_true", help="show entropy quality")
    g.add_argument("--quiet", action="store_true", help="suppress log output")

    v = sub.add_parser("verify", help="Verify key ownership via HMAC challenge")
    v.add_argument("--key", required=True, help="path to key file")
    v.add_argument("--challenge-json", help="JSON challenge file")
    v.add_argument("--response", help="base64-encoded response to verify")

    p_cmd = sub.add_parser("prune", help="Rotate or set expiration on a key")
    p_cmd.add_argument("--parent-key", required=True, help="path to parent key file")
    p_cmd.add_argument("--path", default="m/44'/1'/0'", help="child derivation path")
    p_cmd.add_argument("--expires", help="expiration date (ISO 8601)")
    p_cmd.add_argument("--rotate", action="store_true", help="rotate the key")
    p_cmd.add_argument("--reason", default="manual", help="rotation reason")

    e = sub.add_parser("export", help="Export key to PEM, SSH, JSON, JWK, binary, or QR")
    e.add_argument("--key", required=True, help="path to key file")
    e.add_argument("--format", default="pem",
                   choices=("pem", "ssh", "json", "jwk", "binary", "qr", "qr-ascii", "qr-png"))
    e.add_argument("--output", required=True, help="output file path")

    gd = sub.add_parser("garden", help="Visualize image as ASCII art")
    gd.add_argument("--input", required=True, help="path to image file")
    gd.add_argument("--orientation", type=int, default=0,
                    choices=range(8),
                    help="image orientation 0-7 (default: 0=normal)")
    gd.add_argument("--width", type=int, default=0, help="output width (0=auto)")
    gd.add_argument("--height", type=int, default=0, help="output height (0=auto)")
    gd.add_argument("--quiet", action="store_true", help="suppress log output")

    info = sub.add_parser("info", help="Display metadata about a key file")
    info.add_argument("--key", required=True, help="path to key file")
    info.add_argument("--hex-dump", action="store_true", help="also show hex dump")

    sub.add_parser("init", help="Create default configuration file")

    return p


def _parse_ssh_public_key(blob: bytes) -> bytes:
    """Parse an SSH public key blob and extract the actual key bytes.
    
    SSH public key format is: ssh-ed25519 [base64-blob] where the blob structure is:
    - 4 bytes: length of "ssh-ed25519" (11)
    - N bytes: "ssh-ed25519" string  
    - 4 bytes: length of key (32 for ed25519)
    - 32 bytes: the actual public key
    """
    offset = 0
    
    # Parse key type string length
    if len(blob) < 4:
        raise ValueError("Invalid SSH format: too short")
    key_type_len = int.from_bytes(blob[offset:offset+4], "big")
    offset += 4
    
    # Parse and verify key type
    if offset + key_type_len > len(blob):
        raise ValueError("Invalid SSH format: key type overflow")
    key_type = blob[offset:offset+key_type_len]
    offset += key_type_len
    
    if key_type != b"ssh-ed25519":
        raise ValueError(f"Unsupported key type: {key_type.decode()}")
    
    # Parse public key length
    if offset + 4 > len(blob):
        raise ValueError("Invalid SSH format: missing key length")
    pub_key_len = int.from_bytes(blob[offset:offset+4], "big")
    offset += 4
    
    # Extract public key
    if offset + pub_key_len != len(blob):
        raise ValueError(f"Invalid SSH format: expected {pub_key_len} key bytes")
    
    return blob[offset:offset+pub_key_len]


def _read_key_file(path: str) -> bytes:
    """Read a key file, handling PEM, JSON, JWK, and SSH formats"""
    raw = Path(path).read_bytes()

    # Binary export format: 4-byte checksum prefix + 32-byte key.
    if len(raw) == 36:
        return raw[4:]
    if len(raw) == 32:
        return raw

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError(f"Cannot parse key file: {path}")

    # Try JSON format first.
    try:
        data = json.loads(text)
        if "k" in data and data.get("kty") == "oct":
            import base64 as _b64
            padded = data["k"] + "=" * (-len(data["k"]) % 4)
            return _b64.urlsafe_b64decode(padded)
        if "key" in data:
            return base64.b64decode(data["key"])
        if data.get("crv") == "X25519":
            field = "d" if "d" in data else "x" if "x" in data else "X" if "X" in data else None
            if field:
                import base64 as _b64
                value = data[field]
                padded = value + "=" * (-len(value) % 4)
                return _b64.urlsafe_b64decode(padded)
    except (json.JSONDecodeError, KeyError, Exception):
        pass

    # Try SSH format (ssh-ed25519 [base64]).
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("ssh-"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    blob = base64.b64decode(parts[1])
                    return _parse_ssh_public_key(blob)
                except Exception:
                    pass

    # PEM blocks: support raw base64 keys, Ed25519 PKCS#8 private keys, and SPKI public keys.
    pem_lines = []
    begin_line = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("-----BEGIN"):
            begin_line = stripped
            continue
        if stripped.startswith("-----END"):
            break
        if stripped and not stripped.startswith("#"):
            pem_lines.append(stripped)

    if pem_lines:
        try:
            der = base64.b64decode("".join(pem_lines))
        except Exception as exc:
            raise ValueError(f"Cannot parse key file: {path}") from exc

        if len(der) == 32:
            return der

        seed = _extract_pkcs8_seed(der)
        if seed is not None:
            return seed

        public_key = _extract_spki_public_key(der)
        if public_key is not None:
            return public_key

        if begin_line:
            raise ValueError(f"Unsupported PEM key format: {path}")

    raise ValueError(f"Cannot parse key file: {path}")


def _prepare_key_for_export(path: str, fmt: str) -> bytes:
    """Load key material and derive export bytes for formats like SSH."""
    key_bytes = _read_key_file(path)
    if fmt != "ssh":
        return key_bytes

    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    if '"crv"' in text and "X25519" in text:
        raise ValueError("SSH export is only supported for Ed25519 keys")
    if "ssh-ed25519" in text or "BEGIN PUBLIC KEY" in text:
        return key_bytes[:32]

    from entropygarden import ed25519
    return ed25519.generate_signing_key(key_bytes[:32]).public_key


def _extract_pkcs8_seed(der: bytes) -> bytes | None:
    """Extract a 32-byte private key seed from minimal PKCS#8 DER."""
    marker = b"\x06\x03\x2b\x65\x70"  # 1.3.101.112 Ed25519
    if marker not in der:
        return None

    # Accept both the simplified local encoding and common PKCS#8 wrapping.
    for prefix in (b"\x04\x20", b"\x04\x22\x04\x20"):
        idx = der.rfind(prefix)
        if idx != -1:
            start = idx + len(prefix)
            end = start + 32
            if end <= len(der):
                return der[start:end]
    return None


def _extract_spki_public_key(der: bytes) -> bytes | None:
    """Extract a 32-byte Ed25519 public key from SPKI DER."""
    marker = b"\x06\x03\x2b\x65\x70"  # 1.3.101.112 Ed25519
    if marker not in der:
        return None

    prefix = b"\x03\x21\x00"
    idx = der.rfind(prefix)
    if idx == -1:
        return None
    start = idx + len(prefix)
    end = start + 32
    if end <= len(der):
        return der[start:end]
    return None
    
    
def _parse_key_metadata(text: str) -> dict:
    """Extract metadata comments from a PEM or JSON key file"""
    meta = {}
    try:
        data = json.loads(text)
        if "k" in data and data.get("kty") == "oct":
            meta["format"] = "JWK"
            for field in ("path", "source", "orientation", "mode", "alg", "checksum"):
                if field in data:
                    meta[field] = data[field]
        elif "key" in data:
            meta["format"] = "JSON"
            for field in ("algorithm", "checksum", "path", "source", "orientation", "mode"):
                if field in data:
                    meta[field] = data[field]
            if "created_at" in data:
                meta["created_at"] = data["created_at"]
        elif data.get("crv") == "X25519":
            meta["format"] = "JSON"
            meta["curve"] = "X25519"
            meta["type"] = "private" if "d" in data else "public"
            for field in ("created_at", "source", "path", "orientation", "checksum"):
                if field in data:
                    meta[field] = data[field]
        return meta
    except (json.JSONDecodeError, KeyError):
        pass
    for line in text.splitlines():
        if line.startswith("# "):
            parts = line[2:].split(": ", 1)
            if len(parts) == 2:
                key, val = parts[0].strip().lower(), parts[1].strip()
                meta[key] = val
        elif line.startswith("-----BEGIN"):
            meta["format"] = "PEM"
    return meta


def _cmd_grow(args: argparse.Namespace) -> None:
    """Non interactive batch key derivation"""
    cfg = config.load()
    set_quiet(args.quiet or cfg.get("quiet", False))
    inputs = args.input

    for inp in inputs:
        log(f"Processing: {inp}")
        try:
            pixel_data, img_w, img_h = image_parser.get_image(inp)
        except ValueError as e:
            error_msg(str(e))
            continue

        try:
            info = image_parser.get_image_info(inp)
            log(f"{info['format']}  {human_size(info['file_size'])}  "
                f"{info['width']}x{info['height']}")
        except OSError:
            pass
        
        # Apply orientation
        if args.orientation > 0:
            pixel_data, img_w, img_h = image_parser.rotate_pixels(
                pixel_data, args.orientation, img_w, img_h)
            log(f"Orientation: {ORIENTATIONS[args.orientation]}")

        if args.quality:
            q = image_parser.entropy_quality_test(pixel_data)
            print(f"Entropy score: {q['score']}%, bits/byte: {q['bits_per_byte']}")

        child_key = _derive_keys(pixel_data, args.algorithm)
        
        if args.fingerprint:
            fp = key_derive.key_fingerprint(child_key)
            print(f"Fingerprint: {fp}")

        if args.hex_dump:
            for line in render.hex_dump(child_key):
                print(line)

        if args.dry_run:
            log(f"[DRY RUN] Would write private key to {args.output_private or '(none)'}")
            log(f"[DRY RUN] Would write public key to {args.output_public or '(none)'}")
            log(f"[DRY RUN] Checksum: {key_derive.compute_checksum(child_key)}")
            continue

        meta = {
            "algorithm": args.algorithm,
            "path": args.path,
            "source": inp,
            "orientation": ORIENTATIONS[args.orientation],
            "orientation_index": args.orientation,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        key_type = args.key_type
        if key_type == "symmetric":
            if args.output_private:
                key_export.write_key(child_key, args.output_private, "pem", meta)
            if args.output_public:
                pub = key_derive.hkdf_expand(child_key, b"public", 32)
                key_export.write_key(pub, args.output_public, "json", meta)
        elif key_type == "ed25519":
            from . import ed25519
            sk = ed25519.generate_signing_key(child_key[:32])
            priv_out = args.output_private or "priv_ed25519.key"
            pub_out = args.output_public or "pub_ed25519.pub"
            key_export.write_ed25519_keypair(sk.seed, priv_out, pub_out, meta)
        elif key_type == "x25519":
            priv_out = args.output_private or "priv_x25519.key"
            pub_out = args.output_public or "pub_x25519.pub"
            key_export.write_x25519_keypair(child_key[:32], priv_out, pub_out, meta)

    if not args.dry_run and len(inputs) > 0:
        print_complete(key_derive.compute_checksum(child_key))
        
        
def _cmd_verify(args: argparse.Namespace) -> None:
    """Verify load key and check HMAC challenge response"""
    key = _read_key_file(args.key)
    if args.challenge_json:
        challenge = json.loads(Path(args.challenge_json).read_text())
        ok = verify.verify_response(key, challenge, args.response or "")
        log(f"Verification: {'PASSED' if ok else 'FAILED'}",
            color="green" if ok else "red")
        if not ok:
            sys.exit(1)
    else:
        chal = verify.generate_challenge(key)
        print(json.dumps(chal, indent=2))
        
        
def _cmd_prune(args: argparse.Namespace) -> None:
    """Derive the child key with expiration or rotate the parent key"""
    cfg = config.load()
    parent = Path(args.parent_key).read_bytes()
    if args.rotate:
        result = key_rotation.rotate_key(parent, args.reason)
    elif args.expires:
        result = key_rotation.derive_with_expiration(parent, args.path, args.expires)
    else:
        result = key_rotation.derive_with_expiration(parent, args.path, "never")
    log(f"Child checksum: {result['checksum']}", color="yellow")
    print(json.dumps({k: v for k, v in result.items() if k != "key"},
                      indent=2, default=str))
    
    
def _cmd_export(args: argparse.Namespace) -> None:
    """Export - save key in the requested format"""
    key = _prepare_key_for_export(args.key, args.format)
    meta = {"created_at": datetime.now(timezone.utc).isoformat()}
    key_export.write_key(key, args.output, args.format, meta)
    print_complete(key_derive.compute_checksum(key))
    
    
def _cmd_garden(args: argparse.Namespace) -> None:
    """Garden: visualize image as ASCII art."""
    cfg = config.load()
    set_quiet(args.quiet or cfg.get("quiet", False))
    pixel_data, img_w, img_h = image_parser.get_image(args.input)

    if args.orientation > 0:
        pixel_data, img_w, img_h = image_parser.rotate_pixels(
            pixel_data, args.orientation, img_w, img_h)

    term = render.detect_terminal()
    w = args.width or min(term["width"], 60)
    h = args.height or min(term["height"] - 2, 16)

    print(f"  Orientation: {ORIENTATIONS[args.orientation]} ({img_w}x{img_h})")
    for line in render.render_image_as_ascii(pixel_data, img_w, img_h, w, h):
        print(f"  {line}")
        
    
def _cmd_info(args: argparse.Namespace) -> None:
    """Display all metadata about a key file by default"""
    text = Path(args.key).read_text(encoding ="utf-8")
    try:
        key = _read_key_file(args.key)
    except ValueError as e:
        error_msg(str(e))
        sys.exit(1)
        
    meta = _parse_key_metadata(text)
    meta["key_length"] = len(key)
    meta["checksum"] = key_derive.compute_checksum(key)
    meta["fingerprint"] = key_derive.key_fingerprint(key)

    print(json.dumps(meta, indent=2, default=str))

    if args.hex_dump:
        print()
        for line in render.hex_dump(key):
            print(line)
                
                
def _cmd_init(args: argparse.Namespace = None) -> None:
    """Create default config file"""
    p = Path.home() / ".entropygarden" / "config.json"
    config.save(config.DEFAULTS, str(p))
    log(f"Config written to {p}", color="green")
    
    
def main(argv=None) -> None:
    """Main entry point: interactive + subcommands for scripting if required"""
    print_banner()
    parser = _build_parser()

    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        try:
            _interactive_main_menu()
        except KeyboardInterrupt:
            print()
            return
        except Exception as e:
            error_msg(f"{type(e).__name__}: {e}")
            sys.exit(1)
        return
    
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return
    
    cfg = config.load()
    try:
        handlers = {
            "grow": _cmd_grow,
            "verify": _cmd_verify,
            "prune": _cmd_prune,
            "export": _cmd_export,
            "garden": _cmd_garden,
            "info": _cmd_info,
            "init": _cmd_init,
        }
        handlers[args.command](args)
    except KeyboardInterrupt:
        error_msg("Interrupted by user")
        sys.exit(130)
    except FileNotFoundError as e:
        error_msg(str(e))
        sys.exit(1)
    except ValueError as e:
        error_msg(str(e))
        sys.exit(1)
    except Exception as e:
        error_msg(f"{type(e).__name__}: {e}")
        sys.exit(1)
    
