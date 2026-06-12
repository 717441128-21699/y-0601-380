from typing import List, Dict, Optional
from PySide6.QtCore import QObject, Signal
from core.photo import Photo, PhotoStatus
from utils import image_utils
from core.event_bus import EventBus


class PhotoStore(QObject):
    photos_changed = Signal()

    def __init__(self):
        super().__init__()
        self._photos: Dict[str, Photo] = {}
        self._bus = EventBus.instance()

    @property
    def all_photos(self) -> List[Photo]:
        return list(self._photos.values())

    @property
    def count(self) -> int:
        return len(self._photos)

    def get_photo(self, file_path: str) -> Optional[Photo]:
        return self._photos.get(file_path)

    def add_photos(self, photos: List[Photo]):
        for p in photos:
            self._photos[p.file_path] = p
        self.photos_changed.emit()
        self._bus.photos_imported.emit(photos)
        self._bus.log_message.emit("info", f"已导入 {len(photos)} 张照片")

    def clear(self):
        self._photos.clear()
        self.photos_changed.emit()

    def remove_photos(self, file_paths: List[str]):
        for fp in file_paths:
            self._photos.pop(fp, None)
        self.photos_changed.emit()

    def get_by_status(self, status: PhotoStatus) -> List[Photo]:
        return [p for p in self._photos.values() if p.status == status]

    def get_by_tag(self, tag: str) -> List[Photo]:
        return [p for p in self._photos.values() if tag in p.tags]

    def get_all_tags(self) -> List[str]:
        tags = set()
        for p in self._photos.values():
            tags.update(p.tags)
        return sorted(tags)

    def group_by_date(self) -> Dict[str, List[Photo]]:
        groups: Dict[str, List[Photo]] = {}
        for p in self._photos.values():
            key = p.shot_time.strftime("%Y-%m-%d") if p.shot_time else "未知日期"
            groups.setdefault(key, []).append(p)
        return dict(sorted(groups.items(), reverse=True))

    def group_by_dimensions(self) -> Dict[str, List[Photo]]:
        groups: Dict[str, List[Photo]] = {}
        for p in self._photos.values():
            key = p.dimensions_str
            groups.setdefault(key, []).append(p)
        return groups

    def group_by_ratio(self) -> Dict[str, List[Photo]]:
        groups: Dict[str, List[Photo]] = {}
        for p in self._photos.values():
            key = p.aspect_ratio
            groups.setdefault(key, []).append(p)
        return groups

    def group_by_status(self) -> Dict[str, List[Photo]]:
        groups: Dict[str, List[Photo]] = {}
        for p in self._photos.values():
            key = p.status.value
            groups.setdefault(key, []).append(p)
        return groups

    def update_photo_status(self, photo: Photo, status: PhotoStatus):
        old_status = photo.status
        photo.status = status
        self.photos_changed.emit()
        self._bus.photo_status_changed.emit(photo, old_status)

    def update_photo_tags(self, photo: Photo, tags: List[str]):
        photo.tags = tags
        self.photos_changed.emit()
        self._bus.photo_tags_changed.emit(photo, tags)

    def find_duplicates(self, use_perceptual: bool = True) -> List[List[Photo]]:
        hash_map: Dict[str, List[Photo]] = {}
        for p in self._photos.values():
            if use_perceptual:
                h = p.perceptual_hash or image_utils.compute_perceptual_hash(str(p.file_path))
                p.perceptual_hash = h
            else:
                h = p.hash or image_utils.compute_file_hash(str(p.file_path))
                p.hash = h
            if h:
                hash_map.setdefault(h, []).append(p)
        return [group for group in hash_map.values() if len(group) > 1]
