"""Configuration data structures for ASCII conversion and rendering."""

from dataclasses import dataclass, field
from typing import Optional, Tuple, Union
import re


def parse_color(color_val: Union[str, Tuple[int, int, int]]) -> Tuple[int, int, int]:
    """Parse color into (R, G, B) tuple.
    
    Supports:
      - Hex strings: "#RRGGBB", "RRGGBB", "#RGB"
      - Named colors: "white", "black", "green", "matrix", "amber", "cyan", "red", "blue", "yellow"
      - Tuples: (r, g, b)
    """
    if isinstance(color_val, (tuple, list)):
        return (int(color_val[0]), int(color_val[1]), int(color_val[2]))

    named = {
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "gray": (128, 128, 128),
        "grey": (128, 128, 128),
        "dark": (14, 17, 23),
        "matrix": (0, 255, 85),
        "amber": (255, 176, 0),
        "cyan": (0, 229, 255),
        "red": (255, 60, 60),
        "green": (50, 220, 50),
        "blue": (60, 120, 255),
        "yellow": (255, 230, 50),
        "magenta": (230, 50, 230),
        "orange": (255, 140, 0),
    }

    clean = color_val.strip().lower()
    if clean in named:
        return named[clean]

    if clean.startswith("#"):
        clean = clean[1:]

    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)

    if len(clean) == 6 and re.match(r"^[0-9a-f]{6}$", clean):
        return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))

    return (255, 255, 255)


@dataclass
class AsciiConfig:
    """Settings controlling ASCII conversion and output rendering."""
    # Dimensions
    width: Optional[int] = 100
    height: Optional[int] = None
    char_aspect: float = 0.52  # Width/height ratio of typical monospace fonts

    # Character set
    charset: str = "standard"
    invert: bool = False

    # Color options
    color_mode: str = "color"  # "color", "grayscale", "monochrome", "matrix", "amber", "cyan"
    fg_color: Tuple[int, int, int] = (255, 255, 255)
    bg_color: Tuple[int, int, int] = (14, 17, 23)  # Dark background
    sample_bg: bool = False

    # Image adjustments
    brightness: float = 1.0
    contrast: float = 1.0
    gamma: float = 1.0
    edge_detect: bool = False
    edge_weight: float = 0.35

    # Rendering (image/video rasterization)
    font_size: int = 16
    font_path: Optional[str] = None
    line_spacing: int = 0

    def get_effective_colors(self) -> Tuple[str, Tuple[int, int, int], Tuple[int, int, int]]:
        """Return (mode, fg_color, bg_color) taking presets into account."""
        mode = self.color_mode.lower()
        bg = self.bg_color

        if mode == "matrix":
            return ("monochrome", (0, 255, 85), (5, 15, 5))
        elif mode == "amber":
            return ("monochrome", (255, 176, 0), (20, 12, 0))
        elif mode == "cyan":
            return ("monochrome", (0, 229, 255), (0, 15, 25))
        elif mode in ("grayscale", "gray", "mono", "white"):
            return ("grayscale", self.fg_color, bg)
        elif mode == "monochrome":
            return ("monochrome", self.fg_color, bg)
        else:
            return ("color", self.fg_color, bg)
