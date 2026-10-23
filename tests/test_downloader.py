import os
from unittest.mock import MagicMock, patch
import pytest

from asciify.downloader import (
    detect_media_type,
    download_direct_url,
    is_url,
    is_youtube_url,
    resolve_media_input,
)


def test_is_url():
    assert is_url("http://example.com/image.png")
    assert is_url("https://www.youtube.com/watch?v=test")
    assert not is_url("C:\\path\\to\\file.png")
    assert not is_url("sample.mp4")
    assert not is_url("")


def test_is_youtube_url():
    assert is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert is_youtube_url("http://youtu.be/dQw4w9WgXcQ")
    assert is_youtube_url("https://m.youtube.com/watch?v=abc")
    assert not is_youtube_url("https://example.com/video.mp4")
    assert not is_youtube_url("https://vimeo.com/123456")


def test_detect_media_type():
    assert detect_media_type("https://example.com/image.png") == "image"
    assert detect_media_type("https://example.com/photo.jpg") == "image"
    assert detect_media_type("https://example.com/video.mp4") == "video"
    assert detect_media_type("https://www.youtube.com/watch?v=123") == "video"
    assert detect_media_type("https://example.com/asset", content_type="image/jpeg") == "image"
    assert detect_media_type("https://example.com/stream", content_type="video/mp4") == "video"


def test_resolve_local_file(tmp_path):
    img_file = tmp_path / "test.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    path, mtype = resolve_media_input(str(img_file))
    assert os.path.exists(path)
    assert mtype == "image"

    with pytest.raises(FileNotFoundError):
        resolve_media_input(str(tmp_path / "nonexistent.png"))


@patch("requests.get")
@patch("requests.head")
def test_download_direct_url(mock_head, mock_get, tmp_path):
    mock_head_resp = MagicMock()
    mock_head_resp.headers = {"content-type": "image/png"}
    mock_head.return_value = mock_head_resp

    mock_get_resp = MagicMock()
    mock_get_resp.headers = {"content-type": "image/png"}
    mock_get_resp.iter_content.return_value = [b"fake_image_data_chunk"]
    mock_get_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_get_resp

    test_url = "https://example.com/mock_image.png"
    file_path, mtype = download_direct_url(test_url, output_dir=str(tmp_path))

    assert mtype == "image"
    assert os.path.exists(file_path)
    with open(file_path, "rb") as f:
        assert f.read() == b"fake_image_data_chunk"


@patch("asciify.downloader.download_youtube_video")
def test_resolve_youtube_url(mock_dl):
    mock_dl.return_value = "/tmp/test_yt.mp4"
    path, mtype = resolve_media_input("https://www.youtube.com/watch?v=test1234")
    assert path == "/tmp/test_yt.mp4"
    assert mtype == "video"
