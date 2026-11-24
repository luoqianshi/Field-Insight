"""地理位置 API：从架次图片文件夹的 EXIF 中提取无人机拍摄 GPS 坐标。

所有响应遵循统一信封：{"success": bool, "data": <data>|None, "message": str}。
"""
from pathlib import Path

from flask import Blueprint, jsonify, request

from config import PROJECT_ROOT
from core.geo_extractor import extract_folder_gps

geo_bp = Blueprint("geo", __name__)


def _error(message: str, status_code: int = 400):
    return jsonify({"success": False, "data": None, "message": message}), status_code


def _resolve_path(path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


@geo_bp.route("/api/geo/extract-from-images", methods=["POST"])
def extract_from_images():
    """POST /api/geo/extract-from-images → 抽样解析图片 EXIF GPS。

    body: {"image_folder_path": "<本机图片文件夹路径>"}
    """
    body = request.get_json(silent=True) or {}
    folder_str = (body.get("image_folder_path") or "").strip()
    if not folder_str:
        return _error("缺少 image_folder_path 参数", 400)
    folder = _resolve_path(folder_str)
    try:
        result = extract_folder_gps(folder)
    except Exception as exc:
        return _error(f"提取图片地理位置失败: {exc}", 500)
    # 未找到 GPS 也返回 success:True，由 data.found 区分，便于前端展示统计信息
    return jsonify({
        "success": True,
        "data": result,
        "message": result["message"],
    })
