"""Command-line interface for asciify-graphic."""

import os
import shutil
import sys
from typing import Optional

# Ensure standard streams use UTF-8 with graceful error handling on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table

from . import __version__
from .charsets import CHARSETS
from .config import AsciiConfig, parse_color
from .converter import AsciiConverter
from .renderer import AsciiRenderer
from .video import AsciiVideoConverter, get_video_info, play_video_terminal

console = Console()

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v"}


def is_video_file(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in VIDEO_EXTS


class SmartGroup(click.Group):
    """Custom Click Group that intelligently dispatches file paths to 'auto'."""

    def parse_args(self, ctx, args):
        # If the first non-option argument is not a command, prepend 'auto'
        for i, arg in enumerate(args):
            if not arg.startswith("-"):
                if arg not in self.commands:
                    args = list(args)
                    args.insert(i, "auto")
                break
        return super().parse_args(ctx, args)


@click.group(cls=SmartGroup)
@click.version_option(__version__, "-v", "--version", message="asciify-graphic version %(version)s")
def cli():
    """Asciify - Convert any image or video file into ASCII art, graphics, or animations."""
    pass


@cli.command("auto", hidden=True)
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", help="Output file path (.txt, .ans, .html, .png, .mp4, .gif, etc.)")
@click.option("-w", "--width", type=int, default=None, help="ASCII columns (width).")
@click.option("-H", "--height", type=int, default=None, help="ASCII rows (height).")
@click.option("-c", "--charset", default="standard", help="Character ramp preset or custom characters.")
@click.option("-m", "--color-mode", default="color", type=click.Choice(["color", "grayscale", "matrix", "amber", "cyan", "monochrome", "none"], case_sensitive=False))
@click.option("--invert/--no-invert", default=False, help="Invert character ramp.")
@click.option("--edge/--no-edge", default=False, help="Enable edge detection enhancement.")
@click.option("--brightness", type=float, default=1.0, help="Brightness adjustment factor.")
@click.option("--contrast", type=float, default=1.0, help="Contrast adjustment factor.")
@click.option("--gamma", type=float, default=1.0, help="Gamma factor.")
@click.option("--bg", "bg_color", default="#0e1117", help="Background color.")
@click.option("--fg", "fg_color", default="white", help="Foreground color for monochrome modes.")
@click.option("--font-size", type=int, default=16, help="Font size for rendered images and videos.")
@click.option("--font-path", type=click.Path(exists=True), default=None, help="Custom TTF/OTF font file.")
@click.option("--fps", type=float, default=None, help="Video FPS override.")
@click.option("--loop/--no-loop", default=False, help="Loop playback (for terminal video player).")
@click.option("--audio/--no-audio", default=True, help="Preserve audio in video conversions.")
@click.pass_context
def auto_cmd(
    ctx,
    input_file: str,
    output: Optional[str],
    width: Optional[int],
    height: Optional[int],
    charset: str,
    color_mode: str,
    invert: bool,
    edge: bool,
    brightness: float,
    contrast: float,
    gamma: float,
    bg_color: str,
    fg_color: str,
    font_size: int,
    font_path: Optional[str],
    fps: Optional[float],
    loop: bool,
    audio: bool,
):
    """Auto-detect input type and perform conversion or playback."""
    if is_video_file(input_file):
        if output:
            ctx.invoke(
                convert_video_cmd,
                input_video=input_file,
                output=output,
                width=width or 120,
                height=height,
                charset=charset,
                color_mode=color_mode,
                fps=fps,
                step=1,
                max_frames=None,
                audio=audio,
                invert=invert,
                edge=edge,
                brightness=brightness,
                contrast=contrast,
                gamma=gamma,
                bg_color=bg_color,
                fg_color=fg_color,
                font_size=font_size,
                font_path=font_path,
            )
        else:
            ctx.invoke(
                play_cmd,
                input_video=input_file,
                width=width,
                height=height,
                charset=charset,
                color_mode=color_mode,
                fps=fps,
                loop=loop,
                invert=invert,
                edge=edge,
                brightness=brightness,
                contrast=contrast,
            )
    else:
        ctx.invoke(
            convert_image_cmd,
            input_image=input_file,
            output=output,
            width=width,
            height=height,
            charset=charset,
            color_mode=color_mode,
            invert=invert,
            edge=edge,
            brightness=brightness,
            contrast=contrast,
            gamma=gamma,
            bg_color=bg_color,
            fg_color=fg_color,
            font_size=font_size,
            font_path=font_path,
        )


@cli.command("image")
@click.argument("input_image", type=click.Path(exists=True))
@click.option("-o", "--output", help="Output file path (.txt, .ans, .html, .png, .jpg, etc.). If omitted, prints to terminal.")
@click.option("-w", "--width", type=int, default=None, help="ASCII columns (width). Defaults to terminal width or 100.")
@click.option("-H", "--height", type=int, default=None, help="ASCII rows (height). Auto-calculated if omitted.")
@click.option("-c", "--charset", default="standard", help="Character ramp preset or custom characters.")
@click.option("-m", "--color-mode", default="color", type=click.Choice(["color", "grayscale", "matrix", "amber", "cyan", "monochrome", "none"], case_sensitive=False))
@click.option("--invert/--no-invert", default=False, help="Invert character ramp.")
@click.option("--edge/--no-edge", default=False, help="Enable edge detection enhancement.")
@click.option("--brightness", type=float, default=1.0, help="Brightness adjustment factor.")
@click.option("--contrast", type=float, default=1.0, help="Contrast adjustment factor.")
@click.option("--gamma", type=float, default=1.0, help="Gamma factor.")
@click.option("--bg", "bg_color", default="#0e1117", help="Background color.")
@click.option("--fg", "fg_color", default="white", help="Foreground color.")
@click.option("--font-size", type=int, default=16, help="Font size for rendered images.")
@click.option("--font-path", type=click.Path(exists=True), default=None, help="Custom TTF/OTF font file.")
def convert_image_cmd(
    input_image: str,
    output: Optional[str],
    width: Optional[int],
    height: Optional[int],
    charset: str,
    color_mode: str,
    invert: bool,
    edge: bool,
    brightness: float,
    contrast: float,
    gamma: float,
    bg_color: str,
    fg_color: str,
    font_size: int,
    font_path: Optional[str],
):
    """Convert an image file to ASCII art (prints to terminal or saves to file)."""
    # If no output specified and no width given, fit to terminal
    if output is None and width is None:
        term_cols, _ = shutil.get_terminal_size((80, 24))
        width = max(20, term_cols - 2)

    config = AsciiConfig(
        width=width or 100,
        height=height,
        charset=charset,
        color_mode=color_mode,
        invert=invert,
        edge_detect=edge,
        brightness=brightness,
        contrast=contrast,
        gamma=gamma,
        bg_color=parse_color(bg_color),
        fg_color=parse_color(fg_color),
        font_size=font_size,
        font_path=font_path,
    )

    converter = AsciiConverter(config)
    frame = converter.convert_image(input_image)
    renderer = AsciiRenderer()

    if output:
        renderer.save(frame, output)
        console.print(f"[bold green]Saved ASCII graphic to:[/bold green] [cyan]{output}[/cyan] ({frame.width}x{frame.height} chars)")
    else:
        ansi_text = renderer.to_ansi(frame, color=(color_mode != "none"))
        sys.stdout.write(ansi_text + "\n")
        sys.stdout.flush()


@cli.command("video")
@click.argument("input_video", type=click.Path(exists=True))
@click.option("-o", "--output", required=True, help="Output file path (.mp4, .mkv, .avi, .gif, or folder for frame sequence).")
@click.option("-w", "--width", type=int, default=120, help="ASCII columns. Default: 120.")
@click.option("-H", "--height", type=int, default=None, help="ASCII rows. Auto-calculated if omitted.")
@click.option("-c", "--charset", default="standard", help="Character ramp preset or custom characters.")
@click.option("-m", "--color-mode", default="color", type=click.Choice(["color", "grayscale", "matrix", "amber", "cyan", "monochrome", "none"], case_sensitive=False))
@click.option("--fps", type=float, default=None, help="Output FPS override.")
@click.option("--step", type=int, default=1, help="Process every Nth frame.")
@click.option("--max-frames", type=int, default=None, help="Maximum number of frames to convert.")
@click.option("--audio/--no-audio", default=True, help="Preserve audio from original video.")
@click.option("--invert/--no-invert", default=False, help="Invert character ramp.")
@click.option("--edge/--no-edge", default=False, help="Enable edge detection enhancement.")
@click.option("--brightness", type=float, default=1.0, help="Brightness adjustment factor.")
@click.option("--contrast", type=float, default=1.0, help="Contrast adjustment factor.")
@click.option("--gamma", type=float, default=1.0, help="Gamma factor.")
@click.option("--bg", "bg_color", default="#0e1117", help="Background color.")
@click.option("--fg", "fg_color", default="white", help="Foreground color.")
@click.option("--font-size", type=int, default=16, help="Font size for rendered video.")
@click.option("--font-path", type=click.Path(exists=True), default=None, help="Custom TTF/OTF font file.")
def convert_video_cmd(
    input_video: str,
    output: str,
    width: int,
    height: Optional[int],
    charset: str,
    color_mode: str,
    fps: Optional[float],
    step: int,
    max_frames: Optional[int],
    audio: bool,
    invert: bool,
    edge: bool,
    brightness: float,
    contrast: float,
    gamma: float,
    bg_color: str,
    fg_color: str,
    font_size: int,
    font_path: Optional[str],
):
    """Convert a video file into an ASCII animation video or animated GIF."""
    info = get_video_info(input_video)
    console.print(f"[bold cyan]Input Video:[/bold cyan] {input_video} ([dim]{info['width']}x{info['height']} @ {info['fps']:.2f} FPS, {info['total_frames']} frames[/dim])")

    config = AsciiConfig(
        width=width,
        height=height,
        charset=charset,
        color_mode=color_mode,
        invert=invert,
        edge_detect=edge,
        brightness=brightness,
        contrast=contrast,
        gamma=gamma,
        bg_color=parse_color(bg_color),
        fg_color=parse_color(fg_color),
        font_size=font_size,
        font_path=font_path,
    )

    converter = AsciiVideoConverter(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total} frames)"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        est_total = min(max_frames, info["total_frames"] // step) if max_frames else (info["total_frames"] // step)
        task_id = progress.add_task("[yellow]Converting to ASCII animation...", total=est_total)

        def on_progress(completed: int, total: int):
            if progress.tasks[task_id].total != total:
                progress.update(task_id, total=total)
            progress.update(task_id, completed=completed)

        converter.convert_video(
            input_path=input_video,
            output_path=output,
            fps_override=fps,
            max_frames=max_frames,
            frame_step=step,
            keep_audio=audio,
            progress_callback=on_progress,
        )

    console.print(f"[bold green]ASCII animation successfully rendered to:[/bold green] [cyan]{output}[/cyan]")


