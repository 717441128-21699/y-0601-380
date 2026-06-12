from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QFileDialog, QProgressBar, QFrame, QCheckBox, QSpinBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QPainter, QColor, QFont
from modules.import_module import PhotoLoader
from utils import image_utils


class DropArea(QLabel):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(160)
        self.setStyleSheet("""
            DropArea {
                border: 2px dashed #aaa;
                border-radius: 12px;
                background: #fafafa;
                color: #666;
                font-size: 14px;
            }
            DropArea:hover {
                border-color: #4A90D9;
                background: #f0f7ff;
                color: #4A90D9;
            }
        """)
        self._update_text()

    def _update_text(self, dragging=False):
        if dragging:
            self.setText("📁 释放以导入照片")
        else:
            self.setText("📂 拖入文件夹或点击选择\n支持 JPG, PNG, TIFF, RAW 等格式")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._update_text(True)

    def dragLeaveEvent(self, event):
        self._update_text(False)

    def dropEvent(self, event: QDropEvent):
        self._update_text(False)
        paths = []
        for url in event.mimeData().urls():
            local_path = url.toLocalFile()
            if local_path:
                paths.append(local_path)
        if paths:
            self.files_dropped.emit(paths)


class ImportPanel(QWidget):
    photos_loaded = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loader = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("📥 导入照片")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self._on_files_dropped)
        layout.addWidget(self.drop_area)

        btn_layout = QHBoxLayout()
        self.btn_select_folder = QPushButton("选择文件夹")
        self.btn_select_folder.setStyleSheet(self._button_style("#4A90D9"))
        self.btn_select_folder.clicked.connect(self._select_folder)

        self.btn_select_files = QPushButton("选择文件")
        self.btn_select_files.setStyleSheet(self._button_style("#6c757d"))
        self.btn_select_files.clicked.connect(self._select_files)

        btn_layout.addWidget(self.btn_select_folder)
        btn_layout.addWidget(self.btn_select_files)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        options_frame = QFrame()
        options_frame.setStyleSheet("QFrame { background: #f8f9fa; border-radius: 8px; padding: 8px; }")
        options_layout = QHBoxLayout(options_frame)
        self.chk_recursive = QCheckBox("包含子文件夹")
        self.chk_recursive.setChecked(True)
        self.spin_thumbs = QSpinBox()
        self.spin_thumbs.setRange(64, 512)
        self.spin_thumbs.setValue(200)
        self.spin_thumbs.setPrefix("缩略图尺寸: ")
        self.spin_thumbs.setSuffix(" px")
        options_layout.addWidget(self.chk_recursive)
        options_layout.addStretch()
        options_layout.addWidget(self.spin_thumbs)
        layout.addWidget(options_frame)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #ddd; border-radius: 4px; text-align: center; height: 20px; }
            QProgressBar::chunk { background: #4A90D9; border-radius: 3px; }
        """)
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("就绪")
        self.lbl_status.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        layout.addStretch()

    def _button_style(self, color: str) -> str:
        return f"""
            QPushButton {{
                background: {color};
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {color}dd; }}
            QPushButton:disabled {{ background: #ccc; }}
        """

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择照片文件夹")
        if folder:
            self._on_files_dropped([folder])

    def _select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择照片文件", "",
            "图片文件 (*.jpg *.jpeg *.png *.gif *.bmp *.tiff *.webp *.raw *.cr2 *.nef *.arw *.heic)"
        )
        if files:
            self._on_files_dropped(files)

    def _on_files_dropped(self, paths: list):
        file_paths = []
        for p in paths:
            path = Path(p)
            if path.is_dir():
                file_paths.extend(image_utils.scan_directory(str(path), self.chk_recursive.isChecked()))
            elif path.is_file() and image_utils.is_image_file(str(path)):
                file_paths.append(str(path))

        if not file_paths:
            self.lbl_status.setText("未找到支持的图片文件")
            return

        self.lbl_status.setText(f"正在加载 {len(file_paths)} 张照片...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(file_paths))
        self.progress_bar.setValue(0)
        self._set_buttons_enabled(False)

        self._loader = PhotoLoader(file_paths)
        self._loader.progress.connect(self._on_progress)
        self._loader.finished_loading.connect(self._on_finished)
        self._loader.start()

    def _on_progress(self, current: int, total: int, filepath: str):
        self.progress_bar.setValue(current)
        self.lbl_status.setText(f"加载中... ({current}/{total}) {Path(filepath).name[:40]}")

    def _on_finished(self, photos: list):
        self.progress_bar.setVisible(False)
        self._set_buttons_enabled(True)
        if photos:
            self.lbl_status.setText(f"✅ 成功导入 {len(photos)} 张照片")
            self.photos_loaded.emit(photos)
        else:
            self.lbl_status.setText("未加载到任何照片")

    def _set_buttons_enabled(self, enabled: bool):
        self.btn_select_folder.setEnabled(enabled)
        self.btn_select_files.setEnabled(enabled)
