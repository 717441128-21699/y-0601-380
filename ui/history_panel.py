from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QFrame, QListWidget, QListWidgetItem, QInputDialog, QMessageBox,
                               QCheckBox, QSpinBox, QLineEdit, QFormLayout, QDialog, QDialogButtonBox)
from PySide6.QtCore import Qt, Signal
from utils.storage import RuleManager
from core.history_rule import HistoryRule
import uuid


class SaveRuleDialog(QDialog):
    def __init__(self, parent=None, initial: HistoryRule = None):
        super().__init__(parent)
        self.setWindowTitle("保存整理规则")
        self.setMinimumWidth(420)
        self.rule = None
        self._initial = initial
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: 客户A精修图交付流程")
        form.addRow("规则名称:", self.name_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("可选描述")
        form.addRow("描述:", self.desc_edit)

        self.pattern_edit = QLineEdit()
        self.pattern_edit.setPlaceholderText("例如: Project_{date}_{index:03d}{ext}")
        form.addRow("命名模板:", self.pattern_edit)

        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("例如: D:/交付/保留")
        form.addRow("目标目录:", self.target_edit)

        self.compress_spin = QSpinBox()
        self.compress_spin.setRange(10, 100)
        self.compress_spin.setValue(80)
        self.compress_spin.setSuffix(" %")
        form.addRow("压缩质量:", self.compress_spin)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("用逗号分隔多个标签")
        form.addRow("默认标签:", self.tags_edit)

        self.chk_keep = QCheckBox("仅处理已标记保留的照片")
        self.chk_keep.setChecked(True)
        form.addRow("", self.chk_keep)

        self.chk_del = QCheckBox("删除已淘汰照片")
        form.addRow("", self.chk_del)

        self.chk_dup = QCheckBox("检测重复文件")
        form.addRow("", self.chk_dup)

        self.chk_manifest = QCheckBox("生成交付清单")
        form.addRow("", self.chk_manifest)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        if self._initial:
            self.name_edit.setText(self._initial.name)
            self.desc_edit.setText(self._initial.description)
            self.pattern_edit.setText(self._initial.rename_pattern or "")
            self.target_edit.setText(self._initial.target_directory or "")
            if self._initial.compress_quality:
                self.compress_spin.setValue(self._initial.compress_quality)
            self.tags_edit.setText(", ".join(self._initial.tags))
            self.chk_keep.setChecked(self._initial.keep_status_only)
            self.chk_del.setChecked(self._initial.delete_rejected)
            self.chk_dup.setChecked(self._initial.detect_duplicates)
            self.chk_manifest.setChecked(self._initial.generate_manifest)

    def _on_accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入规则名称")
            return
        tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        self.rule = HistoryRule(
            rule_id=self._initial.rule_id if self._initial else str(uuid.uuid4()),
            name=name,
            description=self.desc_edit.text().strip(),
            rename_pattern=self.pattern_edit.text().strip() or None,
            target_directory=self.target_edit.text().strip() or None,
            compress_quality=self.compress_spin.value(),
            tags=tags,
            keep_status_only=self.chk_keep.isChecked(),
            delete_rejected=self.chk_del.isChecked(),
            detect_duplicates=self.chk_dup.isChecked(),
            generate_manifest=self.chk_manifest.isChecked(),
        )
        self.accept()


class HistoryPanel(QWidget):
    rule_applied = Signal(object)
    capture_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rm = RuleManager()
        self._init_ui()
        self._refresh_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("📚 历史与规则")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        desc = QLabel("保存常用的整理流程，一键复用。")
        desc.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(desc)

        btn_layout = QHBoxLayout()
        self.btn_capture = QPushButton("💾 保存当前设置为规则")
        self.btn_capture.setStyleSheet(self._btn_style("#4A90D9"))
        self.btn_capture.clicked.connect(self.capture_requested.emit)

        self.btn_new = QPushButton("➕ 新建规则")
        self.btn_new.setStyleSheet(self._btn_style("#27ae60"))
        self.btn_new.clicked.connect(self._new_rule)
        btn_layout.addWidget(self.btn_capture)
        btn_layout.addWidget(self.btn_new)
        layout.addLayout(btn_layout)

        list_frame = QFrame()
        list_frame.setStyleSheet("QFrame { background: #fff; border: 1px solid #e5e5e5; border-radius: 8px; }")
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(8, 8, 8, 8)

        list_header = QLabel("常用规则 (最近使用在前)")
        list_header.setStyleSheet("font-weight: bold; color: #333; padding: 4px;")
        list_layout.addWidget(list_header)

        self.rule_list = QListWidget()
        self.rule_list.setStyleSheet("""
            QListWidget { border: none; background: transparent; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #f0f0f0; border-radius: 4px; }
            QListWidget::item:selected { background: #e8f3ff; }
            QListWidget::item:hover { background: #f5faff; }
        """)
        self.rule_list.itemDoubleClicked.connect(self._on_double_click)
        list_layout.addWidget(self.rule_list)

        action_layout = QHBoxLayout()
        self.btn_apply = QPushButton("▶ 应用规则")
        self.btn_apply.setStyleSheet(self._btn_style("#27ae60"))
        self.btn_apply.clicked.connect(self._apply_selected)

        self.btn_edit = QPushButton("✏ 编辑")
        self.btn_edit.setStyleSheet(self._btn_style("#6c757d"))
        self.btn_edit.clicked.connect(self._edit_selected)

        self.btn_delete = QPushButton("🗑 删除")
        self.btn_delete.setStyleSheet(self._btn_style("#e74c3c"))
        self.btn_delete.clicked.connect(self._delete_selected)

        action_layout.addWidget(self.btn_apply)
        action_layout.addWidget(self.btn_edit)
        action_layout.addWidget(self.btn_delete)
        list_layout.addLayout(action_layout)

        layout.addWidget(list_frame, 1)

        detail_frame = QFrame()
        detail_frame.setStyleSheet("QFrame { background: #f8f9fa; border-radius: 8px; padding: 12px; }")
        detail_layout = QVBoxLayout(detail_frame)
        self.lbl_detail_title = QLabel("选择规则查看详情")
        self.lbl_detail_title.setStyleSheet("font-weight: bold; color: #333;")
        detail_layout.addWidget(self.lbl_detail_title)
        self.lbl_detail_body = QLabel("")
        self.lbl_detail_body.setWordWrap(True)
        self.lbl_detail_body.setStyleSheet("color: #555; font-size: 11px;")
        detail_layout.addWidget(self.lbl_detail_body)
        detail_frame.setMaximumHeight(160)
        layout.addWidget(detail_frame)

        self.rule_list.currentItemChanged.connect(self._on_selection)

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
        """

    def _refresh_list(self):
        self.rule_list.blockSignals(True)
        self.rule_list.clear()
        for rule in self.rm.get_recent(50):
            item = QListWidgetItem()
            used = f" (已用{rule.use_count}次)" if rule.use_count > 0 else ""
            date_str = rule.last_used.strftime("%m-%d") if rule.last_used else rule.created_at.strftime("%m-%d")
            item.setText(f"📌 {rule.name}{used}\n   {date_str}  |  {rule.description or '无描述'}")
            item.setData(Qt.UserRole, rule.rule_id)
            self.rule_list.addItem(item)
        self.rule_list.blockSignals(False)

    def _get_selected_rule(self) -> HistoryRule:
        item = self.rule_list.currentItem()
        if not item:
            return None
        rule_id = item.data(Qt.UserRole)
        for r in self.rm.get_all():
            if r.rule_id == rule_id:
                return r
        return None

    def _on_selection(self):
        rule = self._get_selected_rule()
        if not rule:
            self.lbl_detail_title.setText("选择规则查看详情")
            self.lbl_detail_body.setText("")
            return
        self.lbl_detail_title.setText(rule.name)
        lines = []
        if rule.description:
            lines.append(f"描述: {rule.description}")
        if rule.rename_pattern:
            lines.append(f"命名: {rule.rename_pattern}")
        if rule.target_directory:
            lines.append(f"目录: {rule.target_directory}")
        if rule.tags:
            lines.append(f"标签: {', '.join(rule.tags)}")
        options = []
        if rule.keep_status_only:
            options.append("仅保留")
        if rule.delete_rejected:
            options.append("删淘汰")
        if rule.detect_duplicates:
            options.append("去重")
        if rule.generate_manifest:
            options.append("清单")
        if options:
            lines.append("选项: " + " | ".join(options))
        lines.append(f"使用次数: {rule.use_count}")
        self.lbl_detail_body.setText("\n".join(lines))

    def _on_double_click(self):
        self._apply_selected()

    def _apply_selected(self):
        rule = self._get_selected_rule()
        if rule:
            self.rm.mark_used(rule.rule_id)
            self.rule_applied.emit(rule)
            self._refresh_list()

    def _new_rule(self):
        dlg = SaveRuleDialog(self)
        if dlg.exec() == QDialog.Accepted and dlg.rule:
            self.rm.save_rule(dlg.rule)
            self._refresh_list()

    def _edit_selected(self):
        rule = self._get_selected_rule()
        if not rule:
            return
        dlg = SaveRuleDialog(self, initial=rule)
        if dlg.exec() == QDialog.Accepted and dlg.rule:
            self.rm.update_rule(dlg.rule)
            self._refresh_list()

    def _delete_selected(self):
        rule = self._get_selected_rule()
        if not rule:
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除规则 '{rule.name}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.rm.delete_rule(rule.rule_id)
            self._refresh_list()

    def save_current(self, current_settings: dict):
        dlg = SaveRuleDialog(self)
        if current_settings.get("rename_pattern"):
            dlg.pattern_edit.setText(current_settings["rename_pattern"])
        if current_settings.get("target_directory"):
            dlg.target_edit.setText(current_settings["target_directory"])
        if current_settings.get("tags"):
            dlg.tags_edit.setText(", ".join(current_settings["tags"]))
        if dlg.exec() == QDialog.Accepted and dlg.rule:
            self.rm.save_rule(dlg.rule)
            self._refresh_list()