@cli.command("play")
@click.argument("input_video", type=click.Path(exists=True))
@click.option("-w", "--width", type=int, default=None, help="ASCII columns. Auto-fits terminal if omitted.")
@click.option("-H", "--height", type=int, default=None, help="ASCII rows. Auto-fits terminal if omitted.")
@click.option("-c", "--charset", default="standard", help="Character ramp preset or custom characters.")
@click.option("-m", "--color-mode", default="color", type=click.Choice(["color", "grayscale", "matrix", "amber", "cyan", "monochrome", "none"], case_sensitive=False))
@click.option("--fps", type=float, default=None, help="Playback FPS override.")
@click.option("--loop/--no-loop", default=False, help="Loop playback continuously.")
@click.option("--invert/--no-invert", default=False, help="Invert character ramp.")
@click.option("--edge/--no-edge", default=False, help="Enable edge detection enhancement.")
@click.option("--brightness", type=float, default=1.0, help="Brightness adjustment factor.")
@click.option("--contrast", type=float, default=1.0, help="Contrast adjustment factor.")
def play_cmd(
    input_video: str,
    width: Optional[int],
    height: Optional[int],
    charset: str,
    color_mode: str,
    fps: Optional[float],
    loop: bool,
    invert: bool,
    edge: bool,
    brightness: float,
    contrast: float,
):
    """Play video directly in the terminal as real-time ASCII animation."""
    config = AsciiConfig(
        width=width,
        height=height,
        charset=charset,
        color_mode=color_mode,
        invert=invert,
        edge_detect=edge,
        brightness=brightness,
        contrast=contrast,
    )
    play_video_terminal(input_video, config=config, fps_override=fps, loop=loop)


