from collections import deque
from typing import Callable, Optional, List
from datetime import datetime
from PySide6.QtCore import QObject, Signal


class UndoEntry:
    def __init__(self, entry_id: str, description: str, undo_action: Callable,
                 affected_count: int = 0, timestamp: datetime = None, extra_data: dict = None):
        self.entry_id = entry_id
        self.description = description
        self.undo_action = undo_action
        self.affected_count = affected_count
        self.timestamp = timestamp or datetime.now()
        self.applied = True
        self.extra_data = extra_data or {}


class UndoManager(QObject):
    stack_changed = Signal(int)
    history_changed = Signal()

    def __init__(self, max_size: int = 50):
        super().__init__()
        self._undo_stack: deque = deque(maxlen=max_size)
        self._entry_counter = 0

    def push(self, description: str, undo_action: Callable, affected_count: int = 0, extra_data: dict = None) -> str:
        self._entry_counter += 1
        entry = UndoEntry(
            entry_id=f"undo_{self._entry_counter}",
            description=description,
            undo_action=undo_action,
            affected_count=affected_count,
            extra_data=extra_data,
        )
        self._undo_stack.append(entry)
        self.stack_changed.emit(len(self._undo_stack))
        self.history_changed.emit()
        return entry.entry_id

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def history(self) -> List[UndoEntry]:
        return list(reversed(self._undo_stack))

    def undo(self) -> Optional[str]:
        if not self.can_undo():
            return None
        entry = self._undo_stack.pop()
        try:
            entry.undo_action()
        except Exception:
            pass
        self.stack_changed.emit(len(self._undo_stack))
        self.history_changed.emit()
        return entry.description

    def undo_until(self, entry_id: str) -> int:
        count = 0
        while self.can_undo():
            entry = self._undo_stack[-1]
            if entry.entry_id == entry_id:
                break
            self._undo_stack.pop()
            try:
                entry.undo_action()
            except Exception:
                pass
            count += 1
        self.stack_changed.emit(len(self._undo_stack))
        self.history_changed.emit()
        return count

    def undo_to_index(self, index: int) -> int:
        count = 0
        target = len(self._undo_stack) - 1 - index
        while len(self._undo_stack) > target and self.can_undo():
            entry = self._undo_stack.pop()
            try:
                entry.undo_action()
            except Exception:
                pass
            count += 1
        self.stack_changed.emit(len(self._undo_stack))
        self.history_changed.emit()
        return count

    def last_description(self) -> Optional[str]:
        if not self.can_undo():
            return None
        return self._undo_stack[-1].description

    def clear(self):
        self._undo_stack.clear()
        self.stack_changed.emit(0)
        self.history_changed.emit()

    @property
    def count(self) -> int:
        return len(self._undo_stack)
