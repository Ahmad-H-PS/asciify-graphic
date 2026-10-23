import os
import pytest

from asciify.storage import (
    get_asciify_export_dir,
    get_user_folder,
    is_video_extension,
    resolve_output_path,
)


def test_get_user_folder():
    pic_dir = get_user_folder("Pictures")
    vid_dir = get_user_folder("Videos")
    assert os.path.exists(pic_dir)
    assert os.path.exists(vid_dir)


def test_get_asciify_export_dir():
    vid_export = get_asciify_export_dir("video")
    pic_export = get_asciify_export_dir("image")

    assert os.path.isdir(vid_export)
    assert os.path.isdir(pic_export)
    assert vid_export.endswith("ASCIIFY")
    assert pic_export.endswith("ASCIIFY")
    assert "Videos" in vid_export
    assert "Pictures" in pic_export


def test_is_video_extension():
    assert is_video_extension("clip.mp4")
    assert is_video_extension(".gif")
    assert is_video_extension("movie.mkv")
    assert not is_video_extension("photo.png")
    assert not is_video_extension(".jpg")
    assert not is_video_extension("art.txt")


def test_resolve_output_path_bare_filename():
    # Bare filename for video -> goes to Videos/ASCIIFY
    res_vid = resolve_output_path("my_anim.mp4", media_type="video")
    assert "Videos" in res_vid
    assert res_vid.endswith(os.path.join("ASCIIFY", "my_anim.mp4"))

    # Bare filename for image -> goes to Pictures/ASCIIFY
    res_pic = resolve_output_path("art.png", media_type="image")
    assert "Pictures" in res_pic
    assert res_pic.endswith(os.path.join("ASCIIFY", "art.png"))


def test_resolve_output_path_default_omitted():
    # No output specified for video -> generates <input>_ascii.mp4 in Videos/ASCIIFY
    res_default_vid = resolve_output_path(None, input_source="clip.mp4", media_type="video")
    assert "Videos" in res_default_vid
    assert "clip_ascii.mp4" in res_default_vid

    # No output specified for image -> generates in Pictures/ASCIIFY
    res_default_pic = resolve_output_path(None, input_source="photo.jpg", media_type="image")
    assert "Pictures" in res_default_pic
    assert "photo_ascii.png" in res_default_pic


def test_resolve_output_path_explicit_directory(tmp_path):
    custom_target = str(tmp_path / "custom_folder" / "custom.mp4")
    res = resolve_output_path(custom_target, media_type="video")
    assert res == os.path.abspath(custom_target)
    assert os.path.isdir(os.path.dirname(res))
