"""Pillow 10+ removed Image.ANTIALIAS — restore aliases for MoviePy 1.x."""
from __future__ import annotations

from PIL import Image

if not hasattr(Image, "ANTIALIAS"):
    try:
        Image.ANTIALIAS = Image.Resampling.LANCZOS  # type: ignore[attr-defined]
    except AttributeError:
        Image.ANTIALIAS = Image.LANCZOS  # type: ignore[attr-defined]

if not hasattr(Image, "LINEAR"):
    try:
        Image.LINEAR = Image.Resampling.BILINEAR  # type: ignore[attr-defined]
    except AttributeError:
        Image.LINEAR = getattr(Image, "BILINEAR", 2)  # type: ignore[attr-defined]

if not hasattr(Image, "CUBIC"):
    try:
        Image.CUBIC = Image.Resampling.BICUBIC  # type: ignore[attr-defined]
    except AttributeError:
        Image.CUBIC = getattr(Image, "BICUBIC", 3)  # type: ignore[attr-defined]
