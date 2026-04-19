
"""CLI entry point"""
import argparse
import base64
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from entropygarden import key_derive, config, render, key_export, image_parser, verify, key_rotation
from entropygarden.cli_output import (print_banner, print_complete, log, error_msg, set_quiet, human_size)


DETERMINISTIC_PATHS = [
    "m/44'/0'/0'",
    "m/44'/0'/1'",
    "m/44'/0'/2'",
    "m/44'/0'/3'",
    "m/44'/1'/0'",
    "m/44'/1'/1'",
    "m/44'/2'/0'",
    "m/44'/2'/1'",
    "m/48'/0'/0'",
    "m/48'/0'/1'",
    "m/48'/1'/0'",
    "m/48'/1'/1'",
]


def _ask(prompt: str, default_val: str = "y") -> bool:
    """Asks a yes or no question, returns true for yes"""
    default_label = "[Y/n]" if default_val == "y" else "[y/N]"
    try:
        answer = input(f" {prompt} {default_label}").strip().lower()
        if not answer:
            return default_val == "y"
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    
    
def _find_image_in_dir(directory: str) -> str:
    """Finds the first image file in a directory if it is a ppm or png"""
    import glob
    for ext in ("*.ppm", "*.png", "*.PPM", "*.PNG"):
        matches = glob.glob(os.path.join(directory, ext))
        if matches:
            return matches[0]
    return ""


def _show_keys(hash_data: bytes, path: str, nonce: bytes = None,
               use_random: bool = False) -> dict:
    """Derives and display keys for the given hash data and derivation path"""
    if use_random:
        if nonce is None:
            nonce = image_parsere.generate_nonce(32)
        entropy = image_parser.mix_randomness(hash_data, nonce)
        master_key = key_derive.derive_master(entropy)
    else:
        master_key = key_derive.derive_master(hash_data)
        
    child_key = key_derive.derive_child(master_key, path)
    fp = key_derive.key_fingerprint(child_key)
    cs = key_derive.compute_checksum(child_key)
    
    return {
        "child_key": child_key,
        "path": path,
        "nonce": nonce,
        "checksum": cs,
        "fingerprint": fp,
    }
    
    
