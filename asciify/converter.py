"""Core ASCII conversion engine using fast vectorized numpy routines."""

from dataclasses import dataclass
from typing import Optional, Union, Tuple
import cv2
import numpy as np
from PIL import Image

from .config import AsciiConfig
from .charsets import get_charset


@dataclass
class AsciiFrame:
    """Represents a converted frame with characters and color data."""
    chars: np.ndarray          # 2D array of unicode single-character strings (rows, cols)
    char_indices: np.ndarray   # 2D array of integers indexing the charset (rows, cols)
    colors: np.ndarray         # (rows, cols, 3) uint8 foreground RGB
    bg_colors: Optional[np.ndarray]  # (rows, cols, 3) uint8 background RGB or None
    width: int                 # Columns
    height: int                # Rows
    config: AsciiConfig

    @property
    def shape(self) -> Tuple[int, int]:
        return (self.height, self.width)

    def to_lines(self) -> list[str]:
        """Convert char array to list of string lines."""
        return ["".join(row) for row in self.chars]


class AsciiConverter:
    """Converts images into ASCII representations with color and edge support."""

    def __init__(self, config: Optional[AsciiConfig] = None):
        self.config = config or AsciiConfig()
        self._cached_charset = None
        self._cached_charset_str = ""
        self._cached_charset_arr = None

    def _get_charset_array(self) -> Tuple[str, np.ndarray]:
        charset_str = get_charset(self.config.charset, invert=self.config.invert)
        if charset_str != self._cached_charset_str:
            self._cached_charset_str = charset_str
            self._cached_charset_arr = np.array(list(charset_str), dtype="<U1")
        return self._cached_charset_str, self._cached_charset_arr

    def calculate_dimensions(self, orig_w: int, orig_h: int) -> Tuple[int, int]:
        """Calculate target (columns, rows) ASCII grid dimensions."""
        cfg = self.config
        if cfg.width is not None and cfg.height is not None:
            return max(1, cfg.width), max(1, cfg.height)

        if cfg.width is not None:
            cols = max(1, cfg.width)
            rows = max(1, int(orig_h / orig_w * cols * cfg.char_aspect))
            return cols, rows

        if cfg.height is not None:
            rows = max(1, cfg.height)
            cols = max(1, int(orig_w / orig_h * rows / cfg.char_aspect))
            return cols, rows

        # Default fallback
        cols = 100
        rows = max(1, int(orig_h / orig_w * cols * cfg.char_aspect))
        return cols, rows

    def convert_image(self, image_input: Union[str, Image.Image, np.ndarray]) -> AsciiFrame:
        """Convert an image (filepath, PIL Image, or numpy array) to an AsciiFrame."""
        # 1. Load image to RGB PIL Image
        if isinstance(image_input, str):
            pil_img = Image.open(image_input)
        elif isinstance(image_input, np.ndarray):
            # Check shape and channel order
            if image_input.ndim == 2:
                pil_img = Image.fromarray(image_input).convert("RGB")
            elif image_input.shape[2] == 4:
                pil_img = Image.fromarray(image_input, mode="RGBA")
            else:
                pil_img = Image.fromarray(image_input, mode="RGB")
        elif isinstance(image_input, Image.Image):
            pil_img = image_input
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")

        # Handle RGBA transparency compositing over background
        if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
            bg = Image.new("RGB", pil_img.size, self.config.bg_color)
            converted = pil_img.convert("RGBA")
            bg.paste(converted, mask=converted.split()[3])
            pil_img = bg
        else:
            pil_img = pil_img.convert("RGB")

        orig_w, orig_h = pil_img.size
        cols, rows = self.calculate_dimensions(orig_w, orig_h)

        # 2. Resize to ASCII grid dimensions
        resized_pil = pil_img.resize((cols, rows), resample=Image.Resampling.LANCZOS)
        rgb_arr = np.array(resized_pil, dtype=np.float32)

        # 3. Apply brightness, contrast, gamma adjustments
        if self.config.brightness != 1.0:
            rgb_arr *= self.config.brightness

        if self.config.contrast != 1.0:
            rgb_arr = (rgb_arr - 128.0) * self.config.contrast + 128.0

        if self.config.gamma != 1.0 and self.config.gamma > 0:
            rgb_arr = np.clip(rgb_arr, 0.0, 255.0)
            rgb_arr = 255.0 * ((rgb_arr / 255.0) ** (1.0 / self.config.gamma))

        rgb_arr = np.clip(rgb_arr, 0.0, 255.0).astype(np.uint8)

        # 4. Calculate luminance (ITU-R 601-2 standard)
        r = rgb_arr[:, :, 0].astype(np.float32)
        g = rgb_arr[:, :, 1].astype(np.float32)
        b = rgb_arr[:, :, 2].astype(np.float32)
        luma = 0.299 * r + 0.587 * g + 0.114 * b

        # 5. Optional edge detection overlay
        if self.config.edge_detect:
            gray_u8 = luma.astype(np.uint8)
            sobelx = cv2.Sobel(gray_u8, cv2.CV_32F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray_u8, cv2.CV_32F, 0, 1, ksize=3)
            edge_mag = np.hypot(sobelx, sobely)
            max_edge = np.max(edge_mag)
            if max_edge > 0:
                edge_norm = (edge_mag / max_edge) * 255.0
                luma = np.clip(luma + self.config.edge_weight * edge_norm, 0.0, 255.0)

        # 6. Map luminance to character ramp
        charset_str, charset_arr = self._get_charset_array()
        ramp_len = len(charset_str)

        # Map 0..255 -> 0..(ramp_len - 1)
        normalized = luma / 255.0
        indices = np.clip((normalized * (ramp_len - 1)).astype(np.int32), 0, ramp_len - 1)
        chars = charset_arr[indices]

        # 7. Compute colors based on color mode
        mode, default_fg, default_bg = self.config.get_effective_colors()

        if mode == "color":
            colors = rgb_arr.copy()
        elif mode == "grayscale":
            # Per-character grayscale intensity
            gray_vals = luma.astype(np.uint8)[:, :, None]
            colors = np.repeat(gray_vals, 3, axis=2)
        elif mode == "monochrome":
            # Shaded tint of default_fg based on luminance
            fg_base = np.array(default_fg, dtype=np.float32)
            norm_3d = (luma / 255.0)[:, :, None]
            colors = np.clip(fg_base * norm_3d, 0, 255).astype(np.uint8)
        else:
            colors = np.full((rows, cols, 3), default_fg, dtype=np.uint8)

        # Sample background if requested
        bg_colors = None
        if self.config.sample_bg:
            bg_colors = (rgb_arr * 0.2).astype(np.uint8)

        return AsciiFrame(
            chars=chars,
            char_indices=indices,
            colors=colors,
            bg_colors=bg_colors,
            width=cols,
            height=rows,
            config=self.config,
        )
