from click.testing import CliRunner
from PIL import Image
import pytest

from asciify import __version__
from asciify.cli import cli


@pytest.fixture
def test_image(tmp_path):
    img_path = tmp_path / "cli_test.png"
    img = Image.new("RGB", (60, 40), (200, 50, 50))
    img.save(str(img_path))
    return str(img_path)


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_cli_charsets():
    runner = CliRunner()
    result = runner.invoke(cli, ["charsets"])
    assert result.exit_code == 0
    assert "standard" in result.output
    assert "detailed" in result.output
    assert "matrix" in result.output


def test_cli_info(test_image):
    runner = CliRunner()
    result = runner.invoke(cli, ["info", test_image])
    assert result.exit_code == 0
    assert "60 x 40" in result.output


def test_cli_convert_image_stdout(test_image):
    runner = CliRunner()
    result = runner.invoke(cli, ["image", test_image, "-w", "20"])
    assert result.exit_code == 0
    assert len(result.output) > 0


def test_cli_convert_image_to_file(test_image, tmp_path):
    out_txt = str(tmp_path / "out.txt")
    out_png = str(tmp_path / "out.png")
    runner = CliRunner()

    res_txt = runner.invoke(cli, ["image", test_image, "-o", out_txt, "-w", "30"])
    assert res_txt.exit_code == 0
    assert "Saved ASCII graphic to:" in res_txt.output

    res_png = runner.invoke(cli, ["image", test_image, "-o", out_png, "-w", "30"])
    assert res_png.exit_code == 0
    assert "Saved ASCII graphic to:" in res_png.output


def test_cli_smart_dispatch(test_image, tmp_path):
    out_html = str(tmp_path / "out.html")
    runner = CliRunner()
    res = runner.invoke(cli, [test_image, "-o", out_html, "-w", "25"])
    assert res.exit_code == 0
    assert "Saved ASCII graphic to:" in res.output
