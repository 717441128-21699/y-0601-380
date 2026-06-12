from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                               QMenu, QSizePolicy, QToolButton, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, Signal, QSize, QPoint
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QFont, QIcon, QAction
from core.photo import Photo, PhotoStatus
from modules.import_module import pil_to_qpixmap
from utils import image_utils


class PhotoCard(QFrame):
    clicked = Signal(object)
    double_clicked = Signal(object)
    status_changed = Signal(object, object)

    def __init__(self, photo: Photo, parent=None):
        super().__init__(parent)
        self.photo = photo
        self._selected = False
        self.setFixedSize(180, 220)
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_ui()
        self._update_style()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self.thumb_label = QLabel()
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setFixedSize(164, 140)
        self.thumb_label.setStyleSheet("background: #f5f5f5; border-radius: 4px;")
        self._render_thumbnail()
        layout.addWidget(self.thumb_label)

        self.name_label = QLabel(self.photo.filename)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setFixedHeight(36)
        font = QFont()
        font.setPointSize(8)
        self.name_label.setFont(font)
        layout.addWidget(self.name_label)

        info_layout = QHBoxLayout()
        self.info_label = QLabel(f"{self.photo.dimensions_str} | {self.photo.size_mb}MB")
        self.info_label.setStyleSheet("color: #666; font-size: 9px;")
        self.info_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.info_label)
        layout.addLayout(info_layout)

        self.status_badge = QLabel()
        self.status_badge.setAlignment(Qt.AlignCenter)
        self.status_badge.setFixedHeight(18)
        layout.addWidget(self.status_badge)

    def _render_thumbnail(self):
        if self.photo.thumbnail:
            pixmap = pil_to_qpixmap(self.photo.thumbnail)
            if not pixmap.isNull():
                scaled = pixmap.scaled(164, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.thumb_label.setPixmap(scaled)
                return
        self.thumb_label.setText("无预览")

    def _update_style(self):
        border_color = "#4A90D9" if self._selected else "#ddd"
        bg_color = "#e8f3ff" if self._selected else "#fff"
        self.setStyleSheet(f"""
            PhotoCard {{
                background: {bg_color};
                border: 2px solid {border_color};
                border-radius: 8px;
            }}
            PhotoCard:hover {{
                border-color: #4A90D9;
            }}
        """)

        status_colors = {
            PhotoStatus.UNPROCESSED: ("#999", "#f0f0f0"),
            PhotoStatus.KEEP: ("#fff", "#27ae60"),
            PhotoStatus.REJECT: ("#fff", "#e74c3c"),
            PhotoStatus.DUPLICATE: ("#fff", "#f39c12"),
        }
        text_color, bg = status_colors.get(self.photo.status, ("#999", "#f0f0f0"))
        self.status_badge.setText(f"● {self.photo.status.value}")
        self.status_badge.setStyleSheet(f"color: {text_color}; background: {bg}; border-radius: 9px; font-size: 10px; font-weight: bold; padding: 0 8px;")

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()

    @property
    def is_selected(self) -> bool:
        return self._selected

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.photo)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.photo)
        super().mouseDoubleClickEvent(event)

    def _show_menu(self, pos: QPoint):
        menu = QMenu(self)
        act_keep = QAction("标记为保留 (K)", self)
        act_reject = QAction("标记为淘汰 (X)", self)
        act_reset = QAction("重置状态", self)
        menu.addAction(act_keep)
        menu.addAction(act_reject)
        menu.addSeparator()
        menu.addAction(act_reset)
        action = menu.exec(self.mapToGlobal(pos))
        if action == act_keep:
            self.status_changed.emit(self.photo, PhotoStatus.KEEP)
        elif action == act_reject:
            self.status_changed.emit(self.photo, PhotoStatus.REJECT)
        elif action == act_reset:
            self.status_changed.emit(self.photo, PhotoStatus.UNPROCESSED)


class ThumbnailGridView(QWidget):
    photo_clicked = Signal(object)
    photo_double_clicked = Signal(object)
    photo_status_changed = Signal(object, object)
    selection_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: dict = {}
        self._selected_photos: list = []
        self._init_ui()

    def _init_ui(self):
        from PySide6.QtWidgets import QScrollArea, QGridLayout
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: #fafafa; }")

        self.container = QWidget()
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setContentsMargins(16, 16, 16, 16)
        self.scroll.setWidget(self.container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.scroll)

    def set_photos(self, photos: list):
        self.clear()
        cols = 5
        for i, photo in enumerate(photos):
            card = PhotoCard(photo)
            card.clicked.connect(self._on_card_clicked)
            card.double_clicked.connect(self.photo_double_clicked.emit)
            card.status_changed.connect(self.photo_status_changed.emit)
            row, col = divmod(i, cols)
            self.grid_layout.addWidget(card, row, col)
            self._cards[str(photo.file_path)] = card

    def clear(self):
        for card in self._cards.values():
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()
        self._selected_photos.clear()

    def _on_card_clicked(self, photo: Photo):
        from PySide6.QtWidgets import QApplication
        modifiers = QApplication.keyboardModifiers()
        key = str(photo.file_path)
        if modifiers & Qt.ControlModifier:
            if key in [str(p.file_path) for p in self._selected_photos]:
                self._selected_photos = [p for p in self._selected_photos if str(p.file_path) != key]
                if key in self._cards:
                    self._cards[key].set_selected(False)
            else:
                self._selected_photos.append(photo)
                if key in self._cards:
                    self._cards[key].set_selected(True)
        elif modifiers & Qt.ShiftModifier:
            pass
        else:
            for p in self._selected_photos:
                k = str(p.file_path)
                if k in self._cards:
                    self._cards[k].set_selected(False)
            self._selected_photos = [photo]
            if key in self._cards:
                self._cards[key].set_selected(True)
        self.photo_clicked.emit(photo)
        self.selection_changed.emit(self._selected_photos)

    @property
    def selected_photos(self) -> list:
        return self._selected_photos

    def select_all(self):
        self._selected_photos = [c.photo for c in self._cards.values()]
        for card in self._cards.values():
            card.set_selected(True)
        self.selection_changed.emit(self._selected_photos)

    def clear_selection(self):
        for p in self._selected_photos:
            k = str(p.file_path)
            if k in self._cards:
                self._cards[k].set_selected(False)
        self._selected_photos.clear()
        self.selection_changed.emit([])

    def refresh_photo(self, photo: Photo):
        key = str(photo.file_path)
        if key in self._cards:
            self._cards[key]._update_style()
