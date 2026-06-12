from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QFrame, QListWidget, QListWidgetItem, QProgressBar, QSplitter,
                               QTextEdit, QMenu)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QAction
from modules.task_queue import TaskManager
from core.task import Task, TaskStatus, TaskType


class TaskQueuePanel(QWidget):
    control_requested = Signal(str)
    undo_requested = Signal()

    def __init__(self, task_manager: TaskManager, parent=None):
        super().__init__(parent)
        self.tm = task_manager
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

        undo_layout = QHBoxLayout()
        self.btn_undo = QPushButton("↩ 撤销上一步")
        self.btn_undo.setStyleSheet(self._btn_style("#4A90D9"))
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self.undo_requested.emit)
        undo_layout.addWidget(self.btn_undo)
        undo_layout.addStretch()
        self.lbl_undo_desc = QLabel("")
        self.lbl_undo_desc.setStyleSheet("color: #888; font-size: 11px; font-style: italic;")
        undo_layout.addWidget(self.lbl_undo_desc)
        layout.addLayout(undo_layout)

        splitter = QSplitter(Qt.Vertical)

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
        splitter.addWidget(list_frame)

        detail_frame = QFrame()
        detail_frame.setStyleSheet("QFrame { background: #fff; border: 1px solid #e5e5e5; border-radius: 8px; }")
        detail_layout = QVBoxLayout(detail_frame)
        detail_layout.setContentsMargins(8, 8, 8, 8)

        detail_header = QLabel("任务详情")
        detail_header.setStyleSheet("font-weight: bold; color: #333; padding: 4px;")
        detail_layout.addWidget(detail_header)

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

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #e74c3c; background: #fef0f0; padding: 8px; border-radius: 4px; font-size: 11px;")
        self.error_label.setVisible(False)
        detail_layout.addWidget(self.error_label)

        detail_layout.addStretch()
        splitter.addWidget(detail_frame)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

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
        log_frame.setFixedHeight(150)
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
            from PySide6.QtGui import QBrush, QColor
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

        if task.error_message:
            self.error_label.setVisible(True)
            self.error_label.setText(f"❌ 失败原因:\n{task.error_message}")
        else:
            self.error_label.setVisible(False)

    def set_undo_enabled(self, enabled: bool, description: str = ""):
        self.btn_undo.setEnabled(enabled)
        if enabled and description:
            self.lbl_undo_desc.setText(f"撤销: {description}")
        else:
            self.lbl_undo_desc.setText("")

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
