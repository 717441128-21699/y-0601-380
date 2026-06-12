import os
import sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QFrame, QListWidget, QListWidgetItem, QProgressBar, QSplitter,
                               QTextEdit, QTreeWidget, QTreeWidgetItem, QHeaderView, QMessageBox)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QAction, QBrush, QColor
from modules.task_queue import TaskManager
from core.task import Task, TaskStatus, TaskType
from utils.undo_manager import UndoManager


class TaskQueuePanel(QWidget):
    control_requested = Signal(str)
    undo_requested = Signal()
    undo_to_index = Signal(int)
    retry_task = Signal(str, bool)

    def __init__(self, task_manager: TaskManager, undo_manager: UndoManager, parent=None):
        super().__init__(parent)
        self.tm = task_manager
        self.um = undo_manager
        self._current_selected_undo_entry = None
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("📋 任务队列")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        ctrl_layout = QHBoxLayout()
        self.btn_pause = QPushButton("⏸ 暂停")
        self.btn_pause.setStyleSheet(self._btn_style("#f39c12"))
        self.btn_pause.clicked.connect(lambda: self.control_requested.emit("pause"))

        self.btn_resume = QPushButton("▶ 继续")
        self.btn_resume.setStyleSheet(self._btn_style("#27ae60"))
        self.btn_resume.clicked.connect(lambda: self.control_requested.emit("resume"))

        self.btn_cancel = QPushButton("✕ 取消")
        self.btn_cancel.setStyleSheet(self._btn_style("#e74c3c"))
        self.btn_cancel.clicked.connect(lambda: self.control_requested.emit("cancel"))

        self.btn_clear = QPushButton("🧹 清除已完成")
        self.btn_clear.setStyleSheet(self._btn_style("#6c757d"))
        self.btn_clear.clicked.connect(lambda: self.control_requested.emit("clear"))

        ctrl_layout.addWidget(self.btn_pause)
        ctrl_layout.addWidget(self.btn_resume)
        ctrl_layout.addWidget(self.btn_cancel)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_clear)
        layout.addLayout(ctrl_layout)

        splitter_main = QSplitter(Qt.Vertical)

        tasks_splitter = QSplitter(Qt.Vertical)

        list_frame = QFrame()
        list_frame.setStyleSheet("QFrame { background: #fff; border: 1px solid #e5e5e5; border-radius: 8px; }")
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(8, 8, 8, 8)

        list_header = QLabel("任务列表")
        list_header.setStyleSheet("font-weight: bold; color: #333; padding: 4px;")
        list_layout.addWidget(list_header)

        self.task_list = QListWidget()
        self.task_list.setStyleSheet("""
            QListWidget { border: none; background: transparent; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #f0f0f0; border-radius: 4px; }
            QListWidget::item:selected { background: #e8f3ff; }
        """)
        self.task_list.itemSelectionChanged.connect(self._on_selection)
        list_layout.addWidget(self.task_list)
        tasks_splitter.addWidget(list_frame)

        detail_frame = QFrame()
        detail_frame.setStyleSheet("QFrame { background: #fff; border: 1px solid #e5e5e5; border-radius: 8px; }")
        detail_layout = QVBoxLayout(detail_frame)
        detail_layout.setContentsMargins(8, 8, 8, 8)

        detail_header_layout = QHBoxLayout()
        detail_header = QLabel("任务详情")
        detail_header.setStyleSheet("font-weight: bold; color: #333; padding: 4px;")
        detail_header_layout.addWidget(detail_header)
        detail_header_layout.addStretch()

        self.btn_retry_full = QPushButton("🔄 重试全部")
        self.btn_retry_full.setStyleSheet(self._btn_style("#8e44ad"))
        self.btn_retry_full.setVisible(False)
        self.btn_retry_full.clicked.connect(self._retry_full)
        detail_header_layout.addWidget(self.btn_retry_full)

        self.btn_retry_skipped = QPushButton("⚠ 重跑跳过项")
        self.btn_retry_skipped.setStyleSheet(self._btn_style("#e67e22"))
        self.btn_retry_skipped.setVisible(False)
        self.btn_retry_skipped.clicked.connect(self._retry_skipped)
        detail_header_layout.addWidget(self.btn_retry_skipped)

        detail_layout.addLayout(detail_header_layout)

        self.lbl_task_name = QLabel("选择任务查看详情")
        self.lbl_task_name.setStyleSheet("font-weight: bold; font-size: 13px;")
        detail_layout.addWidget(self.lbl_task_name)

        self.lbl_task_status = QLabel("")
        detail_layout.addWidget(self.lbl_task_status)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { border: 1px solid #ddd; border-radius: 4px; text-align: center; height: 18px; }
            QProgressBar::chunk { background: #4A90D9; border-radius: 3px; }
        """)
        detail_layout.addWidget(self.progress)

        self.lbl_task_time = QLabel("")
        self.lbl_task_time.setStyleSheet("color: #666; font-size: 11px;")
        detail_layout.addWidget(self.lbl_task_time)

        self.lbl_task_desc = QLabel("")
        self.lbl_task_desc.setWordWrap(True)
        self.lbl_task_desc.setStyleSheet("color: #666; font-size: 11px;")
        detail_layout.addWidget(self.lbl_task_desc)

        self.delivery_frame = QFrame()
        self.delivery_frame.setStyleSheet("QFrame { background: #eaf6f0; border: 1px solid #27ae60; border-radius: 6px; }")
        delivery_layout = QVBoxLayout(self.delivery_frame)
        delivery_layout.setContentsMargins(10, 8, 10, 8)
        delivery_layout.setSpacing(4)

        delivery_title_layout = QHBoxLayout()
        self.lbl_delivery_title = QLabel("📦 交付包视图")
        self.lbl_delivery_title.setStyleSheet("font-weight: bold; color: #27ae60; font-size: 12px;")
        delivery_title_layout.addWidget(self.lbl_delivery_title)
        delivery_title_layout.addStretch()

        self.btn_open_output_dir = QPushButton("📂 打开目录")
        self.btn_open_output_dir.setStyleSheet("""
            QPushButton {
                background: #27ae60; color: white; border: none;
                padding: 4px 10px; border-radius: 4px; font-size: 11px;
            }
            QPushButton:hover { background: #219a52; }
        """)
        self.btn_open_output_dir.clicked.connect(self._open_output_directory)
        delivery_title_layout.addWidget(self.btn_open_output_dir)

        delivery_layout.addLayout(delivery_title_layout)

        self.lbl_delivery_counts = QLabel("")
        self.lbl_delivery_counts.setWordWrap(True)
        self.lbl_delivery_counts.setStyleSheet("color: #2c3e50; font-size: 11px;")
        delivery_layout.addWidget(self.lbl_delivery_counts)

        self.lbl_delivery_tags = QLabel("")
        self.lbl_delivery_tags.setWordWrap(True)
        self.lbl_delivery_tags.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        delivery_layout.addWidget(self.lbl_delivery_tags)

        self.lbl_delivery_path = QLabel("")
        self.lbl_delivery_path.setWordWrap(True)
        self.lbl_delivery_path.setStyleSheet("color: #3498db; font-size: 10px; text-decoration: underline;")
        delivery_layout.addWidget(self.lbl_delivery_path)

        self.delivery_frame.setVisible(False)
        detail_layout.addWidget(self.delivery_frame)

        self.lbl_task_summary = QLabel("")
        self.lbl_task_summary.setWordWrap(True)
        self.lbl_task_summary.setStyleSheet("color: #333; font-size: 11px; padding: 6px; background: #f8f9fa; border-radius: 4px;")
        self.lbl_task_summary.setVisible(False)
        detail_layout.addWidget(self.lbl_task_summary)

        self.result_tree = QTreeWidget()
        self.result_tree.setHeaderLabels(["项目", "详情"])
        self.result_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.result_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.result_tree.setStyleSheet("""
            QTreeWidget { border: 1px solid #e5e5e5; border-radius: 4px; font-size: 11px; }
            QTreeWidget::item { padding: 2px 0; }
        """)
        self.result_tree.setVisible(False)
        self.result_tree.setMaximumHeight(260)
        detail_layout.addWidget(self.result_tree)

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #e74c3c; background: #fef0f0; padding: 8px; border-radius: 4px; font-size: 11px;")
        self.error_label.setVisible(False)
        detail_layout.addWidget(self.error_label)

        tasks_splitter.addWidget(detail_frame)
        tasks_splitter.setStretchFactor(0, 2)
        tasks_splitter.setStretchFactor(1, 3)
        splitter_main.addWidget(tasks_splitter)

        undo_frame = QFrame()
        undo_frame.setStyleSheet("QFrame { background: #fff; border: 1px solid #e5e5e5; border-radius: 8px; }")
        undo_layout = QVBoxLayout(undo_frame)
        undo_layout.setContentsMargins(8, 8, 8, 8)

        undo_header_layout = QHBoxLayout()
        undo_header = QLabel("↩ 撤销历史 (时间线)")
        undo_header.setStyleSheet("font-weight: bold; color: #333; padding: 4px;")
        undo_header_layout.addWidget(undo_header)
        undo_header_layout.addStretch()

        self.btn_undo_last = QPushButton("撤销上一步")
        self.btn_undo_last.setStyleSheet(self._btn_style("#4A90D9"))
        self.btn_undo_last.setEnabled(False)
        self.btn_undo_last.clicked.connect(self.undo_requested.emit)
        undo_header_layout.addWidget(self.btn_undo_last)

        self.btn_undo_to = QPushButton("回滚到选中")
        self.btn_undo_to.setStyleSheet(self._btn_style("#f39c12"))
        self.btn_undo_to.setEnabled(False)
        self.btn_undo_to.clicked.connect(self._undo_to_selected)
        undo_header_layout.addWidget(self.btn_undo_to)

        undo_layout.addLayout(undo_header_layout)

        undo_splitter = QSplitter(Qt.Horizontal)

        self.undo_list = QListWidget()
        self.undo_list.setStyleSheet("""
            QListWidget { border: 1px solid #e5e5e5; border-radius: 4px; background: #fafafa; }
            QListWidget::item { padding: 6px 8px; border-bottom: 1px solid #f0f0f0; }
            QListWidget::item:selected { background: #4A90D9; color: white; }
        """)
        self.undo_list.itemSelectionChanged.connect(self._on_undo_selection)
        undo_splitter.addWidget(self.undo_list)

        self.undo_detail_frame = QFrame()
        self.undo_detail_frame.setStyleSheet("QFrame { background: #f8f9fa; border: 1px solid #e5e5e5; border-radius: 4px; }")
        undo_detail_layout = QVBoxLayout(self.undo_detail_frame)
        undo_detail_layout.setContentsMargins(8, 8, 8, 8)
        undo_detail_layout.setSpacing(4)

        self.lbl_undo_detail_title = QLabel("点击左侧条目查看详情")
        self.lbl_undo_detail_title.setStyleSheet("font-weight: bold; color: #555; font-size: 11px;")
        undo_detail_layout.addWidget(self.lbl_undo_detail_title)

        self.undo_detail_tree = QTreeWidget()
        self.undo_detail_tree.setHeaderLabels(["变更项", "变更前 → 变更后"])
        self.undo_detail_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.undo_detail_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.undo_detail_tree.setStyleSheet("""
            QTreeWidget { border: none; background: transparent; font-size: 10px; }
            QTreeWidget::item { padding: 1px 0; }
        """)
        undo_detail_layout.addWidget(self.undo_detail_tree, 1)

        undo_splitter.addWidget(self.undo_detail_frame)
        undo_splitter.setStretchFactor(0, 1)
        undo_splitter.setStretchFactor(1, 1)
        undo_splitter.setSizes([160, 160])
        undo_layout.addWidget(undo_splitter, 1)

        splitter_main.addWidget(undo_frame)
        splitter_main.setStretchFactor(0, 3)
        splitter_main.setStretchFactor(1, 1)
        layout.addWidget(splitter_main, 1)

        log_frame = QFrame()
        log_frame.setStyleSheet("QFrame { background: #1e1e1e; border-radius: 8px; }")
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(8, 8, 8, 8)
        log_header = QLabel("📜 操作日志")
        log_header.setStyleSheet("color: #ddd; font-weight: bold; padding: 4px;")
        log_layout.addWidget(log_header)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit { background: #1e1e1e; color: #d4d4d4; border: none; font-family: Consolas, monospace; font-size: 11px; }
        """)
        log_layout.addWidget(self.log_text)
        log_frame.setFixedHeight(130)
        layout.addWidget(log_frame)

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

    def _connect_signals(self):
        self.tm.task_added.connect(self._on_task_added)
        self.tm.task_updated.connect(self._on_task_updated)
        self.um.history_changed.connect(self._refresh_undo_history)

    def _on_task_added(self, task: Task):
        self._refresh_list()

    def _on_task_updated(self, task: Task):
        self._refresh_list()
        current = self.task_list.currentItem()
        if current and current.data(Qt.UserRole) == task.task_id:
            self._show_detail(task)

    def _refresh_list(self):
        self.task_list.blockSignals(True)
        current_id = None
        cur = self.task_list.currentItem()
        if cur:
            current_id = cur.data(Qt.UserRole)
        self.task_list.clear()

        status_icons = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.RUNNING: "🔄",
            TaskStatus.PAUSED: "⏸",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.CANCELLED: "🚫",
        }

        for task in self.tm.all_tasks:
            item = QListWidgetItem()
            icon = status_icons.get(task.status, "❓")
            prog = ""
            if task.total > 0:
                prog = f" [{task.progress}/{task.total}]"
            item.setText(f"{icon} {task.name}{prog}")
            item.setData(Qt.UserRole, task.task_id)
            color_map = {
                TaskStatus.COMPLETED: "#27ae60",
                TaskStatus.FAILED: "#e74c3c",
                TaskStatus.RUNNING: "#4A90D9",
                TaskStatus.PAUSED: "#f39c12",
                TaskStatus.PENDING: "#6c757d",
                TaskStatus.CANCELLED: "#95a5a6",
            }
            item.setForeground(QBrush(QColor(color_map.get(task.status, "#333"))))
            self.task_list.addItem(item)
            if task.task_id == current_id:
                self.task_list.setCurrentItem(item)

        self.task_list.blockSignals(False)
        if cur is None and self.task_list.count() > 0:
            self.task_list.setCurrentRow(0)

    def _on_selection(self):
        item = self.task_list.currentItem()
        if not item:
            return
        task_id = item.data(Qt.UserRole)
        task = self.tm.get_task(task_id)
        if task:
            self._show_detail(task)

    def _show_detail(self, task: Task):
        self.lbl_task_name.setText(task.name)
        self.lbl_task_status.setText(f"状态: {task.status.value} | 类型: {task.task_type.value}")

        if task.total > 0:
            self.progress.setVisible(True)
            self.progress.setRange(0, task.total)
            self.progress.setValue(task.progress)
            self.progress.setFormat(f"{task.progress}/{task.total} (%p%)")
        else:
            self.progress.setVisible(False)

        time_info = f"创建: {task.created_at.strftime('%H:%M:%S')}"
        if task.started_at:
            time_info += f" | 开始: {task.started_at.strftime('%H:%M:%S')}"
        if task.completed_at:
            time_info += f" | 完成: {task.completed_at.strftime('%H:%M:%S')}"
        self.lbl_task_time.setText(time_info)
        self.lbl_task_desc.setText(task.description if task.description else "(无描述)")

        self._render_delivery_view(task)
        self._render_retry_buttons(task)
        self._render_result_summary(task)
        self._render_result_tree(task)

        if task.error_message:
            self.error_label.setVisible(True)
            self.error_label.setText(f"❌ 失败原因:\n{task.error_message}")
        else:
            self.error_label.setVisible(False)

    def _render_delivery_view(self, task: Task):
        result = task.result
        if task.task_type != TaskType.GENERATE_MANIFEST or not result or not isinstance(result, dict):
            self.delivery_frame.setVisible(False)
            return

        manifest_path = result.get("manifest_path", "")
        output_dir = result.get("output_directory", "")
        status_counts = result.get("status_counts", {})
        tag_summary = result.get("tag_summary", {})
        total = result.get("total", 0)
        count = result.get("count", 0)

        if not manifest_path and task.status == TaskStatus.CANCELLED:
            self.delivery_frame.setVisible(False)
            return

        self.delivery_frame.setVisible(True)

        counts_parts = [f"📊 照片总数: {total} (已列入清单 {count})"]
        for status_name, status_count in status_counts.items():
            status_emoji = {"保留": "✓", "淘汰": "✗", "未处理": "○", "重复": "⚠"}
            emoji = status_emoji.get(status_name, "")
            counts_parts.append(f"{emoji} {status_name}: {status_count}")
        self.lbl_delivery_counts.setText("　".join(counts_parts))

        if tag_summary:
            sorted_tags = sorted(tag_summary.items(), key=lambda x: -x[1])
            tag_strs = [f"🏷 {tag}×{cnt}" for tag, cnt in sorted_tags[:10]]
            if len(sorted_tags) > 10:
                tag_strs.append(f"... 共{len(sorted_tags)}种标签")
            self.lbl_delivery_tags.setText("　".join(tag_strs))
        else:
            self.lbl_delivery_tags.setText("🏷 无标签")

        if manifest_path:
            self.lbl_delivery_path.setText(f"📄 清单文件: {manifest_path}")
            self.lbl_delivery_path.setVisible(True)
        else:
            self.lbl_delivery_path.setText("🚫 清单未生成 (任务已取消)")
            self.lbl_delivery_path.setVisible(True)

        self.btn_open_output_dir.setEnabled(bool(output_dir))
        self._current_output_dir = output_dir
        self._current_manifest_path = manifest_path

    def _render_retry_buttons(self, task: Task):
        can_retry = task.status in (TaskStatus.FAILED, TaskStatus.CANCELLED)
        can_retry_skipped = can_retry and task.task_type in (
            TaskType.RENAME, TaskType.MOVE, TaskType.COMPRESS, TaskType.GENERATE_MANIFEST
        )
        self.btn_retry_full.setVisible(can_retry)
        self.btn_retry_skipped.setVisible(can_retry_skipped)
        self._current_task_id = task.task_id

    def _retry_full(self):
        if hasattr(self, "_current_task_id"):
            reply = QMessageBox.question(
                self, "重试任务",
                "确定要完整重试这个任务吗？\n已完成的项目也会重新处理。",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.retry_task.emit(self._current_task_id, False)

    def _retry_skipped(self):
        if hasattr(self, "_current_task_id"):
            reply = QMessageBox.question(
                self, "重跑跳过项",
                "只重新处理跳过和取消的项目？\n已成功完成的部分不会重复处理。",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.retry_task.emit(self._current_task_id, True)

    def _open_output_directory(self):
        import subprocess
        path = getattr(self, "_current_output_dir", "")
        if not path:
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开目录: {e}")

    def _render_result_summary(self, task: Task):
        result = task.result
        if not result or not isinstance(result, dict):
            self.lbl_task_summary.setVisible(False)
            return
        parts = []
        if "total" in result:
            parts.append(f"总计: {result['total']}")
        if "completed" in result and isinstance(result["completed"], list):
            parts.append(f"✓ 成功: {len(result['completed'])}")
        if "skipped" in result and isinstance(result["skipped"], list):
            parts.append(f"⏭ 跳过: {len(result['skipped'])}")
        if result.get("cancelled"):
            parts.append("🚫 已取消")
        if "count" in result and "completed" not in result:
            parts.append(f"处理: {result['count']}")
        if "total_duplicates" in result:
            parts.append(f"重复文件: {result['total_duplicates']}")
        if parts:
            self.lbl_task_summary.setText(" | ".join(parts))
            self.lbl_task_summary.setVisible(True)
        else:
            self.lbl_task_summary.setVisible(False)

    def _render_result_tree(self, task: Task):
        self.result_tree.clear()
        result = task.result
        if not result or not isinstance(result, dict):
            self.result_tree.setVisible(False)
            return

        has_content = False

        if task.task_type == TaskType.RENAME and result.get("completed"):
            has_content = True
            completed_item = QTreeWidgetItem(self.result_tree, [f"✅ 已重命名 ({len(result['completed'])})", ""])
            for item_data in result["completed"]:
                QTreeWidgetItem(completed_item, [item_data.get("old", ""), f"→ {item_data.get('new', '')}"])
        elif task.task_type == TaskType.MOVE and result.get("completed"):
            has_content = True
            completed_item = QTreeWidgetItem(self.result_tree, [f"✅ 已移动 ({len(result['completed'])})", ""])
            for item_data in result["completed"]:
                QTreeWidgetItem(completed_item, [item_data.get("filename", ""), f"{item_data.get('from', '')} → {item_data.get('to', '')}"])
        elif task.task_type == TaskType.APPLY_TAGS and result.get("completed"):
            has_content = True
            completed_item = QTreeWidgetItem(self.result_tree, [f"✅ 已打标签 ({len(result['completed'])})", f"标签: {', '.join(result.get('applied_tags', []))}"])
            for item_data in result["completed"]:
                old = ", ".join(item_data.get("old_tags", [])) or "(无)"
                new = ", ".join(item_data.get("new_tags", [])) or "(无)"
                QTreeWidgetItem(completed_item, [item_data.get("filename", ""), f"{old}  →  {new}"])
        elif task.task_type == TaskType.DETECT_DUPLICATES and result.get("groups_detail"):
            has_content = True
            for group in result["groups_detail"]:
                g_item = QTreeWidgetItem(self.result_tree, [f"分组#{group['group']} ({group['count']}张)", f"保留: {group['keep']}"])
                for dup in group.get("duplicates", []):
                    QTreeWidgetItem(g_item, [f"🚫 {dup}", "标记为重复"])
        elif task.task_type == TaskType.COMPRESS and result.get("completed"):
            has_content = True
            completed_item = QTreeWidgetItem(self.result_tree, [f"✅ 已压缩 ({len(result['completed'])})", ""])
            for item_data in result["completed"]:
                QTreeWidgetItem(completed_item, [item_data.get("filename", ""), f"输出: {item_data.get('output', '')}"])
        elif task.task_type == TaskType.DELETE_REJECT and result.get("deleted"):
            has_content = True
            deleted_item = QTreeWidgetItem(self.result_tree, [f"🗑 已删除 ({len(result['deleted'])})", "移至回收站"])
            for item_data in result["deleted"]:
                QTreeWidgetItem(deleted_item, [item_data.get("filename", ""), item_data.get("path", "")])
        elif task.task_type == TaskType.GENERATE_MANIFEST:
            has_content = True
            if result.get("cancelled") and not result.get("manifest_path"):
                info_item = QTreeWidgetItem(self.result_tree, ["🚫 清单未生成", "任务已取消，无最终文件"])
            else:
                info_item = QTreeWidgetItem(self.result_tree, ["📄 交付清单", result.get("manifest_path", "") or "(未生成)"])
            if result.get("completed"):
                files_item = QTreeWidgetItem(info_item, [f"已列入清单 ({len(result['completed'])})", ""])
                for fname in result["completed"][:50]:
                    QTreeWidgetItem(files_item, [fname, "✓ 已处理"])
                if len(result["completed"]) > 50:
                    QTreeWidgetItem(files_item, [f"... 还有 {len(result['completed']) - 50} 个", ""])
        elif task.task_type == TaskType.BATCH and result.get("sub_results"):
            has_content = True
            for name, sub_result in result["sub_results"]:
                name_map = {"rename": "重命名", "move": "移动", "compress": "压缩",
                            "manifest": "清单", "tags": "打标签", "delete": "删除", "dedup": "检测重复"}
                count = len(sub_result.get("completed", [])) if isinstance(sub_result.get("completed"), list) else sub_result.get("count", 0)
                QTreeWidgetItem(self.result_tree, [name_map.get(name, name), f"{count} 项"])

        if result.get("skipped") and isinstance(result["skipped"], list) and len(result["skipped"]) > 0:
            has_content = True
            skipped_item = QTreeWidgetItem(self.result_tree, [f"⏭ 跳过/取消 ({len(result['skipped'])})", ""])
            for s in result["skipped"][:30]:
                QTreeWidgetItem(skipped_item, [str(s), ""])
            if len(result["skipped"]) > 30:
                QTreeWidgetItem(skipped_item, [f"... 还有 {len(result['skipped']) - 30} 项", ""])

        self.result_tree.setVisible(has_content)
        if has_content:
            self.result_tree.expandToDepth(0)

    def _on_undo_selection(self):
        row = self.undo_list.currentRow()
        if row < 0:
            self.lbl_undo_detail_title.setText("点击左侧条目查看详情")
            self.undo_detail_tree.clear()
            return

        history = self.um.history
        if row >= len(history):
            return

        entry = history[row]
        self._current_selected_undo_entry = entry
        self.lbl_undo_detail_title.setText(f"⏪ {entry.timestamp.strftime('%H:%M:%S')}  {entry.description}")

        self.undo_detail_tree.clear()
        extra = getattr(entry, "extra_data", None)
        if extra and isinstance(extra, dict):
            changes = extra.get("changes", [])
            for change in changes:
                if isinstance(change, dict):
                    name = change.get("name", "")
                    before = str(change.get("before", ""))
                    after = str(change.get("after", ""))
                    QTreeWidgetItem(self.undo_detail_tree, [name, f"{before}  →  {after}"])
                else:
                    QTreeWidgetItem(self.undo_detail_tree, [str(change), ""])
            if not changes:
                count = entry.affected_count or "(未知)"
                QTreeWidgetItem(self.undo_detail_tree, [f"共影响 {count} 项", "点击上方按钮可执行回滚"])
        else:
            count = entry.affected_count or "(未知)"
            QTreeWidgetItem(self.undo_detail_tree, [f"共影响 {count} 项", "点击上方按钮可执行回滚"])
        self.undo_detail_tree.expandAll()

    def _refresh_undo_history(self):
        self.undo_list.clear()
        for entry in self.um.history:
            item = QListWidgetItem()
            time_str = entry.timestamp.strftime("%H:%M:%S")
            count_str = f" (影响{entry.affected_count}项)" if entry.affected_count else ""
            item.setText(f"⏪ {time_str}  {entry.description}{count_str}")
            item.setData(Qt.UserRole, entry.entry_id)
            self.undo_list.addItem(item)
        self.btn_undo_last.setEnabled(self.um.can_undo())
        self.btn_undo_to.setEnabled(self.um.can_undo())
        self._on_undo_selection()

    def _undo_to_selected(self):
        row = self.undo_list.currentRow()
        if row >= 0:
            self.undo_to_index.emit(row)

    def set_undo_enabled(self, enabled: bool, description: str = ""):
        self.btn_undo_last.setEnabled(enabled)

    def append_log(self, level: str, message: str):
        color_map = {
            "info": "#d4d4d4",
            "success": "#4ec9b0",
            "warning": "#dcdcaa",
            "error": "#f48771",
        }
        color = color_map.get(level, "#d4d4d4")
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        html = f'<span style="color:#808080">[{ts}]</span> <span style="color:{color}">{message}</span>'
        self.log_text.append(html)
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())
