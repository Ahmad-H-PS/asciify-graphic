"""Font resolution, metrics discovery, and glyph atlas caching."""

import os
import platform
from typing import Dict, List, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont


# Candidate monospace fonts by operating system
SYSTEM_FONTS = {
    "Windows": [
        "C:\\Windows\\Fonts\\CascadiaCode.ttf",
        "C:\\Windows\\Fonts\\CascadiaMono.ttf",
        "C:\\Windows\\Fonts\\consola.ttf",
        "C:\\Windows\\Fonts\\consolab.ttf",
        "C:\\Windows\\Fonts\\cour.ttf",
        "C:\\Windows\\Fonts\\lucon.ttf",
    ],
    "Linux": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
    ],
    "Darwin": [
        "/System/Library/Fonts/SFMono-Regular.otf",
        "/Library/Fonts/Courier New.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.dfont",
    ],
}


def find_system_font(custom_path: Optional[str] = None) -> Optional[str]:
    """Locate an available monospace font file on the host system."""
    if custom_path and os.path.isfile(custom_path):
        return custom_path

    system = platform.system()
    candidates: List[str] = SYSTEM_FONTS.get(system, [])

    # Also check other OS candidates just in case of non-standard environment
    for group in SYSTEM_FONTS.values():
        for path in group:
            if path not in candidates:
                candidates.append(path)

    for path in candidates:
        if os.path.isfile(path):
            return path

    return None


def load_font(font_path: Optional[str] = None, size: int = 16) -> Tuple[ImageFont.ImageFont, int, int]:
    """Load font and return (font, char_width, char_height)."""
    resolved_path = find_system_font(font_path)

    font: ImageFont.ImageFont
    if resolved_path:
        try:
            font = ImageFont.truetype(resolved_path, size=size)
        except Exception:
            font = ImageFont.load_default()
    else:
        try:
            font = ImageFont.load_default(size=size)  # type: ignore
        except Exception:
            font = ImageFont.load_default()

    # Calculate exact cell dimensions using standard test characters
    test_chars = "MWXgjqy018@"
    max_w = 0.0
    max_h = 0.0

    # Test width
    for ch in test_chars:
        try:
            w = font.getlength(ch)
            if w > max_w:
                max_w = w
        except AttributeError:
            bbox = font.getbbox(ch)
            w = bbox[2] - bbox[0]
            if w > max_w:
                max_w = w

    # Test height from metrics or bbox
    try:
        ascent, descent = font.getmetrics()
        max_h = ascent + descent
    except (AttributeError, TypeError):
        bbox = font.getbbox("Mjgqy|")
        max_h = bbox[3] - bbox[1] + 2

    char_w = max(1, int(round(max_w)))
    char_h = max(1, int(round(max_h)))

    return font, char_w, char_h


class GlyphAtlas:
    """Pre-rendered glyph alpha masks for ultra-fast vectorized ASCII rasterization."""

    def __init__(self, font: ImageFont.ImageFont, char_w: int, char_h: int, chars: str):
        self.font = font
        self.char_w = char_w
        self.char_h = char_h

        # Extract unique characters preserving order
        seen = set()
        unique_chars: List[str] = []
        for c in chars:
            if c not in seen:
                seen.add(c)
                unique_chars.append(c)
        if " " not in seen:
            unique_chars.append(" ")

        self.chars = unique_chars
        self.char_to_idx: Dict[str, int] = {c: i for i, c in enumerate(unique_chars)}
        self.space_idx = self.char_to_idx.get(" ", 0)

        # Pre-render alpha masks shape: (N, char_h, char_w, 1) float32
        n_chars = len(unique_chars)
        self.masks = np.zeros((n_chars, char_h, char_w, 1), dtype=np.float32)

        for i, c in enumerate(unique_chars):
            if c == " ":
                continue
            glyph_img = Image.new("L", (char_w, char_h), 0)
            draw = ImageDraw.Draw(glyph_img)
            # Center character horizontally if desired, or draw at 0,0
            draw.text((0, 0), c, fill=255, font=font)
            mask_arr = np.array(glyph_img, dtype=np.float32) / 255.0
            self.masks[i, :, :, 0] = mask_arr
