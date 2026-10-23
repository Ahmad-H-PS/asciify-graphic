"""Media download and URL handling for images, videos, and YouTube streams."""

import hashlib
import mimetypes
import os
import re
import shutil
import sys
import tempfile
from typing import Optional, Tuple
from urllib.parse import urlparse

import imageio_ffmpeg
import requests

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".gif", ".ppm", ".pgm", ".svg"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v", ".3gp", ".ts"}

YOUTUBE_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "music.youtube.com",
}


def is_url(source: str) -> bool:
    """Return True if source string is an HTTP/HTTPS URL."""
    if not isinstance(source, str):
        return False
    clean = source.strip()
    return clean.startswith("http://") or clean.startswith("https://")


def is_youtube_url(url: str) -> bool:
    """Return True if URL is a YouTube video or shorts link."""
    if not is_url(url):
        return False
    try:
        parsed = urlparse(url.strip())
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain in {"youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"}
    except Exception:
        return False


def get_cache_dir() -> str:
    """Return cache directory for downloaded media."""
    cache_path = os.path.join(tempfile.gettempdir(), "asciify_cache")
    os.makedirs(cache_path, exist_ok=True)
    return cache_path


def get_url_hash(url: str) -> str:
    """Return SHA-256 hash prefix for URL caching."""
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:16]


def detect_media_type(path_or_url: str, content_type: Optional[str] = None) -> str:
    """Determine whether path or URL represents an image or a video."""
    if is_youtube_url(path_or_url):
        return "video"

    parsed = urlparse(path_or_url)
    ext = os.path.splitext(parsed.path)[1].lower()

    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in IMAGE_EXTENSIONS:
        return "image"

    if content_type:
        c_low = content_type.lower()
        if "video" in c_low or "application/vnd.apple.mpegurl" in c_low:
            return "video"
        if "image" in c_low:
            return "image"

    # Default to image
    return "image"


def download_direct_url(
    url: str,
    output_dir: Optional[str] = None,
    timeout: int = 25,
) -> Tuple[str, str]:
    """Download direct image or video URL.
    
    Returns:
        (downloaded_local_path, media_type)
    """
    target_dir = output_dir or get_cache_dir()
    url_hash = get_url_hash(url)

    # First check HEAD request for content-type and size
    content_type = ""
    try:
        head_resp = requests.head(url, allow_redirects=True, timeout=timeout)
        content_type = head_resp.headers.get("content-type", "")
    except Exception:
        pass

    media_type = detect_media_type(url, content_type)

    # Determine file extension
    parsed = urlparse(url)
    ext = os.path.splitext(parsed.path)[1].lower()
    if not ext or len(ext) > 5:
        ext = mimetypes.guess_extension(content_type.split(";")[0]) or (".mp4" if media_type == "video" else ".png")
        if ext == ".jpe":
            ext = ".jpg"

    cached_filename = f"{url_hash}{ext}"
    cached_path = os.path.join(target_dir, cached_filename)

    # Check if already cached and non-empty
    if os.path.isfile(cached_path) and os.path.getsize(cached_path) > 0:
        return cached_path, media_type

    # Stream download
    resp = requests.get(url, stream=True, timeout=timeout)
    resp.raise_for_status()

    # Re-verify content type if HEAD failed
    if not content_type:
        content_type = resp.headers.get("content-type", "")
        media_type = detect_media_type(url, content_type)

    temp_path = cached_path + ".tmp"
    with open(temp_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)

    if os.path.isfile(cached_path):
        os.remove(cached_path)
    os.rename(temp_path, cached_path)

    return cached_path, media_type


