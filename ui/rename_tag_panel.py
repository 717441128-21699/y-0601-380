from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QLineEdit, QFrame, QListWidget, QListWidgetItem, QInputDialog,
                               QComboBox, QCheckBox)
from PySide6.QtCore import Qt, Signal
from core.photo_store import PhotoStore


class RenameTagPanel(QWidget):
    rename_requested = Signal(str, list)
    tags_requested = Signal(list, list)
    preview_rename = Signal(str)

    def __init__(self, photo_store: PhotoStore, parent=None):
        super().__init__(parent)
        self.store = photo_store
        self._selected_photos = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("✏️ 命名与标签")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        rename_frame = QFrame()
        rename_frame.setStyleSheet("QFrame { background: #f8f9fa; border-radius: 8px; padding: 12px; }")
        rename_layout = QVBoxLayout(rename_frame)
        rename_layout.setSpacing(8)

        rename_layout.addWidget(QLabel("批量重命名模式:"))

        patterns = [
            ("自定义", "{custom}"),
            ("序号递增", "IMG_{index:04d}{ext}"),
            ("日期_序号", "{date}_{index:03d}{ext}"),
            ("原始_序号", "{original}_{index:02d}{ext}"),
            ("项目_日期_尺寸", "Project_{date}_{dim}{ext}"),
            ("拍摄时间戳", "{datetime}{ext}"),
        ]
        self.pattern_combo = QComboBox()
        for name, patt in patterns:
            self.pattern_combo.addItem(name, patt)
        self.pattern_combo.currentIndexChanged.connect(self._on_pattern_changed)
        rename_layout.addWidget(self.pattern_combo)

        rename_layout.addWidget(QLabel("命名模板:"))
        self.pattern_edit = QLineEdit()
        self.pattern_edit.setPlaceholderText("支持变量: {index} {original} {date} {datetime} {dim} {width} {height} {ext}")
        self.pattern_edit.setText("IMG_{index:04d}{ext}")
        rename_layout.addWidget(self.pattern_edit)

        self.lbl_preview = QLabel("预览: -")
        self.lbl_preview.setStyleSheet("color: #4A90D9; font-size: 11px; padding: 4px; background: #fff; border-radius: 4px;")
        rename_layout.addWidget(self.lbl_preview)

        self.chk_keep_only = QCheckBox("仅重命名已标记保留的照片")
        self.chk_keep_only.setChecked(True)
        rename_layout.addWidget(self.chk_keep_only)

        self.btn_preview = QPushButton("👁 预览命名")
        self.btn_preview.setStyleSheet(self._btn_style("#6c757d"))
        self.btn_preview.clicked.connect(self._do_preview)

        self.btn_rename = QPushButton("📝 执行重命名")
        self.btn_rename.setStyleSheet(self._btn_style("#4A90D9"))
        self.btn_rename.clicked.connect(self._do_rename)
        rename_layout.addWidget(self.btn_preview)
        rename_layout.addWidget(self.btn_rename)

        layout.addWidget(rename_frame)

        tag_frame = QFrame()
        tag_frame.setStyleSheet("QFrame { background: #f8f9fa; border-radius: 8px; padding: 12px; }")
        tag_layout = QVBoxLayout(tag_frame)
        tag_layout.setSpacing(8)

        tag_layout.addWidget(QLabel("项目标签:"))

        tag_input_layout = QHBoxLayout()
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("输入标签后按回车添加")
        self.tag_input.returnPressed.connect(self._add_tag)
        self.btn_add_tag = QPushButton("+")
        self.btn_add_tag.setFixedWidth(36)
        self.btn_add_tag.clicked.connect(self._add_tag)
        tag_input_layout.addWidget(self.tag_input)
        tag_input_layout.addWidget(self.btn_add_tag)
        tag_layout.addLayout(tag_input_layout)

        self.tag_list = QListWidget()
        self.tag_list.setSelectionMode(QListWidget.MultiSelection)
        self.tag_list.setStyleSheet("""
            QListWidget { border: 1px solid #ddd; border-radius: 4px; background: #fff; padding: 4px; }
            QListWidget::item { padding: 4px 8px; border-radius: 3px; }
            QListWidget::item:selected { background: #4A90D9; color: white; }
        """)
        tag_layout.addWidget(self.tag_list)

        tag_btn_layout = QHBoxLayout()
        self.btn_apply_tags = QPushButton("🏷 应用选中标签")
        self.btn_apply_tags.setStyleSheet(self._btn_style("#27ae60"))
        self.btn_apply_tags.clicked.connect(self._apply_tags)
        self.btn_remove_tag = QPushButton("删除标签")
        self.btn_remove_tag.setStyleSheet(self._btn_style("#e74c3c"))
        self.btn_remove_tag.clicked.connect(self._remove_selected_tags)
        tag_btn_layout.addWidget(self.btn_apply_tags)
        tag_btn_layout.addWidget(self.btn_remove_tag)
        tag_layout.addLayout(tag_btn_layout)

        layout.addWidget(tag_frame)
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

    def _on_pattern_changed(self, idx: int):
        patt = self.pattern_combo.itemData(idx)
        if patt != "{custom}":
            self.pattern_edit.setText(patt)

    def _add_tag(self):
        tag = self.tag_input.text().strip()
        if tag and self.tag_list.findItems(tag, Qt.MatchExactly) == []:
            item = QListWidgetItem(tag)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.tag_list.addItem(item)
            self.tag_input.clear()

    def _remove_selected_tags(self):
        for item in self.tag_list.selectedItems():
            self.tag_list.takeItem(self.tag_list.row(item))

    def _get_checked_tags(self) -> list:
        tags = []
        for i in range(self.tag_list.count()):
            item = self.tag_list.item(i)
            if item.checkState() == Qt.Checked:
                tags.append(item.text())
        return tags

    def set_selected_photos(self, photos: list):
        self._selected_photos = photos

    def _target_photos(self) -> list:
        if self._selected_photos:
            photos = self._selected_photos
        else:
            photos = self.store.all_photos
        if self.chk_keep_only.isChecked():
            from core.photo import PhotoStatus
            photos = [p for p in photos if p.status == PhotoStatus.KEEP]
        return photos

    def _do_preview(self):
        from utils import image_utils
        photos = self._target_photos()
        if not photos:
            self.lbl_preview.setText("⚠ 没有符合条件的照片")
            return
        pattern = self.pattern_edit.text()
        previews = []
        for i, p in enumerate(photos[:5]):
            name = image_utils.apply_rename_pattern(pattern, i + 1, p, len(photos))
            previews.append(name)
        preview_text = " → ".join(previews)
        if len(photos) > 5:
            preview_text += f" ... (共{len(photos)}张)"
        self.lbl_preview.setText(f"预览: {preview_text}")

    def _do_rename(self):
        photos = self._target_photos()
        if not photos:
            return
        pattern = self.pattern_edit.text()
        self.rename_requested.emit(pattern, photos)

    def _apply_tags(self):
        tags = self._get_checked_tags()
        if not tags:
            tags = [item.text() for item in self.tag_list.selectedItems()]
        if not tags:
            return
        photos = self._selected_photos if self._selected_photos else self.store.all_photos
        if photos:
            self.tags_requested.emit(tags, photos)

    def refresh_tags(self):
        existing = set()
        for i in range(self.tag_list.count()):
            existing.add(self.tag_list.item(i).text())
        for t in self.store.get_all_tags():
            if t not in existing:
                item = QListWidgetItem(t)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.tag_list.addItem(item)
