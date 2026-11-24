"""geo_extractor 单元测试：EXIF GPS 解析与文件夹抽样聚合。

运行：cd backend && python -m pytest tests/test_geo_extractor.py -v
"""
from fractions import Fraction
from pathlib import Path

import pytest
from PIL import Image

from core.geo_extractor import _dms_to_decimal, extract_folder_gps, extract_image_gps


def _write_gps_jpeg(path: Path, lat, lon, alt=None):
    """写入带标准 EXIF GPSInfo 的 JPEG（模拟 DJI 输出）。"""
    img = Image.new("RGB", (64, 64), (0, 128, 0))
    exif = img.getexif()
    gps = exif.get_ifd(0x8825)
    gps[1] = "N" if lat >= 0 else "S"
    gps[2] = (int(abs(lat)), int(abs(lat) % 1 * 60), Fraction(round((abs(lat) * 3600) % 60 * 100), 100))
    gps[3] = "E" if lon >= 0 else "W"
    gps[4] = (int(abs(lon)), int(abs(lon) % 1 * 60), Fraction(round((abs(lon) * 3600) % 60 * 100), 100))
    if alt is not None:
        gps[5] = 0
        gps[6] = Fraction(alt)
    exif[0x8825] = gps  # Pillow 需显式挂载 GPS IFD 才会序列化
    img.save(path, "JPEG", exif=exif)
    return path


def test_dms_to_decimal_basic():
    assert _dms_to_decimal((23, 8, Fraction(1334, 100)), "N") == pytest.approx(23.1370389, abs=1e-6)
    assert _dms_to_decimal((113, 15, Fraction(5000, 100)), "E") == pytest.approx(113.2638889, abs=1e-6)
    assert _dms_to_decimal((33, 54, 0), "S") == pytest.approx(-33.9)
    assert _dms_to_decimal((1, 2, 3), "X") is None
    assert _dms_to_decimal(None, "N") is None


def test_extract_image_gps_roundtrip(tmp_path):
    p = _write_gps_jpeg(tmp_path / "DJI_0001.JPG", 23.1370389, 113.2583333, alt=152.5)
    gps = extract_image_gps(p)
    assert gps is not None
    assert gps["latitude"] == pytest.approx(23.1370389, abs=1e-5)
    assert gps["longitude"] == pytest.approx(113.2583333, abs=1e-5)
    assert gps["altitude_m"] == pytest.approx(152.5, abs=0.01)


def test_extract_image_gps_no_exif(tmp_path):
    img = Image.new("RGB", (32, 32), (1, 2, 3))
    p = tmp_path / "plain.jpg"
    img.save(p, "JPEG")
    assert extract_image_gps(p) is None


def test_extract_folder_gps_aggregates(tmp_path):
    _write_gps_jpeg(tmp_path / "a.jpg", 22.5, 113.5, alt=100)
    img = Image.new("RGB", (32, 32), (9, 9, 9))
    img.save(tmp_path / "b.jpg", "JPEG")  # 无 GPS
    result = extract_folder_gps(tmp_path)
    assert result["found"] is True
    assert result["latitude"] == pytest.approx(22.5, abs=1e-5)
    assert result["images_sampled"] == 2
    assert result["images_with_gps"] == 1
    assert result["source_filename"] == "a.jpg"


def test_extract_folder_gps_none_found(tmp_path):
    img = Image.new("RGB", (32, 32), (9, 9, 9))
    img.save(tmp_path / "b.jpg", "JPEG")
    result = extract_folder_gps(tmp_path)
    assert result["found"] is False
    assert result["images_sampled"] == 1


def test_extract_folder_gps_invalid_path(tmp_path):
    result = extract_folder_gps(tmp_path / "not_exist")
    assert result["found"] is False
