import numpy as np
from PIL import Image
import pytest

from asciify.config import AsciiConfig, parse_color
from asciify.converter import AsciiConverter, AsciiFrame
from asciify.charsets import get_charset, CHARSETS


def test_parse_color():
    assert parse_color("black") == (0, 0, 0)
    assert parse_color("white") == (255, 255, 255)
    assert parse_color("matrix") == (0, 255, 85)
    assert parse_color("#ff0000") == (255, 0, 0)
    assert parse_color("#00ff00") == (0, 255, 0)
    assert parse_color("#00f") == (0, 0, 255)
    assert parse_color((10, 20, 30)) == (10, 20, 30)


def test_charsets():
    assert "standard" in CHARSETS
    std = get_charset("standard")
    assert std.startswith("@")
    inv = get_charset("standard", invert=True)
    assert inv == std[::-1]


def test_converter_dimensions():
    cfg = AsciiConfig(width=80, height=40)
    converter = AsciiConverter(cfg)
    assert converter.calculate_dimensions(200, 100) == (80, 40)

    cfg2 = AsciiConfig(width=100, height=None, char_aspect=0.5)
    conv2 = AsciiConverter(cfg2)
    cols, rows = conv2.calculate_dimensions(200, 100)
    assert cols == 100
    assert rows == 25  # 100/200 * 100 * 0.5 = 25


def test_convert_solid_image():
    # Pure white image
    white_img = Image.new("RGB", (100, 100), (255, 255, 255))
    cfg = AsciiConfig(width=20, height=10, charset="standard")
    converter = AsciiConverter(cfg)
    frame = converter.convert_image(white_img)

    assert isinstance(frame, AsciiFrame)
    assert frame.width == 20
    assert frame.height == 10
    assert frame.chars.shape == (10, 20)
    # White maps to lightest character (space ' ' in standard ramp)
    assert np.all(frame.chars == " ")

    # Pure black image
    black_img = Image.new("RGB", (100, 100), (0, 0, 0))
    frame_black = converter.convert_image(black_img)
    # Black maps to darkest character ('@' in standard ramp)
    assert np.all(frame_black.chars == "@")


def test_convert_color_modes():
    img = Image.new("RGB", (50, 50), (255, 0, 0))

    # Color mode
    conv_color = AsciiConverter(AsciiConfig(width=10, height=10, color_mode="color"))
    frame_color = conv_color.convert_image(img)
    assert np.all(frame_color.colors[:, :, 0] == 255)
    assert np.all(frame_color.colors[:, :, 1] == 0)

    # Matrix mode
    conv_matrix = AsciiConverter(AsciiConfig(width=10, height=10, color_mode="matrix"))
    frame_matrix = conv_matrix.convert_image(img)
    # Red has non-zero luminance so matrix green channel will be active
    assert np.all(frame_matrix.colors[:, :, 1] > 0)


def test_convert_edge_detect():
    arr = np.zeros((60, 60, 3), dtype=np.uint8)
    arr[20:40, 20:40] = 255
    img = Image.fromarray(arr)

    conv_edge = AsciiConverter(AsciiConfig(width=30, height=30, edge_detect=True))
    frame = conv_edge.convert_image(img)
    assert frame.chars.shape == (30, 30)
