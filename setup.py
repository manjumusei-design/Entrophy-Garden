"""
Setup configuration for EntropyGarden
Cryptographic key derivation from image entropy
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="entropy-garden",
    version="1.0.0",
    author="EntropyGarden Contributors",
    description="Derive cryptographic keys from image entropy - RFC 8032/7748 compliant",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/manjumusei-design/Entrophy-Garden",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Security :: Cryptography",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "entropy-garden=entropygarden.cli:main",
        ],
    },
    extras_require={
        "crypto": ["cryptography>=3.4"],  # Optional 20x speedup
        "dev": ["pytest>=6.0", "pytest-cov>=2.12", "black>=21.0", "flake8>=3.9"],
    },
)
