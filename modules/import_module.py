import os
from pathlib import Path
from typing import List
from PySide6.QtCore import QThread, Signal, QObject
from PySide6.QtGui import QPixmap, QImage
from PIL import Image
from core.photo import Photo
from utils import image_utils


class PhotoLoader(QThread):
    progress = Signal(int, int, str)
    photo_loaded = Signal(object)
    finished_loading = Signal(list)

    def __init__(self, file_paths: List[str]):
        super().__init__()
        self.file_paths = file_paths
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        photos = []
        total = len(self.file_paths)
        for i, fp in enumerate(self.file_paths):
            if self._stop:
                break
            try:
                photo = Photo(fp)
                w, h = image_utils.get_image_dimensions(fp)
                photo.width = w
                photo.height = h
                photo.shot_time = image_utils.get_shot_time(fp, photo.created_time)
                photo.thumbnail = image_utils.generate_thumbnail(fp, (200, 200))
                photos.append(photo)
                self.photo_loaded.emit(photo)
            except Exception as e:
                print(f"加载照片失败 {fp}: {e}")
            self.progress.emit(i + 1, total, fp)
        self.finished_loading.emit(photos)


def pil_to_qpixmap(pil_image) -> QPixmap:
    if pil_image is None:
        return QPixmap()
    if pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA")
    data = pil_image.tobytes("raw", "RGBA")
    qimg = QImage(data, pil_image.width, pil_image.height, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())
