"""Path resolution and user directory management for exported ASCII media."""

import os
import sys
from typing import Optional


def get_user_folder(folder_name: str) -> str:
    """Retrieve standard user directory path (e.g. Videos, Pictures) cross-platform."""
    home = os.path.expanduser("~")

    # Check direct user folder (standard on Windows, macOS, and standard Linux desktops)
    candidate = os.path.join(home, folder_name)
    if os.path.isdir(candidate):
        return candidate

    # Check XDG user directories on Linux
    if sys.platform.startswith("linux"):
        xdg_var = f"XDG_{folder_name.upper()}_DIR"
        xdg_path = os.environ.get(xdg_var)
        if xdg_path and os.path.isdir(xdg_path):
            return xdg_path

    # Fallback: create candidate folder under home
    os.makedirs(candidate, exist_ok=True)
    return candidate


def get_asciify_export_dir(media_type: str = "image") -> str:
    """Return the dedicated ASCIIFY folder inside Videos or Pictures."""
    is_video = media_type.lower() in ("video", "mp4", "gif", "avi", "mkv", "mov", "webm")
    parent_folder = get_user_folder("Videos" if is_video else "Pictures")
    asciify_dir = os.path.join(parent_folder, "ASCIIFY")
    os.makedirs(asciify_dir, exist_ok=True)
    return asciify_dir


def is_video_extension(ext_or_path: str) -> bool:
    """Return True if path or extension indicates a video file."""
    root, ext = os.path.splitext(ext_or_path)
    clean_ext = ext if ext else root
    if not clean_ext.startswith("."):
        clean_ext = "." + clean_ext
    return clean_ext.lower() in {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".gif"}


def resolve_output_path(
    output: Optional[str],
    input_source: Optional[str] = None,
    media_type: str = "image",
    default_ext: Optional[str] = None,
) -> str:
    """Resolve destination file path.

    If output is omitted or just a filename (without directory path),
    it is saved into ~/Videos/ASCIIFY (for videos) or ~/Pictures/ASCIIFY (for pictures).
    """
    # Detect media type from extension if specified
    if output:
        _, ext = os.path.splitext(output)
        if ext and is_video_extension(ext):
            media_type = "video"

    export_dir = get_asciify_export_dir(media_type)

    if not output:
        base_name = "ascii_art"
        if input_source:
            # Clean basename if URL or path
            clean_name = os.path.basename(input_source.split("?")[0])
            base_name = os.path.splitext(clean_name)[0] or "ascii_art"
        ext = default_ext or (".mp4" if media_type == "video" else ".png")
        return os.path.join(export_dir, f"{base_name}_ascii{ext}")

    dir_part = os.path.dirname(output)
    # If output is a bare filename with no directory specified (e.g. "rickroll.mp4" or "art.png")
    if not dir_part:
        return os.path.join(export_dir, output)

    # User provided an explicit directory path (e.g. "./art.png" or "C:/custom/art.png")
    os.makedirs(dir_part, exist_ok=True)
    return os.path.abspath(output)
