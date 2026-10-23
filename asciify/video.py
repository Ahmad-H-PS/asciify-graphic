"""Video processing, conversion to ASCII animation video/GIF, and live terminal playback."""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Callable, Generator, Optional, Tuple

import cv2
import imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image

from .config import AsciiConfig
from .converter import AsciiConverter, AsciiFrame
from .fonts import GlyphAtlas, load_font
from .renderer import AsciiRenderer


def get_video_info(video_path: str) -> dict:
    """Retrieve video metadata including FPS, total frames, resolution, and duration."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = total_frames / fps if fps > 0 else 0.0
    cap.release()

    return {
        "fps": fps,
        "total_frames": total_frames,
        "width": width,
        "height": height,
        "duration": duration,
    }


def iter_video_frames(
    video_path: str,
    max_frames: Optional[int] = None,
    frame_step: int = 1,
) -> Generator[Tuple[int, np.ndarray], None, None]:
    """Yield (frame_index, frame_rgb_array) from video."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")

    frame_idx = 0
    yielded = 0

    try:
        while True:
            ret, bgr = cap.read()
            if not ret:
                break

            if frame_idx % frame_step == 0:
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                yield frame_idx, rgb
                yielded += 1
                if max_frames and yielded >= max_frames:
                    break

            frame_idx += 1
    finally:
        cap.release()


def extract_audio(video_path: str, output_audio_path: str) -> bool:
    """Extract audio track from video using bundled ffmpeg. Returns True if successful."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "copy",
        output_audio_path,
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.isfile(output_audio_path) and os.path.getsize(output_audio_path) > 100:
            return True
    except Exception:
        pass

    # Fallback to AAC re-encoding if copy failed
    cmd_fallback = [
        ffmpeg_exe,
        "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "aac",
        output_audio_path,
    ]
    try:
        res = subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0 and os.path.isfile(output_audio_path) and os.path.getsize(output_audio_path) > 100
    except Exception:
        return False


def mux_audio_video(video_path: str, audio_path: str, output_path: str) -> bool:
    """Combine video and audio track into destination container."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output_path,
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0 and os.path.isfile(output_path) and os.path.getsize(output_path) > 0
    except Exception:
        return False