def ensure_ffmpeg_in_cache() -> str:
    """Ensure ffmpeg binary is available with standard executable name in cache directory and PATH."""
    cache_dir = get_cache_dir()
    is_win = sys.platform == "win32"
    exe_name = "ffmpeg.exe" if is_win else "ffmpeg"
    target_ffmpeg = os.path.join(cache_dir, exe_name)

    if not os.path.isfile(target_ffmpeg) or os.path.getsize(target_ffmpeg) == 0:
        src = imageio_ffmpeg.get_ffmpeg_exe()
        try:
            os.link(src, target_ffmpeg)
        except Exception:
            try:
                shutil.copyfile(src, target_ffmpeg)
            except Exception:
                target_ffmpeg = src

    # Also prepend cache directory to PATH for any subprocess lookups
    path_env = os.environ.get("PATH", "")
    if cache_dir not in path_env:
        os.environ["PATH"] = cache_dir + os.pathsep + path_env

    return target_ffmpeg


def download_youtube_video(
    url: str,
    output_dir: Optional[str] = None,
    max_resolution: int = 720,
) -> str:
    """Download video from YouTube or supported streaming platforms via yt-dlp.
    
    Returns:
        downloaded_local_path
    """
    if yt_dlp is None:
        raise ImportError(
            "yt-dlp is required for YouTube video downloads. Please install it with 'pip install yt-dlp'."
        )

    target_dir = output_dir or get_cache_dir()
    ffmpeg_bin = ensure_ffmpeg_in_cache()

    # Check if video was already downloaded in cache
    # First extract info without downloading to get ID
    ydl_info_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }
    video_id = None
    try:
        with yt_dlp.YoutubeDL(ydl_info_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_id = info.get("id")
    except Exception:
        pass

    if video_id:
        for candidate_ext in ("mp4", "mkv", "webm"):
            candidate_path = os.path.join(target_dir, f"{video_id}.{candidate_ext}")
            if os.path.isfile(candidate_path) and os.path.getsize(candidate_path) > 1000:
                return candidate_path

    # Download with yt-dlp restricting resolution for speed
    outtmpl = os.path.join(target_dir, "%(id)s.%(ext)s")
    ydl_opts = {
        "format": f"bestvideo[height<={max_resolution}][ext=mp4]+bestaudio[ext=m4a]/best[height<={max_resolution}]/best",
        "outtmpl": outtmpl,
        "ffmpeg_location": ffmpeg_bin,
        "merge_output_format": "mp4",
        "quiet": False,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(result)
        # Check if merged to .mp4
        mp4_version = os.path.splitext(filename)[0] + ".mp4"
        if os.path.isfile(mp4_version):
            return mp4_version
        if os.path.isfile(filename):
            return filename

    # Search target_dir for created file with video_id
    if video_id:
        for f in os.listdir(target_dir):
            if f.startswith(video_id):
                return os.path.join(target_dir, f)

    raise RuntimeError(f"Failed to locate downloaded YouTube video for URL: {url}")


def resolve_media_input(input_source: str, force_type: Optional[str] = None) -> Tuple[str, str]:
    """Resolve input path or URL to an accessible local media file.
    
    Returns:
        (local_file_path, media_type) where media_type is 'image' or 'video'
    """
    clean_input = input_source.strip()

    if not is_url(clean_input):
        if not os.path.exists(clean_input):
            raise FileNotFoundError(f"Input file not found: {clean_input}")

        # Local file
        ext = os.path.splitext(clean_input)[1].lower()
        if ext in VIDEO_EXTENSIONS:
            media_type = "video"
        elif ext in IMAGE_EXTENSIONS:
            media_type = "image"
        else:
            media_type = force_type or "image"

        return os.path.abspath(clean_input), media_type

    # URL Input
    if is_youtube_url(clean_input) or force_type == "video":
        if is_youtube_url(clean_input):
            downloaded = download_youtube_video(clean_input)
            return downloaded, "video"
        else:
            downloaded, mtype = download_direct_url(clean_input)
            return downloaded, "video"

    # Direct URL
    downloaded, mtype = download_direct_url(clean_input)
    return downloaded, (force_type or mtype)
