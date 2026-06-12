from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class PhotoStatus(Enum):
    UNPROCESSED = "未处理"
    KEEP = "保留"
    REJECT = "淘汰"
    DUPLICATE = "重复"


class Photo:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.filename = self.file_path.name
        self.extension = self.file_path.suffix.lower()
        self.size_bytes = self.file_path.stat().st_size if self.file_path.exists() else 0
        self.created_time = datetime.fromtimestamp(self.file_path.stat().st_ctime) if self.file_path.exists() else datetime.now()
        self.modified_time = datetime.fromtimestamp(self.file_path.stat().st_mtime) if self.file_path.exists() else datetime.now()
        self.shot_time: Optional[datetime] = None
        self.width: int = 0
        self.height: int = 0
        self.thumbnail = None
        self.status: PhotoStatus = PhotoStatus.UNPROCESSED
        self.tags: List[str] = []
        self.new_filename: Optional[str] = None
        self.target_directory: Optional[Path] = None
        self.hash: Optional[str] = None
        self.perceptual_hash: Optional[str] = None
        self.group_key: Optional[str] = None

    @property
    def size_mb(self) -> float:
        return round(self.size_bytes / (1024 * 1024), 2)

    @property
    def dimensions_str(self) -> str:
        if self.width and self.height:
            return f"{self.width}×{self.height}"
        return "未知"

    @property
    def aspect_ratio(self) -> str:
        if not self.width or not self.height:
            return "未知"
        from math import gcd
        g = gcd(self.width, self.height)
        return f"{self.width // g}:{self.height // g}"

    def __repr__(self):
        return f"<Photo {self.filename}>"
