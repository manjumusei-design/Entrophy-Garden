#!/usr/bin/env python
"""Entry point for PyInstaller executable"""
import sys
from pathlib import Path

# Add the current directory to path so entropygarden can be imported
sys.path.insert(0, str(Path(__file__).parent))

from entropygarden.cli import main

if __name__ == "__main__":
    main()
