import os
from PIL import Image
import pytest

from asciify.config import AsciiConfig
from asciify.converter import AsciiConverter
from asciify.renderer import AsciiRenderer


@pytest.fixture
def sample_frame():
    img = Image.new("RGB", (40, 20), (100, 150, 200))
    cfg = AsciiConfig(width=20, height=10, color_mode="color")
    converter = AsciiConverter(cfg)
    return converter.convert_image(img)


def test_render_text(sample_frame):
    text = AsciiRenderer.to_text(sample_frame)
    lines = text.split("\n")
    assert len(lines) == 10
    assert all(len(line) == 20 for line in lines)


def test_render_ansi(sample_frame):
    ansi = AsciiRenderer.to_ansi(sample_frame, color=True)
    assert "\033[38;2;" in ansi
    assert "\033[0m" in ansi

    # Non-colored ansi should match plain text
    plain_ansi = AsciiRenderer.to_ansi(sample_frame, color=False)
    assert plain_ansi == AsciiRenderer.to_text(sample_frame)


def test_render_html(sample_frame):
    html_doc = AsciiRenderer.to_html(sample_frame, title="Test Art")
    assert "<!DOCTYPE html>" in html_doc
    assert "<title>Test Art</title>" in html_doc
    assert "<pre class=\"ascii-canvas\">" in html_doc
    assert "<span style=\"color:#" in html_doc


def test_render_image(sample_frame):
    renderer = AsciiRenderer()
    rendered_img = renderer.to_image(sample_frame)
    assert isinstance(rendered_img, Image.Image)
    assert rendered_img.width > 20
    assert rendered_img.height > 10


def test_save_all_formats(sample_frame, tmp_path):
    renderer = AsciiRenderer()

    # Text
    txt_path = tmp_path / "art.txt"
    renderer.save(sample_frame, str(txt_path))
    assert txt_path.exists() and txt_path.stat().st_size > 0

    # ANSI
    ans_path = tmp_path / "art.ans"
    renderer.save(sample_frame, str(ans_path))
    assert ans_path.exists() and ans_path.stat().st_size > 0

    # HTML
    html_path = tmp_path / "art.html"
    renderer.save(sample_frame, str(html_path))
    assert html_path.exists() and html_path.stat().st_size > 0

    # PNG Image
    png_path = tmp_path / "art.png"
    renderer.save(sample_frame, str(png_path))
    assert png_path.exists() and png_path.stat().st_size > 0
