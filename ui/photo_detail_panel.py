from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                               QPushButton, QScrollArea)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap
from core.photo import Photo, PhotoStatus
from modules.import_module import pil_to_qpixmap
from utils import image_utils


class PhotoDetailPanel(QWidget):
    status_changed = Signal(object, object)
    open_external = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._photo = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("🖼 照片详情")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: 1px solid #e5e5e5; border-radius: 8px; background: #222; }")
        self.preview_label = QLabel("选择照片以预览")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("color: #aaa; padding: 20px;")
        self.preview_label.setMinimumSize(300, 250)
        self.scroll.setWidget(self.preview_label)
        self.scroll.setMinimumHeight(280)
        layout.addWidget(self.scroll)

        info_frame = QFrame()
        info_frame.setStyleSheet("QFrame { background: #f8f9fa; border-radius: 8px; padding: 12px; }")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(4)

        self.lbl_filename = QLabel("文件名: -")
        self.lbl_filename.setWordWrap(True)
        self.lbl_filename.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.lbl_filename)

        self.lbl_path = QLabel("路径: -")
        self.lbl_path.setWordWrap(True)
        self.lbl_path.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(self.lbl_path)

        self.lbl_size = QLabel("大小: -")
        self.lbl_size.setStyleSheet("color: #333;")
        info_layout.addWidget(self.lbl_size)

        self.lbl_dim = QLabel("尺寸: -")
        self.lbl_dim.setStyleSheet("color: #333;")
        info_layout.addWidget(self.lbl_dim)

        self.lbl_ratio = QLabel("比例: -")
        self.lbl_ratio.setStyleSheet("color: #333;")
        info_layout.addWidget(self.lbl_ratio)

        self.lbl_shot = QLabel("拍摄时间: -")
        self.lbl_shot.setStyleSheet("color: #333;")
        info_layout.addWidget(self.lbl_shot)

        self.lbl_modified = QLabel("修改时间: -")
        self.lbl_modified.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(self.lbl_modified)

        self.lbl_status = QLabel("状态: -")
        self.lbl_status.setStyleSheet("color: #333;")
        info_layout.addWidget(self.lbl_status)

        self.lbl_tags = QLabel("标签: -")
        self.lbl_tags.setWordWrap(True)
        self.lbl_tags.setStyleSheet("color: #333;")
        info_layout.addWidget(self.lbl_tags)

        self.lbl_hash = QLabel("哈希: -")
        self.lbl_hash.setStyleSheet("color: #888; font-size: 10px; font-family: Consolas, monospace;")
        self.lbl_hash.setWordWrap(True)
        info_layout.addWidget(self.lbl_hash)

        layout.addWidget(info_frame)

        btn_layout = QHBoxLayout()
        self.btn_keep = QPushButton("✓ 保留")
        self.btn_keep.setStyleSheet(self._btn_style("#27ae60"))
        self.btn_keep.clicked.connect(lambda: self._change_status(PhotoStatus.KEEP))

        self.btn_reject = QPushButton("✗ 淘汰")
        self.btn_reject.setStyleSheet(self._btn_style("#e74c3c"))
        self.btn_reject.clicked.connect(lambda: self._change_status(PhotoStatus.REJECT))

        self.btn_reset = QPushButton("↺ 重置")
        self.btn_reset.setStyleSheet(self._btn_style("#6c757d"))
        self.btn_reset.clicked.connect(lambda: self._change_status(PhotoStatus.UNPROCESSED))

        btn_layout.addWidget(self.btn_keep)
        btn_layout.addWidget(self.btn_reject)
        btn_layout.addWidget(self.btn_reset)
        layout.addLayout(btn_layout)

        self.btn_open = QPushButton("📂 在资源管理器中打开")
        self.btn_open.setStyleSheet(self._btn_style("#4A90D9"))
        self.btn_open.clicked.connect(self._open_in_explorer)
        layout.addWidget(self.btn_open)

        layout.addStretch()

    def _btn_style(self, color: str) -> str:
        return f"""
            QPushButton {{
                background: {color};
                color: white;
                border: none;
                padding: 6px 14px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: {color}dd; }}
            QPushButton:disabled {{ background: #ccc; }}
        """

    def _change_status(self, status: PhotoStatus):
        if self._photo:
            self.status_changed.emit(self._photo, status)

    def _open_in_explorer(self):
        if self._photo and self._photo.file_path.exists():
            self.open_external.emit(self._photo)

    def set_photo(self, photo: Photo):
        self._photo = photo
        if not photo:
            self.preview_label.setText("选择照片以预览")
            self.preview_label.setPixmap(QPixmap())
            for lbl in [self.lbl_filename, self.lbl_path, self.lbl_size, self.lbl_dim,
                        self.lbl_ratio, self.lbl_shot, self.lbl_modified, self.lbl_status,
                        self.lbl_tags, self.lbl_hash]:
                lbl.setText(lbl.text().split(":")[0] + ": -")
            return

        if photo.thumbnail:
            pixmap = pil_to_qpixmap(photo.thumbnail)
            if not pixmap.isNull():
                scaled = pixmap.scaled(500, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_label.setPixmap(scaled)
                self.preview_label.setText("")
            else:
                self.preview_label.setText("无法预览")
        else:
            self.preview_label.setText("无预览")

        self.lbl_filename.setText(f"文件名: {photo.filename}")
        self.lbl_path.setText(f"路径: {photo.file_path}")
        self.lbl_size.setText(f"大小: {image_utils.format_size(photo.size_bytes)}")
        self.lbl_dim.setText(f"尺寸: {photo.dimensions_str}")
        self.lbl_ratio.setText(f"比例: {photo.aspect_ratio}")
        shot_str = photo.shot_time.strftime("%Y-%m-%d %H:%M:%S") if photo.shot_time else "未知"
        self.lbl_shot.setText(f"拍摄时间: {shot_str}")
        self.lbl_modified.setText(f"修改时间: {photo.modified_time.strftime('%Y-%m-%d %H:%M:%S')}")

        status_colors = {
            PhotoStatus.KEEP: "#27ae60",
            PhotoStatus.REJECT: "#e74c3c",
            PhotoStatus.DUPLICATE: "#f39c12",
            PhotoStatus.UNPROCESSED: "#666",
        }
        c = status_colors.get(photo.status, "#666")
        self.lbl_status.setText(f'<span style="color:{c}; font-weight:bold;">状态: {photo.status.value}</span>')
        self.lbl_status.setTextFormat(Qt.RichText)

        self.lbl_tags.setText(f"标签: {', '.join(photo.tags) if photo.tags else '(无)'}")
        h = photo.perceptual_hash or photo.hash or "未计算"
        self.lbl_hash.setText(f"哈希: {h[:32]}..." if len(h) > 32 else f"哈希: {h}")

    def refresh(self):
        if self._photo:
            self.set_photo(self._photo)
