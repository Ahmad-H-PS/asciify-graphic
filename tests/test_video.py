import os
import imageio
import numpy as np
from PIL import Image, ImageDraw
import pytest

from asciify.config import AsciiConfig
from asciify.video import (
    AsciiVideoConverter,
    get_video_info,
    iter_video_frames,
)


@pytest.fixture
def synthetic_video(tmp_path):
    video_path = tmp_path / "test_mini.mp4"
    writer = imageio.get_writer(
        str(video_path),
        fps=10,
        format="FFMPEG",
        mode="I",
        macro_block_size=2,
    )
    for i in range(10):
        img = Image.new("RGB", (100, 100), (i * 20, 100, 150))
        d = ImageDraw.Draw(img)
        d.rectangle((20 + i * 2, 20, 50 + i * 2, 50), fill=(255, 255, 0))
        writer.append_data(np.array(img))
    writer.close()
    return str(video_path)


def test_video_info(synthetic_video):
    info = get_video_info(synthetic_video)
    assert info["fps"] == 10.0
    assert info["total_frames"] == 10
    assert info["width"] == 100
    assert info["height"] == 100
    assert info["duration"] == 1.0


def test_iter_video_frames(synthetic_video):
    frames = list(iter_video_frames(synthetic_video, max_frames=5))
    assert len(frames) == 5
    idx, frame_data = frames[0]
    assert idx == 0
    assert frame_data.shape == (100, 100, 3)


def test_convert_video_to_mp4(synthetic_video, tmp_path):
    out_mp4 = str(tmp_path / "ascii_anim.mp4")
    cfg = AsciiConfig(width=40, font_size=12)
    converter = AsciiVideoConverter(cfg)

    converter.convert_video(synthetic_video, out_mp4, keep_audio=False)
    assert os.path.exists(out_mp4)
    assert os.path.getsize(out_mp4) > 0

    info = get_video_info(out_mp4)
    assert info["total_frames"] == 10


def test_convert_video_to_gif(synthetic_video, tmp_path):
    out_gif = str(tmp_path / "ascii_anim.gif")
    cfg = AsciiConfig(width=30, font_size=10)
    converter = AsciiVideoConverter(cfg)

    converter.convert_video(synthetic_video, out_gif)
    assert os.path.exists(out_gif)
    assert os.path.getsize(out_gif) > 0


def test_convert_video_to_frames_dir(synthetic_video, tmp_path):
    out_dir = str(tmp_path / "ascii_frames")
    cfg = AsciiConfig(width=20, font_size=10)
    converter = AsciiVideoConverter(cfg)

    converter.convert_video(synthetic_video, out_dir, max_frames=3)
    assert os.path.isdir(out_dir)
    files = os.listdir(out_dir)
    assert len(files) == 3
