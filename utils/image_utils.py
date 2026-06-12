from pathlib import Path
from typing import List, Optional
from PIL import Image, ExifTags
from datetime import datetime
import hashlib
import imagehash


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic", ".raw", ".cr2", ".nef", ".arw"}


def is_image_file(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS


def scan_directory(directory: str, recursive: bool = True) -> List[str]:
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return []
    pattern = "**/*" if recursive else "*"
    return [str(f) for f in dir_path.glob(pattern) if f.is_file() and is_image_file(str(f))]


def get_exif_data(image_path: str) -> dict:
    try:
        with Image.open(image_path) as img:
            exif_data = img._getexif()
            if exif_data:
                result = {}
                for tag_id, value in exif_data.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    result[tag] = value
                return result
    except Exception:
        pass
    return {}


def get_image_dimensions(image_path: str) -> tuple:
    try:
        with Image.open(image_path) as img:
            return img.width, img.height
    except Exception:
        return 0, 0


def get_shot_time(image_path: str, file_created: datetime) -> datetime:
    exif = get_exif_data(image_path)
    for key in ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]:
        if key in exif:
            try:
                return datetime.strptime(str(exif[key]), "%Y:%m:%d %H:%M:%S")
            except ValueError:
                continue
    return file_created


def compute_file_hash(file_path: str, algorithm: str = "md5") -> Optional[str]:
    try:
        h = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def compute_perceptual_hash(image_path: str) -> Optional[str]:
    try:
        with Image.open(image_path) as img:
            return str(imagehash.phash(img))
    except Exception:
        return None


def generate_thumbnail(image_path: str, size: tuple = (200, 200)) -> Optional["Image.Image"]:
    try:
        with Image.open(image_path) as img:
            img.thumbnail(size)
            return img.copy()
    except Exception:
        return None


def format_size(bytes_size: int) -> str:
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"


def unique_filename(directory: str, filename: str) -> str:
    path = Path(directory) / filename
    if not path.exists():
        return filename
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        if not (Path(directory) / new_name).exists():
            return new_name
        counter += 1


def apply_rename_pattern(pattern: str, index: int, photo, total: int) -> str:
    from datetime import datetime
    replacements = {
        "{n}": str(index),
        "{index}": str(index),
        "{index:02d}": f"{index:02d}",
        "{index:03d}": f"{index:03d}",
        "{index:04d}": f"{index:04d}",
        "{total}": str(total),
        "{total:02d}": f"{total:02d}",
        "{total:03d}": f"{total:03d}",
        "{original}": Path(photo.filename).stem,
        "{ext}": photo.extension,
        "{date}": photo.shot_time.strftime("%Y%m%d") if photo.shot_time else datetime.now().strftime("%Y%m%d"),
        "{datetime}": photo.shot_time.strftime("%Y%m%d_%H%M%S") if photo.shot_time else datetime.now().strftime("%Y%m%d_%H%M%S"),
        "{year}": photo.shot_time.strftime("%Y") if photo.shot_time else datetime.now().strftime("%Y"),
        "{month}": photo.shot_time.strftime("%m") if photo.shot_time else datetime.now().strftime("%m"),
        "{day}": photo.shot_time.strftime("%d") if photo.shot_time else datetime.now().strftime("%d"),
        "{width}": str(photo.width),
        "{height}": str(photo.height),
        "{dim}": f"{photo.width}x{photo.height}",
    }
    result = pattern
    for key, value in replacements.items():
        result = result.replace(key, value)
    return result
