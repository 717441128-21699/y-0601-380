from collections import deque
from typing import Callable, Optional
from PySide6.QtCore import QObject, Signal


class UndoManager(QObject):
    stack_changed = Signal(int)

    def __init__(self, max_size: int = 50):
        super().__init__()
        self._undo_stack: deque = deque(maxlen=max_size)

    def push(self, description: str, undo_action: Callable, redo_action: Optional[Callable] = None):
        self._undo_stack.append({
            "description": description,
            "undo": undo_action,
            "redo": redo_action,
        })
        self.stack_changed.emit(len(self._undo_stack))

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def undo(self) -> Optional[str]:
        if not self.can_undo():
            return None
        item = self._undo_stack.pop()
        try:
            item["undo"]()
        except Exception:
            pass
        self.stack_changed.emit(len(self._undo_stack))
        return item["description"]

    def last_description(self) -> Optional[str]:
        if not self.can_undo():
            return None
        return self._undo_stack[-1]["description"]

    def clear(self):
        self._undo_stack.clear()
        self.stack_changed.emit(0)

    @property
    def count(self) -> int:
        return len(self._undo_stack)
