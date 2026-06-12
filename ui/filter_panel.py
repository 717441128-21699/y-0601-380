from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QComboBox, QFrame, QButtonGroup, QRadioButton, QListWidget,
                               QListWidgetItem, QSplitter)
from PySide6.QtCore import Qt, Signal
from core.photo_store import PhotoStore
from core.photo import Photo, PhotoStatus


class FilterPanel(QWidget):
    filter_changed = Signal(dict)
    group_mode_changed = Signal(str)
    action_requested = Signal(str)

    def __init__(self, photo_store: PhotoStore, parent=None):
        super().__init__(parent)
        self.store = photo_store
        self._current_group_mode = "none"
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("🔍 筛选与分组")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        group_frame = QFrame()
        group_frame.setStyleSheet("QFrame { background: #f8f9fa; border-radius: 8px; padding: 12px; }")
        group_layout = QVBoxLayout(group_frame)
        group_layout.setSpacing(8)
        group_layout.addWidget(QLabel("分组方式:"))

        self.group_none = QRadioButton("不分组")
        self.group_date = QRadioButton("按拍摄日期")
        self.group_dim = QRadioButton("按尺寸")
        self.group_ratio = QRadioButton("按比例")
        self.group_status = QRadioButton("按状态")

        btn_group = QButtonGroup(self)
        for b in [self.group_none, self.group_date, self.group_dim, self.group_ratio, self.group_status]:
            btn_group.addButton(b)
            group_layout.addWidget(b)
        self.group_none.setChecked(True)
        btn_group.buttonClicked.connect(self._on_group_mode)

        layout.addWidget(group_frame)

        filter_frame = QFrame()
        filter_frame.setStyleSheet("QFrame { background: #f8f9fa; border-radius: 8px; padding: 12px; }")
        filter_layout = QVBoxLayout(filter_frame)
        filter_layout.setSpacing(8)
        filter_layout.addWidget(QLabel("状态筛选:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["全部", "未处理", "保留", "淘汰", "重复"])
        self.status_combo.currentIndexChanged.connect(self._emit_filter)
        filter_layout.addWidget(self.status_combo)

        filter_layout.addWidget(QLabel("标签筛选:"))
        self.tag_combo = QComboBox()
        self.tag_combo.addItem("全部标签")
        self.tag_combo.currentIndexChanged.connect(self._emit_filter)
        filter_layout.addWidget(self.tag_combo)
        layout.addWidget(filter_frame)

        action_frame = QFrame()
        action_frame.setStyleSheet("QFrame { background: #f8f9fa; border-radius: 8px; padding: 12px; }")
        action_layout = QVBoxLayout(action_frame)
        action_layout.setSpacing(8)
        action_layout.addWidget(QLabel("快捷操作:"))

        btn_row1 = QHBoxLayout()
        self.btn_keep_sel = QPushButton("✓ 保留选中")
        self.btn_keep_sel.setStyleSheet(self._btn_style("#27ae60"))
        self.btn_keep_sel.clicked.connect(lambda: self.action_requested.emit("keep_selected"))

        self.btn_reject_sel = QPushButton("✗ 淘汰选中")
        self.btn_reject_sel.setStyleSheet(self._btn_style("#e74c3c"))
        self.btn_reject_sel.clicked.connect(lambda: self.action_requested.emit("reject_selected"))
        btn_row1.addWidget(self.btn_keep_sel)
        btn_row1.addWidget(self.btn_reject_sel)
        action_layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        self.btn_select_all = QPushButton("全选")
        self.btn_select_all.setStyleSheet(self._btn_style("#6c757d"))
        self.btn_select_all.clicked.connect(lambda: self.action_requested.emit("select_all"))

        self.btn_clear_sel = QPushButton("取消选择")
        self.btn_clear_sel.setStyleSheet(self._btn_style("#6c757d"))
        self.btn_clear_sel.clicked.connect(lambda: self.action_requested.emit("clear_selection"))
        btn_row2.addWidget(self.btn_select_all)
        btn_row2.addWidget(self.btn_clear_sel)
        action_layout.addLayout(btn_row2)

        self.btn_detect_dup = QPushButton("🔎 检测重复文件")
        self.btn_detect_dup.setStyleSheet(self._btn_style("#f39c12"))
        self.btn_detect_dup.clicked.connect(lambda: self.action_requested.emit("detect_duplicates"))
        action_layout.addWidget(self.btn_detect_dup)

        layout.addWidget(action_frame)

        stats_frame = QFrame()
        stats_frame.setStyleSheet("QFrame { background: #fff; border: 1px solid #e5e5e5; border-radius: 8px; padding: 12px; }")
        stats_layout = QVBoxLayout(stats_frame)
        self.lbl_stats = QLabel("总计: 0 张")
        self.lbl_stats.setStyleSheet("font-weight: bold;")
        self.lbl_keep = QLabel("🟢 保留: 0")
        self.lbl_reject = QLabel("🔴 淘汰: 0")
        self.lbl_dup = QLabel("🟡 重复: 0")
        self.lbl_unprocessed = QLabel("⚪ 未处理: 0")
        for lbl in [self.lbl_stats, self.lbl_keep, self.lbl_reject, self.lbl_dup, self.lbl_unprocessed]:
            stats_layout.addWidget(lbl)
        layout.addWidget(stats_frame)

        layout.addStretch()

    def _btn_style(self, color: str) -> str:
        return f"""
            QPushButton {{
                background: {color};
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: {color}dd; }}
        """

    def _on_group_mode(self, btn):
        mode_map = {
            self.group_none: "none",
            self.group_date: "date",
            self.group_dim: "dimensions",
            self.group_ratio: "ratio",
            self.group_status: "status",
        }
        self._current_group_mode = mode_map.get(btn, "none")
        self.group_mode_changed.emit(self._current_group_mode)

    def _emit_filter(self):
        status_map = {
            0: None,
            1: PhotoStatus.UNPROCESSED,
            2: PhotoStatus.KEEP,
            3: PhotoStatus.REJECT,
            4: PhotoStatus.DUPLICATE,
        }
        status = status_map.get(self.status_combo.currentIndex())
        tag = None if self.tag_combo.currentIndex() <= 0 else self.tag_combo.currentText()
        self.filter_changed.emit({"status": status, "tag": tag})

    def refresh_tags(self):
        current = self.tag_combo.currentText()
        self.tag_combo.blockSignals(True)
        self.tag_combo.clear()
        self.tag_combo.addItem("全部标签")
        for t in self.store.get_all_tags():
            self.tag_combo.addItem(t)
        idx = self.tag_combo.findText(current)
        if idx >= 0:
            self.tag_combo.setCurrentIndex(idx)
        self.tag_combo.blockSignals(False)

    def refresh_stats(self):
        total = self.store.count
        self.lbl_stats.setText(f"总计: {total} 张")
        self.lbl_keep.setText(f"🟢 保留: {len(self.store.get_by_status(PhotoStatus.KEEP))}")
        self.lbl_reject.setText(f"🔴 淘汰: {len(self.store.get_by_status(PhotoStatus.REJECT))}")
        self.lbl_dup.setText(f"🟡 重复: {len(self.store.get_by_status(PhotoStatus.DUPLICATE))}")
        self.lbl_unprocessed.setText(f"⚪ 未处理: {len(self.store.get_by_status(PhotoStatus.UNPROCESSED))}")

    @property
    def group_mode(self) -> str:
        return self._current_group_mode
