from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Optional, List, Any
from datetime import datetime


class TaskStatus(Enum):
    PENDING = "等待中"
    RUNNING = "执行中"
    PAUSED = "已暂停"
    COMPLETED = "已完成"
    FAILED = "失败"
    CANCELLED = "已取消"


class TaskType(Enum):
    RENAME = "重命名"
    MOVE = "移动文件"
    DELETE_REJECT = "删除淘汰"
    COMPRESS = "压缩副本"
    GENERATE_MANIFEST = "生成交付清单"
    DETECT_DUPLICATES = "检测重复"
    APPLY_TAGS = "应用标签"
    BATCH = "批处理"


@dataclass
class Task:
    task_id: str
    task_type: TaskType
    name: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    total: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    target_photos: List[str] = field(default_factory=list)
    parameters: dict = field(default_factory=dict)
    result: Any = None
    can_undo: bool = False
    undo_action: Optional[Callable] = None

    @property
    def is_active(self) -> bool:
        return self.status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.PAUSED)

    @property
    def is_finished(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
