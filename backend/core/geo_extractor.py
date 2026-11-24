"""图片 EXIF 地理位置提取：从 UAV 拍摄照片（如 DJI）中解析 GPS 坐标。

DJI 等无人机在 JPEG 的标准 EXIF GPSInfo IFD（tag 0x8825）中写入拍摄点
WGS84 经纬度（度分秒有理数）与海拔，Pillow 可直接解析，无需额外依赖。

输出坐标统一为 WGS84 十进制度（EPSG:4326）：
- latitude:  纬度，北正南负，范围 [-90, 90]
- longitude: 经度，东正西负，范围 [-180, 180]
- altitude_m: 海拔高度（EGM96 大地水准面基准，米）；无 GPS Altitude 时为 None
"""
import math
from pathlib import Path
from typing import Optional

from PIL import Image

from config import IMAGE_EXTENSIONS, MAX_IMAGE_SIZE_BYTES

# GPSInfo IFD 内常用 tag
_GPS_TAG_LAT_REF = 1
_GPS_TAG_LAT = 2
_GPS_TAG_LON_REF = 3
_GPS_TAG_LON = 4
_GPS_TAG_ALT_REF = 5
_GPS_TAG_ALT = 6

# 单文件夹最多抽样解析的图片数（避免大架次全量扫描耗时）
MAX_SAMPLE_IMAGES = 20


def _to_float(value) -> Optional[float]:
    """EXIF 有理数（Fraction/IFDRational/int/float）转 float。"""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _dms_to_decimal(values, ref: str) -> Optional[float]:
    """度分秒（3 个有理数）+ N/S/E/W 参考 → WGS84 十进制度。"""
    if not values or len(values) < 3:
        return None
    parts = [_to_float(v) for v in values[:3]]
    if any(p is None for p in parts):
        return None
    degrees = parts[0] + parts[1] / 60.0 + parts[2] / 3600.0
    ref = (ref or "").strip().upper()
    if ref in ("S", "W"):
        degrees = -degrees
    elif ref not in ("N", "E"):
        return None
    return degrees


def extract_image_gps(image_path: Path) -> Optional[dict]:
    """读取单张图片 EXIF GPS，返回 {latitude, longitude, altitude_m}；无 GPS 返回 None。"""
    try:
        with Image.open(image_path) as im:
            exif = im.getexif()
            if not exif:
                return None
            gps_ifd = exif.get_ifd(0x8825)
    except Exception:
        return None
    if not gps_ifd:
        return None

    latitude = _dms_to_decimal(gps_ifd.get(_GPS_TAG_LAT), str(gps_ifd.get(_GPS_TAG_LAT_REF, "")))
    longitude = _dms_to_decimal(gps_ifd.get(_GPS_TAG_LON), str(gps_ifd.get(_GPS_TAG_LON_REF, "")))
    if latitude is None or longitude is None:
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    if latitude == 0 and longitude == 0:
        return None  # 无效占位坐标

    altitude_m = _to_float(gps_ifd.get(_GPS_TAG_ALT))
    if altitude_m is not None:
        alt_ref = _to_float(gps_ifd.get(_GPS_TAG_ALT_REF))
        if alt_ref == 1:
            altitude_m = -altitude_m

    return {"latitude": round(latitude, 7), "longitude": round(longitude, 7),
            "altitude_m": round(altitude_m, 2) if altitude_m is not None else None}


def extract_folder_gps(folder_path: Path, max_samples: int = MAX_SAMPLE_IMAGES) -> dict:
    """抽样扫描文件夹内图片的 EXIF GPS，聚合返回首个有效坐标。

    同一架次图片拍摄点相近，抽样即可代表架次位置；返回结构：
    {found, latitude, longitude, altitude_m, source_filename,
     images_with_gps, images_sampled, message}
    """
    folder_path = Path(folder_path)
    if not folder_path.is_dir():
        return {"found": False, "latitude": None, "longitude": None, "altitude_m": None,
                "source_filename": "", "images_with_gps": 0, "images_sampled": 0,
                "message": f"路径不存在或不是文件夹: {folder_path}"}

    candidates = []
    for entry in sorted(folder_path.iterdir()):
        if entry.is_file() and entry.suffix.lower() in IMAGE_EXTENSIONS:
            try:
                if entry.stat().st_size <= MAX_IMAGE_SIZE_BYTES:
                    candidates.append(entry)
            except OSError:
                continue
            if len(candidates) >= max_samples:
                break

    if not candidates:
        return {"found": False, "latitude": None, "longitude": None, "altitude_m": None,
                "source_filename": "", "images_with_gps": 0, "images_sampled": 0,
                "message": "文件夹下未找到可解析的图片文件"}

    first_hit = None
    with_gps = 0
    for img in candidates:
        gps = extract_image_gps(img)
        if gps:
            with_gps += 1
            if first_hit is None:
                first_hit = (img.name, gps)

    if first_hit is None:
        return {"found": False, "latitude": None, "longitude": None, "altitude_m": None,
                "source_filename": "", "images_with_gps": 0, "images_sampled": len(candidates),
                "message": f"已抽样 {len(candidates)} 张图片，均未包含 EXIF GPS 信息（部分设备需开启照片定位记录）"}

    filename, gps = first_hit
    return {
        "found": True,
        "latitude": gps["latitude"],
        "longitude": gps["longitude"],
        "altitude_m": gps["altitude_m"],
        "source_filename": filename,
        "images_with_gps": with_gps,
        "images_sampled": len(candidates),
        "message": f"从 {filename} 解析到 GPS 坐标（抽样 {len(candidates)} 张中 {with_gps} 张含定位）",
    }