@cli.command("charsets")
def list_charsets_cmd():
    """List available built-in character sets and previews."""
    table = Table(title="Available Character Sets", header_style="bold magenta")
    table.add_column("Preset Name", style="bold cyan", width=16)
    table.add_column("Ramp Length", justify="right", width=12)
    table.add_column("Character Ramp (Dense -> Light)")

    for name, chars in CHARSETS.items():
        table.add_row(name, str(len(chars)), chars)

    console.print(table)


@cli.command("info")
@click.argument("file_path", type=click.Path(exists=True))
def info_cmd(file_path: str):
    """Display format and dimension details for an image or video file."""
    if is_video_file(file_path):
        info = get_video_info(file_path)
        table = Table(title=f"Video Information: {os.path.basename(file_path)}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Resolution", f"{info['width']} x {info['height']}")
        table.add_row("Framerate", f"{info['fps']:.2f} FPS")
        table.add_row("Total Frames", str(info["total_frames"]))
        table.add_row("Duration", f"{info['duration']:.2f} seconds")
        console.print(table)
    else:
        from PIL import Image
        with Image.open(file_path) as img:
            table = Table(title=f"Image Information: {os.path.basename(file_path)}")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("Format", str(img.format))
            table.add_row("Mode", str(img.mode))
            table.add_row("Dimensions", f"{img.width} x {img.height}")
            console.print(table)


def main():
    cli()


if __name__ == "__main__":
    main()
