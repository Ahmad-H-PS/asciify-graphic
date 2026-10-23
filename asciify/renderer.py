"""Renderers for converting AsciiFrame objects to text, ANSI, HTML, and rasterized images."""

import html
from typing import Optional, Union
import numpy as np
from PIL import Image

from .converter import AsciiFrame
from .fonts import GlyphAtlas, load_font


class AsciiRenderer:
    """Renders AsciiFrame instances to text, ANSI, HTML, and high-res images."""

    def __init__(self, atlas: Optional[GlyphAtlas] = None):
        self._atlas = atlas

    def get_atlas(self, frame: AsciiFrame) -> GlyphAtlas:
        """Get or initialize cached glyph atlas matching frame configuration."""
        if self._atlas is not None:
            return self._atlas

        font, char_w, char_h = load_font(
            frame.config.font_path,
            size=frame.config.font_size
        )
        unique_chars = "".join(sorted(set("".join(frame.chars.flat) + " ")))
        self._atlas = GlyphAtlas(font, char_w, char_h, unique_chars)
        return self._atlas

    @staticmethod
    def to_text(frame: AsciiFrame) -> str:
        """Generate plain text ASCII art."""
        return "\n".join("".join(row) for row in frame.chars)

    @staticmethod
    def to_ansi(frame: AsciiFrame, color: bool = True) -> str:
        """Generate ANSI TrueColor string for terminal display or .ans files."""
        if not color or frame.config.color_mode in ("none", "plain"):
            return AsciiRenderer.to_text(frame)

        lines = []
        rows, cols = frame.shape
        colors = frame.colors
        chars = frame.chars

        for r in range(rows):
            line_parts = []
            prev_color = None

            for c in range(cols):
                char_str = chars[r, c]
                cur_color = tuple(colors[r, c])

                # Run-length optimization: only emit color code when color changes
                if cur_color != prev_color:
                    line_parts.append(f"\033[38;2;{cur_color[0]};{cur_color[1]};{cur_color[2]}m")
                    prev_color = cur_color

                line_parts.append(char_str)

            line_parts.append("\033[0m")  # Reset at end of line
            lines.append("".join(line_parts))

        return "\n".join(lines)

    @staticmethod
    def to_html(frame: AsciiFrame, title: str = "ASCII Graphic") -> str:
        """Generate a complete, self-contained HTML page displaying colored ASCII."""
        rows, cols = frame.shape
        colors = frame.colors
        chars = frame.chars
        _, _, bg = frame.config.get_effective_colors()
        bg_hex = f"#{bg[0]:02x}{bg[1]:02x}{bg[2]:02x}"

        html_lines = []
        for r in range(rows):
            span_parts = []
            prev_color = None
            buffer = []

            for c in range(cols):
                char_str = html.escape(chars[r, c])
                cur_color = (int(colors[r, c, 0]), int(colors[r, c, 1]), int(colors[r, c, 2]))

                if cur_color != prev_color:
                    if buffer:
                        hex_c = f"#{prev_color[0]:02x}{prev_color[1]:02x}{prev_color[2]:02x}"
                        span_parts.append(f'<span style="color:{hex_c}">{"".join(buffer)}</span>')
                        buffer = []
                    prev_color = cur_color

                buffer.append(char_str)

            if buffer:
                hex_c = f"#{prev_color[0]:02x}{prev_color[1]:02x}{prev_color[2]:02x}"
                span_parts.append(f'<span style="color:{hex_c}">{"".join(buffer)}</span>')

            html_lines.append("".join(span_parts))

        content = "\n".join(html_lines)

        template = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>
  body {{
    background-color: {bg_hex};
    margin: 0;
    padding: 24px;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    box-sizing: border-box;
    font-family: ui-monospace, 'Cascadia Code', 'Consolas', 'Courier New', monospace;
  }}
  pre.ascii-canvas {{
    background-color: {bg_hex};
    line-height: 1.0;
    letter-spacing: 0;
    font-size: 11px;
    font-family: inherit;
    white-space: pre;
    user-select: all;
    margin: auto;
    overflow-x: auto;
  }}
</style>
</head>
<body>
<pre class="ascii-canvas">{content}</pre>
</body>
</html>"""
        return template

    def to_image(self, frame: AsciiFrame, atlas: Optional[GlyphAtlas] = None) -> Image.Image:
        """Rasterize AsciiFrame into a high-resolution PIL Image."""
        if atlas is None:
            atlas = self.get_atlas(frame)

        rows, cols = frame.shape
        cw = atlas.char_w
        ch = atlas.char_h

        # Map frame characters to atlas mask indices
        # If atlas has char_to_idx, map characters quickly
        atlas_indices = np.zeros((rows, cols), dtype=np.int32)
        space_idx = atlas.space_idx

        # Fast lookup mapping
        for r in range(rows):
            for c in range(cols):
                atlas_indices[r, c] = atlas.char_to_idx.get(frame.chars[r, c], space_idx)

        # Retrieve masks: shape (rows, cols, ch, cw, 1) float32
        frame_masks = atlas.masks[atlas_indices]

        # Prepare colors
        fg = frame.colors[:, :, None, None, :].astype(np.float32)

        if frame.bg_colors is not None:
            bg = frame.bg_colors[:, :, None, None, :].astype(np.float32)
        else:
            _, _, default_bg = frame.config.get_effective_colors()
            bg = np.array(default_bg, dtype=np.float32)[None, None, None, None, :]

        # Alpha composite: (fg * alpha + bg * (1 - alpha))
        blended = (fg * frame_masks + bg * (1.0 - frame_masks)).astype(np.uint8)

        # Reshape (rows, cols, ch, cw, 3) -> (rows * ch, cols * cw, 3)
        final_array = blended.swapaxes(1, 2).reshape(rows * ch, cols * cw, 3)

        return Image.fromarray(final_array, mode="RGB")

    def save(self, frame: AsciiFrame, output_path: str) -> None:
        """Save AsciiFrame to disk, determining format from extension."""
        lower = output_path.lower()
        if lower.endswith(".txt"):
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(self.to_text(frame))
        elif lower.endswith((".ans", ".ansi")):
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(self.to_ansi(frame, color=True))
        elif lower.endswith((".html", ".htm")):
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(self.to_html(frame))
        elif lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff")):
            img = self.to_image(frame)
            img.save(output_path)
        else:
            # Default to text
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(self.to_text(frame))