def _process_one_image(cfg: dict) -> bool:
    """Process a single image, prompt for the path, show metadata then derive keys and offer the user a save
        
    Returns True if the user wants to process another image"""
        
    print()
    print (" Drag and drop an image file here or type the path.")
    print(" (PPM AND PNG SUPPORTED!)")
    print()

    try: 
        image_path = input(" Image path:").strip().strip('"').strip("'")
    except (EOFError, KeyboardInterrupt):
        print()
        return False
        
    if not image_path:
        found = _find_image_in_dir(".")
        if found:
            image_path = found
            log(f"Found image: {found}")
        else:
            error_msg("No image specified and none found in the current directory youre in")
            return False
               
        if not os.path.is file(image_path):
            error_msg(f"File not found: {image_path}")
            return False
        
        # Show image metadata
        try:
            info = image_parser.get_image_info(image_path)
        except OSError as e:
            error_msg(f"Cannot read image info: {e}")
            return False 

    print(f"\n  Image: {os.path.basename(image_path)}")
    print(f"  Format: {info['format']}  |  Size: {human_size(info['file_size'])}  |  "
          f"Dimensions: {info['width']}x{info['height']}")

    try:
        pixel_data = image_parser.parse_image(image_path)
    except ValueError as e:
        error_msg(str(e))
        return False
    
    hash_data = image_parser.extract_entropy(pixel_data, cfg.get("algorithm", "sha_3_512"))
    
    quality = image_parser.entropy_quality_test(pixel_data)
    print(f"  Entropy score: {quality['score']}%  |  Bits/byte: {quality['bits_per_byte']}")

    use_random = _ask("Use randomness? This is where the same image can produce different keys each time)",
                      default_val="n")
    
    if use_random:
        nonce = image_parser.generate_nonce(32)
        print(f" Random nonce: {nonce.hex()}")
        print(" (Each reroll will generate a new random nonce)")
        
    reroll_count = 0
    current = None
    mode_label = "Random" if use_random else "Deterministic"
    
    if use_random:
        current = _show_keys(hash_data, DETERMINISTIC_PATHS[0], use_random=True)
    else:
        current = _show_keys(hash_data, DETERMINISTIC_PATHS[0], use_random=False)
        
    while True:
        print()
        term = render.detect_terminal()
        w = min(term["width"] -2, 50)
        h = min(term["height"] -10, 10)
        if h <3:
            h =3
        if w < 10:
            w = 10
            
        for line in render.render_glyphs(hash_data, w, h):
                print(f" {line}")

        print(f"\n  Mode:       {mode_label}")
        print(f"  Path:       {current['path']}")
        if current['nonce']:
            print(f"  Nonce:      {current['nonce'].hex()}")
        print(f"  Checksum:   {current['checksum']}")
        print(f"  Fingerprint: {current['fingerprint']}")
        
        if _ask("Reroll keys?", default_val="y"):
            reroll_count += 1
            if use_random:
                current = _show_keys(hash_data, DETERMINISTIC_PATHS[0],
                                     use_random=True)
            else:
                path_idx = reroll_count % len(DETERMINISTIC_PATHS)
                current = _show_keys(hash_data, DETERMINISTIC_PATHS[path_idx],
                                     use_random=False)
            print(f"\n --- Reroll #{reroll_count} ---")
            continue
        break

    print()
    if _ask("Save key pair to current folder?", default_val="y"):
        meta = {
            "algorithm": cfg.get("algorithm", "sha3_512"),
            "path": current["path"],
            "source": os.path.basename(image_path),
            "mode": "random" if use_random else "deterministic",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if current["nonce"]:
            meta["nonce"] = current["nonce"].hex()
            
        priv_path = "priv.key"
        pub_path = "pub.json"
        
        counter = 1
        while os.path.exists(priv_path):
            priv_path = f"priv_{counter}.key"
            pub_path = f"pub_{counter}.json"
            counter += 1
            
        key_export.write_key(current["child_key"], priv_path, "pem", meta)
        pub_key = key_derive.hkdf_expand(current["child_key"], b"public", 32)
        key_export.write_key(pub_key, pub_path, "json", meta)
        
        print(f"\n Private key saved: {os.path.abspath(priv_path)}")
        print (f" Public key saved: {os.path.abspath(pub_path)}")
        print_complete(current["checksum"])
    else:
        print("\n Keys not saved.")
        
        print()
        return _ask("Process another image?", default_val="n")
    
    
def _interactive_grow(cfg: dict) -> None:
    """Interctive flow where user will be in a loop to process images until the user explicitly stops"""
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
            print(f"\n Session complete: {images_processed} images(s) processed."
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
    g.add_argument("--animate", action="store_true", help="animate visualization")
    g.add_argument("--dry-run", action="store_true", help="preview without writing")
    g.add_argument("--fingerprint", action="store_true", help="show key fingerprint")
    g.add_argument("--hex-dump", action="store_true", help="show hex dump of key")
    g.add_argument("--quality", action="store_true", help="show entropy quality")
    g.add_argument("--random", action="store_true",
                   help="add random nonce for unique keys each run")
    g.add_argument("--nonce",
                   help="hex-encoded nonce for reproducible random mode")
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

    e = sub.add_parser("export", help="Export key to PEM, JSON, JWK, binary, or QR")
    e.add_argument("--key", required=True, help="path to key file")
    e.add_argument("--format", default="pem",
                   choices=("pem", "json", "jwk", "binary", "qr"))
    e.add_argument("--output", required=True, help="output file path")

    gd = sub.add_parser("garden", help="Visualize image entropy as ASCII art")
    gd.add_argument("--input", required=True, help="path to image file")
    gd.add_argument("--mode", default="glyph", choices=("heatmap", "glyph"))
    gd.add_argument("--animate", action="store_true", help="animate the visualization")
    gd.add_argument("--width", type=int, default=0, help="output width (0=auto)")
    gd.add_argument("--height", type=int, default=0, help="output height (0=auto)")
    gd.add_argument("--quiet", action="store_true", help="suppress log output")

    info = sub.add_parser("info", help="Display metadata about a key file")
    info.add_argument("--key", required=True, help="path to key file")
    info.add_argument("--hex-dump", action="store_true", help="also show hex dump")

    sub.add_parser("init", help="Create default configuration file")
    sub.add_parser("gui", help="Launch the graphical interface")

    return p


def _read_key_file(path:str) -> bytes:
    """Read a key file and handle the PEM, JSON and JWK formats"""
    text = Path(path).read_text(encoding="utf-8")
    # Try JSON / JWK
    try:
        data = json.loads(text)
        if "k" in data and data.get("kty") == "oct":
            # JWK: base64url-decode the k field
            import base64 as _b64
            padded = data["k"] + "=" * (4 - len(data["k"]) % 4)
            return _b64.urlsafe_b64decode(padded)
        if "key" in data:
            return base64.b64decode(data["key"])
    except (json.JSONDecodeError, KeyError, Exception):
        pass
    
    # Try PEM
    lines = []
    for line in text.splitlines():
        if not line.startswith("----") and not line.startswith("#"):
            lines.append(line.strip())
    try:
        return base64.b64decode("".join(lines))
    except Exception:
        raise ValueError(f"Cannot parse key file: {path}")
    
def _parse_key_metadata(text: str) -> dict:
    """Extract metadata comments from a PEM and JSON key files."""
    meta = {}
    # Try JSON / JWK first
    try:
        data = json.loads(text)
        if "k" in data and data.get("kty") == "oct":
            # JWK
            meta["format"] = "JWK"
            for field in ("path", "source", "nonce", "mode", "alg", "checksum"):
                if field in data:
                    meta[field] = data[field]
        elif "key" in data:
            # Our JSON format
            meta["format"] = "JSON"
            for field in ("algorithm", "checksum", "path", "source", "nonce", "mode"):
                if field in data:
                    meta[field] = data[field]
            if "created_at" in data:
                meta["created_at"] = data["created_at"]
        return meta
    except (json.JSONDecodeError, KeyError):
        pass
    # Parse PEM comments
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
    """Grow: non-interactive batch key derivation."""
    cfg = config.load()
    set_quiet(args.quiet or cfg.get("quiet", False))
    inputs = args.input

    for inp in inputs:
        log(f"Processing: {inp}")
        pixel_data = image_parser.parse_image(inp)

        # Show image info
        try:
            info = image_parser.get_image_info(inp)
            log(f"{info['format']}  {human_size(info['file_size'])}  "
                f"{info['width']}x{info['height']}")
        except OSError:
            pass

        hash_data = image_parser.extract_entropy(pixel_data, args.algorithm)

        if args.quality:
            q = image_parser.entropy_quality_test(pixel_data)
            print(f"Entropy score: {q['score']}%, bits/byte: {q['bits_per_byte']}")

        if args.animate:
            log("Animating entropy visualization...")
            render.animate_frames(hash_data, mode="glyph")

        nonce = None
        use_random = args.random
        if args.nonce:
            nonce = bytes.fromhex(args.nonce)
            use_random = True

        if use_random:
            if nonce is None:
                nonce = image_parser.generate_nonce(32)
            hash_data = image_parser.mix_randomness(hash_data, nonce, args.algorithm)
            log(f"Random nonce: {nonce.hex()}", color="cyan")
            
        master_key = key_derive.derive_master(hash_data)
        child_key = key_derive.derive_child(master_key, args. path)
        
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
            "create_at": datetime.now(timezone.utc).isoformat(),
        }
        if use_random and nonce:
            meta["mode"] = "random"
            meta["nonce"] = nonce.hex()
            
        key_type = args.key_type
        if key_type == "symmetric":
            if args.output_private:
                key_export.write_key(child_key, args.output_private, "pem", meta)
            if args.output_public:
                pub = key_derive.hkdf_expand(child_key, b"public", 32)
                key_export.write_key(pub, args.output_public, "json", meta)
        elif key_type == "ed25519":
            from entropygarden import ed25519
            sk = ed25519.generate_signing_key(child_key[:32])
            priv_out = args.output_private or "priv_ed25519.key"
            pub_out = args.output_public or "pub_ed25519.pub"
            key_export.write_ed25519_keypair(sk.seed, priv_out, pub_out, meta)
        elif key_type == "x22519":
            priv_out = args.output_private or "priv_x25519.key"
            pub_out = args.output_public or "pub_x25519.pub"
            key_export.write_x25519_keypair(child_key[:32], priv_out, pub_out, meta)
            
        if not args.dry_run and len(inputs) > 0:
            print_complete(key_derive.compute_checksum(child_key))
            
            
def _cmd_verify(args: argparse.Namespace) -> None:
    """Verify: load key and check HMAC challenge-response."""
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
    """Prune: derive child key with expiration or rotate parent key."""
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
    """Export to save the key in requested format"""
    key = _read_key_file(args.key)
    meta = {"created_at": datetime.now(timezone.utc).isoformat()}
    key_export.write_key(key, args.output, args.format, meta)
    print_complete(key_derive.compute_checksum(key))
    
    
def _cmd_garden(args: argparse.Namespace) -> None:
    """Visualize image entropy as ASCII art equivalent of the image"""
    cfg = config.load()
    set_quiet(args.quiet or cfg.get("quiet", False))
    pixel_data = image_parser.parse_image(args.input)
    hash_data = image_parser.exact_entropy(pixel_data, cfg.get("algorithm", "sha3_512"))
    term = render.detect_terminal()
    w = args.width or min(term["width"], 60)
    h = args.height or min(term["height"] -2, 16)
    if args.animate:
        render.animate_frames(hash_data, mode=args.mode)
    elif args.mode == "heatmap":
        for line in render.render_heatmap(hash_data, w, h):
            print(line)
    else:
        for line in render.render_glyphs(hash_data, w, h):
            print(line)
            
            
def _cmd_info(args: argparse.Namespace) -> None:
    """Dislpay all the metadata about a key file by default """
    text = Path(args.key).read_text(encoding="utf-8")
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
    """Create a default config file"""
    p = Path.home() / ".entropygarden" / "config.json"
    config.save(config.DEFAULTS, str(p))
    log(f"Config written to {p}", color="green")
    
    
def _cmd_gui(args: argparse.Namespace = None) -> None:
    """Launch the GUI (tries PyQt6 first, falls back to tkinter)."""
    try:
        from entropygarden import gui_qt
        gui_qt.run_gui()
    except ImportError:
        from entropygarden import gui_tk
        gui_tk.run_gui()


def main(argv=None) -> None:
    """Main entry point for the CLI"""
    print_banner()
    parser = _build_parser()
    
    if argv is None:
        argv = sys.argv[1:]
    
    if not argv:
        cfg = config.load()
        try:
            _interactive_grow(cfg)
        except KeyboardInterrupt:
            print()
            return
        except Exception as e:
            error_msg(f"{type(e).__name__}")
            sys.exit(1)
        return
    
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return
    
    cfg = config.load()
    try:
        if args.command == "gui":
            _cmd_gui()
            return
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