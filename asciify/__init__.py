"""Asciify Graphic - Convert images and videos into ASCII art, graphics, and animations."""

from typing import Optional, Union
from PIL import Image

from .config import AsciiConfig, parse_color
from .converter import AsciiConverter, AsciiFrame
from .renderer import AsciiRenderer
from .video import AsciiVideoConverter, get_video_info, play_video_terminal
from .charsets import CHARSETS, get_charset
from .downloader import (
    download_direct_url,
    download_youtube_video,
    is_url,
    is_youtube_url,
    resolve_media_input,
)


__version__ = "1.1.0"


def convert_image(
    input_image: Union[str, Image.Image],
    output_path: Optional[str] = None,
    config: Optional[AsciiConfig] = None,
    **config_kwargs,
) -> Union[str, Image.Image, AsciiFrame]:
    """Convert an image (local file, URL, or PIL Image) to ASCII.
    
    If output_path is provided, writes the result to file (.txt, .ans, .html, .png, .jpg, etc.).
    Otherwise returns AsciiFrame if output_path is None.
    """
    if isinstance(input_image, str) and is_url(input_image):
        local_path, _ = resolve_media_input(input_image, force_type="image")
        input_image = local_path

    cfg = config or AsciiConfig(**config_kwargs) if config_kwargs else (config or AsciiConfig())
    converter = AsciiConverter(cfg)
    frame = converter.convert_image(input_image)
    renderer = AsciiRenderer()

    if output_path:
        renderer.save(frame, output_path)
        return output_path

    return frame


def convert_video(
    input_path: str,
    output_path: str,
    config: Optional[AsciiConfig] = None,
    fps: Optional[float] = None,
    max_frames: Optional[int] = None,
    frame_step: int = 1,
    keep_audio: bool = True,
    **config_kwargs,
) -> str:
    """Convert a video (local file, direct URL, or YouTube link) to an ASCII video or animated GIF."""
    if is_url(input_path):
        local_path, _ = resolve_media_input(input_path, force_type="video")
        input_path = local_path

    cfg = config or AsciiConfig(**config_kwargs) if config_kwargs else (config or AsciiConfig())
    video_converter = AsciiVideoConverter(cfg)
    return video_converter.convert_video(
        input_path=input_path,
        output_path=output_path,
        fps_override=fps,
        max_frames=max_frames,
        frame_step=frame_step,
        keep_audio=keep_audio,
    )


def play_video(
    input_path: str,
    config: Optional[AsciiConfig] = None,
    fps: Optional[float] = None,
    loop: bool = False,
    **config_kwargs,
) -> None:
    """Play a video (local file or URL / YouTube link) directly inside the terminal as real-time ASCII animation."""
    if is_url(input_path):
        local_path, _ = resolve_media_input(input_path, force_type="video")
        input_path = local_path

    cfg = config or AsciiConfig(**config_kwargs) if config_kwargs else (config or AsciiConfig())
    play_video_terminal(input_path, config=cfg, fps_override=fps, loop=loop)


__all__ = [
    "AsciiConfig",
    "AsciiConverter",
    "AsciiFrame",
    "AsciiRenderer",
    "AsciiVideoConverter",
    "CHARSETS",
    "convert_image",
    "convert_video",
    "download_direct_url",
    "download_youtube_video",
    "get_charset",
    "get_video_info",
    "is_url",
    "is_youtube_url",
    "parse_color",
    "play_video",
    "play_video_terminal",
    "resolve_media_input",
]
