from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QFileDialog, QFrame, QCheckBox, QSpinBox, QComboBox, QLineEdit)
from PySide6.QtCore import Qt, Signal
from core.photo_store import PhotoStore
from core.photo import PhotoStatus


class BatchPanel(QWidget):
    batch_requested = Signal(str, dict)

    def __init__(self, photo_store: PhotoStore, parent=None):
        super().__init__(parent)
        self.store = photo_store
        self._selected_photos = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("⚙️ 批处理")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        move_frame = QFrame()
        move_frame.setStyleSheet("QFrame { background: #f8f9fa; border-radius: 8px; padding: 12px; }")
        move_layout = QVBoxLayout(move_frame)
        move_layout.setSpacing(8)

        move_layout.addWidget(QLabel("📦 移动到指定目录:"))
        path_layout = QHBoxLayout()
        self.target_dir_edit = QLineEdit_path()
        self.target_dir_edit.setPlaceholderText("选择目标目录...")
        self.btn_browse_dir = QPushButton("浏览...")
        self.btn_browse_dir.clicked.connect(self._browse_dir)
        path_layout.addWidget(self.target_dir_edit)
        path_layout.addWidget(self.btn_browse_dir)
        move_layout.addLayout(path_layout)

        self.chk_move_keep_only = QCheckBox("仅移动已标记保留的照片")
        self.chk_move_keep_only.setChecked(True)
        move_layout.addWidget(self.chk_move_keep_only)

        self.btn_move = QPushButton("🚚 移动文件")
        self.btn_move.setStyleSheet(self._btn_style("#4A90D9"))
        self.btn_move.clicked.connect(self._do_move)
        move_layout.addWidget(self.btn_move)

        layout.addWidget(move_frame)

        compress_frame = QFrame()
        compress_frame.setStyleSheet("QFrame { background: #f8f9fa; border-radius: 8px; padding: 12px; }")
        compress_layout = QVBoxLayout(compress_frame)
        compress_layout.setSpacing(8)

        compress_layout.addWidget(QLabel("🗜 压缩副本:"))
        compress_path_layout = QHBoxLayout()
        self.compress_dir_edit = QLineEdit_path()
        self.compress_dir_edit.setPlaceholderText("压缩输出目录...")
        self.btn_browse_compress = QPushButton("浏览...")
        self.btn_browse_compress.clicked.connect(self._browse_compress_dir)
        compress_path_layout.addWidget(self.compress_dir_edit)
        compress_path_layout.addWidget(self.btn_browse_compress)
        compress_layout.addLayout(compress_path_layout)

        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("JPEG 质量:"))
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(10, 100)
        self.quality_spin.setValue(80)
        self.quality_spin.setSuffix(" %")
        quality_layout.addWidget(self.quality_spin)
        quality_layout.addStretch()
        compress_layout.addLayout(quality_layout)

        self.chk_compress_keep_only = QCheckBox("仅压缩已标记保留的照片")
        self.chk_compress_keep_only.setChecked(True)
        compress_layout.addWidget(self.chk_compress_keep_only)

        self.btn_compress = QPushButton("🗜 生成压缩副本")
        self.btn_compress.setStyleSheet(self._btn_style("#9b59b6"))
        self.btn_compress.clicked.connect(self._do_compress)
        compress_layout.addWidget(self.btn_compress)

        layout.addWidget(compress_frame)

        manifest_frame = QFrame()
        manifest_frame.setStyleSheet("QFrame { background: #f8f9fa; border-radius: 8px; padding: 12px; }")
        manifest_layout = QVBoxLayout(manifest_frame)
        manifest_layout.setSpacing(8)

        manifest_layout.addWidget(QLabel("📋 生成交付清单:"))
        fmt_layout = QHBoxLayout()
        fmt_layout.addWidget(QLabel("格式:"))
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["CSV (Excel兼容)", "JSON"])
        fmt_layout.addWidget(self.fmt_combo)
        fmt_layout.addStretch()
        manifest_layout.addLayout(fmt_layout)

        manifest_path_layout = QHBoxLayout()
        self.manifest_edit = QLineEdit_path()
        self.manifest_edit.setPlaceholderText("清单保存路径...")
        self.btn_browse_manifest = QPushButton("另存为...")
        self.btn_browse_manifest.clicked.connect(self._browse_manifest)
        manifest_path_layout.addWidget(self.manifest_edit)
        manifest_path_layout.addWidget(self.btn_browse_manifest)
        manifest_layout.addLayout(manifest_path_layout)

        self.btn_manifest = QPushButton("📋 生成交付清单")
        self.btn_manifest.setStyleSheet(self._btn_style("#27ae60"))
        self.btn_manifest.clicked.connect(self._do_manifest)
        manifest_layout.addWidget(self.btn_manifest)

        layout.addWidget(manifest_frame)

        delete_frame = QFrame()
        delete_frame.setStyleSheet("QFrame { background: #fef0f0; border: 1px solid #f5c6cb; border-radius: 8px; padding: 12px; }")
        delete_layout = QVBoxLayout(delete_frame)
        delete_layout.setSpacing(8)

        delete_layout.addWidget(QLabel("⚠️ 删除淘汰照片 (移至回收站):"))
        self.btn_delete = QPushButton("🗑 删除已淘汰照片")
        self.btn_delete.setStyleSheet(self._btn_style("#e74c3c"))
        self.btn_delete.clicked.connect(self._do_delete)
        delete_layout.addWidget(self.btn_delete)
        layout.addWidget(delete_frame)

        layout.addStretch()

    def _btn_style(self, color: str) -> str:
        return f"""
            QPushButton {{
                background: {color};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {color}dd; }}
        """

    def _browse_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "选择目标目录")
        if folder:
            self.target_dir_edit.setText(folder)

    def _browse_compress_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "选择压缩输出目录")
        if folder:
            self.compress_dir_edit.setText(folder)

    def _browse_manifest(self):
        fmt = "csv" if self.fmt_combo.currentIndex() == 0 else "json"
        ext = "CSV 文件 (*.csv)" if fmt == "csv" else "JSON 文件 (*.json)"
        path, _ = QFileDialog.getSaveFileName(self, "保存交付清单", f"manifest.{fmt}", ext)
        if path:
            self.manifest_edit.setText(path)

    def set_selected_photos(self, photos: list):
        self._selected_photos = photos

    def _target_photos(self, keep_only: bool) -> list:
        if self._selected_photos:
            photos = self._selected_photos
        else:
            photos = self.store.all_photos
        if keep_only:
            photos = [p for p in photos if p.status == PhotoStatus.KEEP]
        return photos

    def _do_move(self):
        target = self.target_dir_edit.text().strip()
        if not target:
            return
        photos = self._target_photos(self.chk_move_keep_only.isChecked())
        if not photos:
            return
        self.batch_requested.emit("move", {
            "target_directory": target,
            "photos": photos,
        })

    def _do_compress(self):
        target = self.compress_dir_edit.text().strip()
        if not target:
            return
        photos = self._target_photos(self.chk_compress_keep_only.isChecked())
        if not photos:
            return
        self.batch_requested.emit("compress", {
            "target_directory": target,
            "quality": self.quality_spin.value(),
            "photos": photos,
        })

    def _do_manifest(self):
        path = self.manifest_edit.text().strip()
        if not path:
            return
        fmt = "csv" if self.fmt_combo.currentIndex() == 0 else "json"
        photos = self.store.all_photos
        self.batch_requested.emit("manifest", {
            "output_path": path,
            "format": fmt,
            "photos": photos,
        })

    def _do_delete(self):
        from PySide6.QtWidgets import QMessageBox
        rejected = [p for p in self.store.all_photos if p.status == PhotoStatus.REJECT]
        if not rejected:
            QMessageBox.information(self, "提示", "没有已标记为淘汰的照片")
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要将 {len(rejected)} 张已淘汰照片移至回收站吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.batch_requested.emit("delete_reject", {"photos": rejected})


class QLineEdit_path(QLineEdit):
    pass