class AsciiVideoConverter:
    """Converts video files into ASCII animation videos or animated GIFs."""

    def __init__(self, config: Optional[AsciiConfig] = None):
        self.config = config or AsciiConfig()
        self.converter = AsciiConverter(self.config)
        self.renderer = AsciiRenderer()

    def convert_video(
        self,
        input_path: str,
        output_path: str,
        fps_override: Optional[float] = None,
        max_frames: Optional[int] = None,
        frame_step: int = 1,
        keep_audio: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """Convert input video to an ASCII animation video or GIF."""
        info = get_video_info(input_path)
        fps = fps_override or (info["fps"] / frame_step)
        total_frames = (
            min(max_frames, info["total_frames"] // frame_step)
            if max_frames
            else (info["total_frames"] // frame_step)
        )

        # Pre-initialize glyph atlas for consistent sizing and fast rendering
        font, char_w, char_h = load_font(self.config.font_path, size=self.config.font_size)
        charset_str, _ = self.converter._get_charset_array()
        unique_chars = "".join(sorted(set(charset_str + " ")))
        atlas = GlyphAtlas(font, char_w, char_h, unique_chars)
        self.renderer = AsciiRenderer(atlas)

        is_gif = output_path.lower().endswith(".gif")
        is_directory = os.path.isdir(output_path) or (not os.path.splitext(output_path)[1])

        if is_gif:
            return self._convert_to_gif(
                input_path, output_path, fps, max_frames, frame_step, atlas, total_frames, progress_callback
            )
        elif is_directory:
            return self._convert_to_frames_dir(
                input_path, output_path, max_frames, frame_step, atlas, total_frames, progress_callback
            )
        else:
            return self._convert_to_video_file(
                input_path, output_path, fps, max_frames, frame_step, keep_audio, atlas, total_frames, progress_callback
            )

    def _convert_to_video_file(
        self,
        input_path: str,
        output_path: str,
        fps: float,
        max_frames: Optional[int],
        frame_step: int,
        keep_audio: bool,
        atlas: GlyphAtlas,
        total_frames: int,
        progress_callback: Optional[Callable[[int, int], None]],
    ) -> str:
        # Determine temporary video output path if audio is to be merged
        temp_dir = tempfile.mkdtemp(prefix="asciify_")
        temp_video = os.path.join(temp_dir, "temp_ascii.mp4")
        temp_audio = os.path.join(temp_dir, "temp_audio.aac")

        target_writer_path = temp_video if keep_audio else output_path
        writer = None

        processed = 0
        try:
            for _, rgb_frame in iter_video_frames(input_path, max_frames=max_frames, frame_step=frame_step):
                ascii_frame = self.converter.convert_image(rgb_frame)
                rendered_img = self.renderer.to_image(ascii_frame, atlas=atlas)
                rendered_np = np.array(rendered_img)

                # Ensure even dimensions for video codecs
                h, w = rendered_np.shape[:2]
                pad_h = h % 2
                pad_w = w % 2
                if pad_h > 0 or pad_w > 0:
                    rendered_np = np.pad(
                        rendered_np,
                        ((0, pad_h), (0, pad_w), (0, 0)),
                        mode="constant",
                        constant_values=0,
                    )

                if writer is None:
                    writer = imageio.get_writer(
                        target_writer_path,
                        fps=fps,
                        format="FFMPEG",
                        mode="I",
                        macro_block_size=2,
                        codec="libx264",
                        quality=8,
                        pixelformat="yuv420p",
                    )

                writer.append_data(rendered_np)
                processed += 1
                if progress_callback:
                    progress_callback(processed, total_frames)

            if writer is not None:
                writer.close()
                writer = None

            # Handle audio muxing if needed
            if keep_audio:
                has_audio = extract_audio(input_path, temp_audio)
                if has_audio:
                    muxed = mux_audio_video(temp_video, temp_audio, output_path)
                    if not muxed:
                        # Fallback: copy video without audio if muxing failed
                        shutil.copy2(temp_video, output_path)
                else:
                    shutil.copy2(temp_video, output_path)

            return output_path
        finally:
            if writer is not None:
                try:
                    writer.close()
                except Exception:
                    pass
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    def _convert_to_gif(
        self,
        input_path: str,
        output_path: str,
        fps: float,
        max_frames: Optional[int],
        frame_step: int,
        atlas: GlyphAtlas,
        total_frames: int,
        progress_callback: Optional[Callable[[int, int], None]],
    ) -> str:
        gif_frames = []
        processed = 0

        for _, rgb_frame in iter_video_frames(input_path, max_frames=max_frames, frame_step=frame_step):
            ascii_frame = self.converter.convert_image(rgb_frame)
            rendered_img = self.renderer.to_image(ascii_frame, atlas=atlas)
            # Quantize for smaller GIF file size
            gif_frames.append(rendered_img.convert("P", palette=Image.Palette.ADAPTIVE, colors=128))
            processed += 1
            if progress_callback:
                progress_callback(processed, total_frames)

        if not gif_frames:
            raise ValueError("No frames could be extracted from input video.")

        duration_ms = int(1000.0 / fps)
        gif_frames[0].save(
            output_path,
            save_all=True,
            append_images=gif_frames[1:],
            duration=duration_ms,
            loop=0,
            optimize=True,
        )
        return output_path

    def _convert_to_frames_dir(
        self,
        input_path: str,
        output_dir: str,
        max_frames: Optional[int],
        frame_step: int,
        atlas: GlyphAtlas,
        total_frames: int,
        progress_callback: Optional[Callable[[int, int], None]],
    ) -> str:
        os.makedirs(output_dir, exist_ok=True)
        processed = 0

        for _, rgb_frame in iter_video_frames(input_path, max_frames=max_frames, frame_step=frame_step):
            ascii_frame = self.converter.convert_image(rgb_frame)
            rendered_img = self.renderer.to_image(ascii_frame, atlas=atlas)
            frame_filename = os.path.join(output_dir, f"frame_{processed:05d}.png")
            rendered_img.save(frame_filename)
            processed += 1
            if progress_callback:
                progress_callback(processed, total_frames)

        return output_dir


def play_video_terminal(
    video_path: str,
    config: Optional[AsciiConfig] = None,
    fps_override: Optional[float] = None,
    max_frames: Optional[int] = None,
    loop: bool = False,
) -> None:
    """Stream ASCII frames of video directly to terminal in real time."""
    cfg = config or AsciiConfig()

    # Determine terminal dimensions to fit screen perfectly
    term_cols, term_lines = shutil.get_terminal_size((80, 24))
    if cfg.width is None:
        cfg.width = max(20, term_cols - 2)
    if cfg.height is None:
        cfg.height = max(10, term_lines - 2)

    converter = AsciiConverter(cfg)
    info = get_video_info(video_path)
    fps = fps_override or info["fps"] or 24.0
    frame_duration = 1.0 / fps

    # Check for Windows kbhit
    is_windows = sys.platform == "win32"
    msvcrt = None
    if is_windows:
        try:
            import msvcrt
        except ImportError:
            pass

    # Hide cursor, enable ANSI
    sys.stdout.write("\033[?25l")  # Hide cursor
    sys.stdout.write("\033[2J")    # Clear entire screen
    sys.stdout.flush()

    try:
        while True:
            start_wall = time.monotonic()
            frame_idx = 0
            paused = False

            for _, rgb_frame in iter_video_frames(video_path, max_frames=max_frames):
                # Handle interactive keypresses
                if is_windows and msvcrt and msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key in (b"q", b"Q", b"\x1b"):  # 'q' or ESC
                        return
                    elif key == b" ":  # Space pause/resume
                        paused = not paused
                        while paused:
                            time.sleep(0.05)
                            if msvcrt.kbhit():
                                k2 = msvcrt.getch()
                                if k2 in (b"q", b"Q", b"\x1b"):
                                    return
                                elif k2 == b" ":
                                    paused = False
                                    start_wall = time.monotonic() - (frame_idx * frame_duration)

                # Convert and format ANSI string
                ascii_frame = converter.convert_image(rgb_frame)
                ansi_output = AsciiRenderer.to_ansi(ascii_frame, color=(cfg.color_mode != "none"))

                # Move cursor to home (top-left) without clearing to eliminate flicker
                sys.stdout.write("\033[H")
                sys.stdout.write(ansi_output)
                sys.stdout.flush()

                frame_idx += 1
                target_time = start_wall + (frame_idx * frame_duration)
                sleep_needed = target_time - time.monotonic()
                if sleep_needed > 0:
                    time.sleep(sleep_needed)

            if not loop:
                break
    except KeyboardInterrupt:
        pass
    finally:
        # Restore terminal state: reset colors, show cursor
        sys.stdout.write("\033[0m\033[?25h\n")
        sys.stdout.flush()
