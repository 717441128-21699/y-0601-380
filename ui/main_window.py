import os
import sys
from pathlib import Path
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QTabWidget, QSplitter, QLabel, QStatusBar, QToolBar,
                               QMessageBox, QApplication)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QKeySequence, QIcon

from core.photo_store import PhotoStore
from core.photo import Photo, PhotoStatus
from core.task import Task, TaskType, TaskStatus
from core.event_bus import EventBus
from core.history_rule import HistoryRule
from modules.task_queue import TaskManager
from utils.undo_manager import UndoManager

from ui.import_panel import ImportPanel
from ui.filter_panel import FilterPanel
from ui.rename_tag_panel import RenameTagPanel
from ui.batch_panel import BatchPanel
from ui.task_queue_panel import TaskQueuePanel
from ui.history_panel import HistoryPanel
from ui.thumbnail_grid import ThumbnailGridView
from ui.photo_detail_panel import PhotoDetailPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PhotoFlow - 个人照片素材整理工具")
        self.setMinimumSize(1400, 850)
        self.resize(1600, 950)

        self.store = PhotoStore()
        self.tm = TaskManager()
        self.undo_mgr = UndoManager()
        self.bus = EventBus.instance()
        self._pending_undo: dict = {}

        self._build_ui()
        self._build_toolbar()
        self._connect_signals()
        self._apply_stylesheet()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        left_splitter = QSplitter(Qt.Horizontal)

        self.left_tabs = QTabWidget()
        self.left_tabs.setTabPosition(QTabWidget.West)
        self.left_tabs.setIconSize(QSize(24, 24))
        self.left_tabs.setFixedWidth(360)

        self.import_panel = ImportPanel()
        self.filter_panel = FilterPanel(self.store)
        self.rename_tag_panel = RenameTagPanel(self.store)
        self.batch_panel = BatchPanel(self.store)
        self.history_panel = HistoryPanel()

        self.left_tabs.addTab(self.import_panel, "📥 导入")
        self.left_tabs.addTab(self.filter_panel, "🔍 筛选")
        self.left_tabs.addTab(self.rename_tag_panel, "✏️ 命名标签")
        self.left_tabs.addTab(self.batch_panel, "⚙️ 批处理")
        self.left_tabs.addTab(self.history_panel, "📚 历史")

        left_splitter.addWidget(self.left_tabs)

        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(8, 8, 8, 8)
        center_layout.setSpacing(6)

        header = QLabel("📷 照片整理工作区")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; padding: 8px 12px;")
        center_layout.addWidget(header)

        self.group_label = QLabel("")
        self.group_label.setStyleSheet("color: #666; padding: 4px 12px; font-size: 12px;")
        center_layout.addWidget(self.group_label)

        self.thumb_grid = ThumbnailGridView()
        center_layout.addWidget(self.thumb_grid, 1)

        left_splitter.addWidget(center_widget)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.right_tabs = QTabWidget()
        self.right_tabs.setTabPosition(QTabWidget.East)

        self.detail_panel = PhotoDetailPanel()
        self.task_panel = TaskQueuePanel(self.tm)

        self.right_tabs.addTab(self.detail_panel, "🖼 详情")
        self.right_tabs.addTab(self.task_panel, "📋 任务队列")
        self.right_tabs.setFixedWidth(380)
        right_layout.addWidget(self.right_tabs)

        left_splitter.addWidget(right_panel)

        left_splitter.setStretchFactor(0, 0)
        left_splitter.setStretchFactor(1, 1)
        left_splitter.setStretchFactor(2, 0)
        left_splitter.setSizes([360, 800, 380])

        main_layout.addWidget(left_splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_count = QLabel("就绪")
        self.status_bar.addWidget(self.lbl_count)

    def _build_toolbar(self):
        tb = QToolBar("主工具栏")
        tb.setIconSize(QSize(20, 20))
        tb.setMovable(False)
        tb.setStyleSheet("""
            QToolBar { background: #f8f9fa; border-bottom: 1px solid #e5e5e5; padding: 4px; spacing: 4px; }
            QToolBar QToolButton { padding: 6px 10px; border-radius: 4px; }
            QToolBar QToolButton:hover { background: #e0e8f0; }
        """)
        self.addToolBar(tb)

        act_keep = QAction("✓ 保留 (K)", self)
        act_keep.setShortcut(QKeySequence("K"))
        act_keep.triggered.connect(lambda: self._bulk_status(PhotoStatus.KEEP))
        tb.addAction(act_keep)

        act_reject = QAction("✗ 淘汰 (X)", self)
        act_reject.setShortcut(QKeySequence("X"))
        act_reject.triggered.connect(lambda: self._bulk_status(PhotoStatus.REJECT))
        tb.addAction(act_reject)

        tb.addSeparator()

        act_select_all = QAction("⌘A 全选", self)
        act_select_all.setShortcut(QKeySequence.SelectAll)
        act_select_all.triggered.connect(self.thumb_grid.select_all)
        tb.addAction(act_select_all)

        act_undo = QAction("↩ 撤销 (Ctrl+Z)", self)
        act_undo.setShortcut(QKeySequence.Undo)
        act_undo.triggered.connect(self._do_undo)
        tb.addAction(act_undo)

        tb.addSeparator()

        act_dedup = QAction("🔎 检测重复", self)
        act_dedup.triggered.connect(lambda: self._action_handler("detect_duplicates"))
        tb.addAction(act_dedup)

        act_clear = QAction("🗑 清空工作区", self)
        act_clear.triggered.connect(self._clear_workspace)
        tb.addAction(act_clear)

    def _connect_signals(self):
        self.import_panel.photos_loaded.connect(self._on_photos_loaded)
        self.filter_panel.filter_changed.connect(self._apply_filter)
        self.filter_panel.group_mode_changed.connect(self._apply_grouping)
        self.filter_panel.action_requested.connect(self._action_handler)
        self.rename_tag_panel.rename_requested.connect(self._on_rename_request)
        self.rename_tag_panel.tags_requested.connect(self._on_tags_request)
        self.batch_panel.batch_requested.connect(self._on_batch_request)
        self.task_panel.control_requested.connect(self._task_control)
        self.task_panel.undo_requested.connect(self._do_undo)
        self.history_panel.rule_applied.connect(self._apply_rule)
        self.history_panel.capture_requested.connect(self._capture_rule)

        self.thumb_grid.photo_clicked.connect(self.detail_panel.set_photo)
        self.thumb_grid.photo_double_clicked.connect(self._open_photo_external)
        self.thumb_grid.photo_status_changed.connect(self._on_photo_status_changed)
        self.thumb_grid.selection_changed.connect(self._on_selection_changed)

        self.detail_panel.status_changed.connect(self._on_photo_status_changed)
        self.detail_panel.open_external.connect(self._open_photo_external)

        self.store.photos_changed.connect(self._refresh_all)

        self.bus.log_message.connect(self.task_panel.append_log)
        self.bus.log_message.connect(self._on_log_message)

        self.undo_mgr.stack_changed.connect(self._on_undo_changed)

        self.tm.task_updated.connect(self._on_task_updated)
        self.bus.task_completed.connect(self._on_task_completed)
        self.bus.task_failed.connect(self._on_task_failed)
        self.bus.photo_tags_changed.connect(self._on_photo_tags_changed)

    def _apply_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow { background: #f5f6f8; }
            QTabWidget::pane { border: 1px solid #e5e5e5; background: white; border-radius: 4px; }
            QTabBar::tab {
                background: #eef0f3;
                padding: 16px 8px;
                border: none;
                border-right: 2px solid transparent;
                min-width: 48px;
                font-size: 12px;
                color: #555;
            }
            QTabBar::tab:selected {
                background: white;
                color: #4A90D9;
                border-right: 3px solid #4A90D9;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected { background: #e4e8ef; }
            QLabel { color: #333; }
        """)

    def _on_photos_loaded(self, photos: list):
        self.store.add_photos(photos)
        self.left_tabs.setCurrentIndex(1)

    def _refresh_all(self):
        self._apply_filter_and_group()
        self.filter_panel.refresh_stats()
        self.filter_panel.refresh_tags()
        self.rename_tag_panel.refresh_tags()
        self.lbl_count.setText(f"共 {self.store.count} 张照片 | 选中 {len(self.thumb_grid.selected_photos)} 张")

    def _apply_filter(self, filters: dict = None):
        self._apply_filter_and_group()

    def _apply_grouping(self, mode: str):
        self._apply_filter_and_group()

    def _apply_filter_and_group(self):
        status = None
        tag = None
        if hasattr(self.filter_panel, 'status_combo'):
            idx = self.filter_panel.status_combo.currentIndex()
            smap = {1: PhotoStatus.UNPROCESSED, 2: PhotoStatus.KEEP,
                    3: PhotoStatus.REJECT, 4: PhotoStatus.DUPLICATE}
            status = smap.get(idx)
            tag_idx = self.filter_panel.tag_combo.currentIndex()
            if tag_idx > 0:
                tag = self.filter_panel.tag_combo.currentText()

        photos = self.store.all_photos
        if status:
            photos = [p for p in photos if p.status == status]
        if tag:
            photos = [p for p in photos if tag in p.tags]

        mode = self.filter_panel.group_mode
        if mode == "date":
            groups = self.store.group_by_date()
            self.group_label.setText(f"按日期分组 ({len(groups)} 组)")
        elif mode == "dimensions":
            groups = self.store.group_by_dimensions()
            self.group_label.setText(f"按尺寸分组 ({len(groups)} 组)")
        elif mode == "ratio":
            groups = self.store.group_by_ratio()
            self.group_label.setText(f"按比例分组 ({len(groups)} 组)")
        elif mode == "status":
            groups = self.store.group_by_status()
            self.group_label.setText(f"按状态分组 ({len(groups)} 组)")
        else:
            self.group_label.setText(f"全部照片 ({len(photos)} 张)")
            self.thumb_grid.set_photos(photos)
            return

        ordered = []
        for key in sorted(groups.keys(), reverse=True):
            ordered.extend([p for p in groups[key] if p in photos])
        self.thumb_grid.set_photos(ordered)

    def _action_handler(self, action: str):
        if action == "keep_selected":
            self._bulk_status(PhotoStatus.KEEP)
        elif action == "reject_selected":
            self._bulk_status(PhotoStatus.REJECT)
        elif action == "select_all":
            self.thumb_grid.select_all()
        elif action == "clear_selection":
            self.thumb_grid.clear_selection()
        elif action == "detect_duplicates":
            self._detect_duplicates()

    def _bulk_status(self, status: PhotoStatus):
        photos = self.thumb_grid.selected_photos or self.store.all_photos
        if not photos:
            return
        old_states = [(p, p.status) for p in photos]
        for p, old in old_states:
            self.store.update_photo_status(p, status)
            self.thumb_grid.refresh_photo(p)
        if self.detail_panel._photo:
            self.detail_panel.refresh()
        self._push_undo_status(old_states, status)

    def _on_photo_status_changed(self, photo: Photo, new_status: PhotoStatus):
        old_status = photo.status
        if old_status == new_status:
            return
        self.store.update_photo_status(photo, new_status)
        self.thumb_grid.refresh_photo(photo)
        self.detail_panel.refresh()
        self.filter_panel.refresh_stats()
        self._push_undo_status([(photo, old_status)], new_status)

    def _on_photo_tags_changed(self, photo: Photo, new_tags: list):
        self.thumb_grid.refresh_photo(photo)
        self.detail_panel.refresh()
        self.filter_panel.refresh_tags()

    def _on_task_updated(self, task: Task):
        pass

    def _on_task_completed(self, task: Task):
        pending = self._pending_undo.pop(task.task_id, None)
        if pending and task.result:
            if pending["type"] == "rename":
                rename_map = task.result.get("rename_map", {})
                if rename_map:
                    self._push_undo_rename(rename_map)
            elif pending["type"] == "tags":
                photos = [p for p, _ in pending["old_states"]]
                self._push_undo_tags(photos, pending["tags"])
            elif pending["type"] == "move":
                move_map = task.result.get("move_map", {})
                if move_map:
                    self._push_undo_move(move_map)

        if task.task_type in (TaskType.DETECT_DUPLICATES, TaskType.RENAME, TaskType.APPLY_TAGS,
                              TaskType.MOVE, TaskType.DELETE_REJECT, TaskType.BATCH):
            self.store.photos_changed.emit()
            self.bus.log_message.emit("success", f"任务完成: {task.name}")

    def _on_task_failed(self, task: Task):
        pass

    def _on_selection_changed(self, selected: list):
        self.rename_tag_panel.set_selected_photos(selected)
        self.batch_panel.set_selected_photos(selected)
        self.lbl_count.setText(f"共 {self.store.count} 张照片 | 选中 {len(selected)} 张")

    def _on_rename_request(self, pattern: str, photos: list):
        old_states = [(p, str(p.file_path)) for p in photos]
        task = self.tm.create_task(
            TaskType.RENAME,
            f"批量重命名 ({len(photos)}张)",
            f"模式: {pattern}",
            {"pattern": pattern, "photos": photos},
            can_undo=True,
        )
        self._pending_undo[task.task_id] = {"type": "rename", "old_states": old_states}
        self.tm.enqueue_task(task)
        self.right_tabs.setCurrentIndex(1)

    def _on_tags_request(self, tags: list, photos: list):
        old_states = [(p, list(p.tags)) for p in photos]
        task = self.tm.create_task(
            TaskType.APPLY_TAGS,
            f"添加标签 ({len(photos)}张)",
            f"标签: {', '.join(tags)}",
            {"tags": tags, "photos": photos},
            can_undo=True,
        )
        self._pending_undo[task.task_id] = {"type": "tags", "old_states": old_states, "tags": tags}
        self.tm.enqueue_task(task)
        self.right_tabs.setCurrentIndex(1)

    def _on_batch_request(self, action: str, params: dict):
        type_map = {
            "move": (TaskType.MOVE, "移动文件"),
            "compress": (TaskType.COMPRESS, "压缩副本"),
            "manifest": (TaskType.GENERATE_MANIFEST, "生成交付清单"),
            "delete_reject": (TaskType.DELETE_REJECT, "删除淘汰照片"),
        }
        task_type, name = type_map.get(action, (TaskType.BATCH, action))
        count = len(params.get("photos", []))
        task = self.tm.create_task(
            task_type,
            f"{name} ({count}张)" if count else name,
            str(params.get("target_directory", params.get("output_path", ""))),
            params,
            can_undo=(action == "move"),
        )
        if action == "move":
            old_states = [(p, str(p.file_path)) for p in params.get("photos", [])]
            self._pending_undo[task.task_id] = {"type": "move", "old_states": old_states}
        self.tm.enqueue_task(task)
        self.right_tabs.setCurrentIndex(1)

    def _detect_duplicates(self):
        photos = self.store.all_photos
        if not photos:
            return
        task = self.tm.create_task(
            TaskType.DETECT_DUPLICATES,
            f"检测重复文件 ({len(photos)}张)",
            "使用感知哈希算法检测视觉重复",
            {"photos": photos, "use_perceptual": True},
        )
        self.tm.enqueue_task(task)
        self.right_tabs.setCurrentIndex(1)

    def _task_control(self, cmd: str):
        if cmd == "pause":
            self.tm.pause_current()
        elif cmd == "resume":
            self.tm.resume_current()
        elif cmd == "cancel":
            self.tm.cancel_current()
        elif cmd == "clear":
            self.tm.clear_finished()

    def _do_undo(self):
        desc = self.undo_mgr.undo()
        if desc:
            self.bus.log_message.emit("success", f"已撤销: {desc}")
            self._refresh_all()

    def _on_undo_changed(self, count: int):
        self.task_panel.set_undo_enabled(count > 0, self.undo_mgr.last_description())

    def _push_undo_status(self, old_states: list, new_status: PhotoStatus):
        def undo():
            for p, s in old_states:
                p.status = s
            self._refresh_all()
        self.undo_mgr.push(f"设置{len(old_states)}张照片为{new_status.value}", undo)

    def _push_undo_tags(self, photos: list, added_tags: list):
        old_states = [(p, list(p.tags)) for p in photos]
        def undo():
            for p, old_tags in old_states:
                p.tags = list(old_tags)
            self._refresh_all()
        self.undo_mgr.push(f"为{len(photos)}张照片添加标签: {', '.join(added_tags)}", undo)

    def _push_undo_rename(self, rename_map: dict):
        def undo():
            for old_path, new_path in list(rename_map.items()):
                from pathlib import Path
                if Path(new_path).exists():
                    Path(new_path).rename(old_path)
                    photo = self.store.get_photo(new_path)
                    if photo:
                        photo.file_path = Path(old_path)
                        photo.filename = Path(old_path).name
                        self.store._photos[old_path] = self.store._photos.pop(new_path, photo)
            self._refresh_all()
        self.undo_mgr.push(f"撤销{len(rename_map)}个文件重命名", undo)

    def _push_undo_move(self, move_map: dict):
        def undo():
            from pathlib import Path
            import shutil
            for old_path, new_path in list(move_map.items()):
                if Path(new_path).exists():
                    shutil.move(new_path, old_path)
                    photo = self.store.get_photo(new_path)
                    if photo:
                        photo.file_path = Path(old_path)
                        photo.filename = Path(old_path).name
                        self.store._photos[old_path] = self.store._photos.pop(new_path, photo)
            self._refresh_all()
        self.undo_mgr.push(f"撤销{len(move_map)}个文件移动", undo)

    def _apply_rule(self, rule: HistoryRule):
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "应用规则",
            f"确定要应用规则 '{rule.name}' 吗？\n这将按顺序执行多个批处理任务。",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        photos = self.store.all_photos
        if rule.keep_status_only:
            photos = [p for p in photos if p.status == PhotoStatus.KEEP]
        if not photos:
            QMessageBox.information(self, "提示", "没有符合条件的照片")
            return

        sub_tasks = []
        if rule.detect_duplicates:
            sub_tasks.append({
                "task_type": TaskType.DETECT_DUPLICATES,
                "name": "检测重复",
                "parameters": {"photos": self.store.all_photos, "use_perceptual": True},
            })
        if rule.tags:
            sub_tasks.append({
                "task_type": TaskType.APPLY_TAGS,
                "name": f"添加标签: {', '.join(rule.tags)}",
                "parameters": {"tags": rule.tags, "photos": photos},
            })
        if rule.rename_pattern:
            sub_tasks.append({
                "task_type": TaskType.RENAME,
                "name": "批量重命名",
                "parameters": {"pattern": rule.rename_pattern, "photos": photos},
            })
        if rule.target_directory:
            sub_tasks.append({
                "task_type": TaskType.MOVE,
                "name": f"移动到 {rule.target_directory}",
                "parameters": {"target_directory": rule.target_directory, "photos": photos},
            })
        if rule.compress_quality:
            sub_tasks.append({
                "task_type": TaskType.COMPRESS,
                "name": f"压缩副本 (质量{rule.compress_quality}%)",
                "parameters": {
                    "target_directory": str(Path(rule.target_directory) / "compressed") if rule.target_directory else str(Path.home() / "compressed"),
                    "quality": rule.compress_quality,
                    "photos": photos,
                },
            })
        if rule.generate_manifest:
            sub_tasks.append({
                "task_type": TaskType.GENERATE_MANIFEST,
                "name": "生成交付清单",
                "parameters": {
                    "output_path": str(Path(rule.target_directory or Path.home()) / "manifest.csv"),
                    "format": "csv",
                    "photos": photos,
                },
            })
        if rule.delete_rejected:
            sub_tasks.append({
                "task_type": TaskType.DELETE_REJECT,
                "name": "删除淘汰照片",
                "parameters": {"photos": self.store.all_photos},
            })

        if not sub_tasks:
            QMessageBox.information(self, "提示", "该规则未配置任何操作")
            return

        batch_task = self.tm.create_task(
            TaskType.BATCH,
            f"应用规则: {rule.name}",
            f"包含 {len(sub_tasks)} 个子任务",
            {"sub_tasks": sub_tasks},
        )
        self.tm.enqueue_task(batch_task)
        self.right_tabs.setCurrentIndex(1)

    def _capture_rule(self):
        current = {
            "rename_pattern": self.rename_tag_panel.pattern_edit.text(),
            "target_directory": self.batch_panel.target_dir_edit.text(),
            "tags": [self.rename_tag_panel.tag_list.item(i).text()
                     for i in range(self.rename_tag_panel.tag_list.count())],
        }
        self.history_panel.save_current(current)

    def _open_photo_external(self, photo: Photo):
        import subprocess
        try:
            if sys.platform == "win32":
                os.startfile(str(photo.file_path))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(photo.file_path)])
            else:
                subprocess.run(["xdg-open", str(photo.file_path)])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件: {e}")

    def _clear_workspace(self):
        if self.store.count == 0:
            return
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "确认清空",
            f"确定要清空工作区的 {self.store.count} 张照片吗？\n(不会删除磁盘上的原文件)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.store.clear()
            self.detail_panel.set_photo(None)

    def _on_log_message(self, level: str, msg: str):
        self.status_bar.showMessage(msg, 5000)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_K and not event.modifiers():
            self._bulk_status(PhotoStatus.KEEP)
        elif event.key() == Qt.Key_X and not event.modifiers():
            self._bulk_status(PhotoStatus.REJECT)
        elif event.key() == Qt.Key_U and not event.modifiers():
            self._bulk_status(PhotoStatus.UNPROCESSED)
        else:
            super().keyPressEvent(event)
