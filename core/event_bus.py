from PySide6.QtCore import QObject, Signal
from typing import List, Optional
from core.photo import Photo
from core.task import Task
from core.history_rule import HistoryRule


class EventBus(QObject):
    photos_imported = Signal(list)
    photos_updated = Signal(list)
    photo_status_changed = Signal(object, object)
    photo_tags_changed = Signal(object, list)

    task_added = Signal(object)
    task_updated = Signal(object)
    task_completed = Signal(object)
    task_failed = Signal(object)
    all_tasks_cleared = Signal()

    rule_saved = Signal(object)
    rule_applied = Signal(object)
    rule_deleted = Signal(str)

    log_message = Signal(str, str)

    _instance = None

    @classmethod
    def instance(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = EventBus()
        return cls._instance
