import uuid
import shutil
import csv
import json
from pathlib import Path
from typing import List, Optional, Callable
from datetime import datetime
from PySide6.QtCore import QThread, Signal, QObject, QMutex, QMutexLocker
from PIL import Image
from send2trash import send2trash
from core.photo import Photo, PhotoStatus
from core.task import Task, TaskStatus, TaskType
from utils import image_utils
from utils.undo_manager import UndoManager
from core.event_bus import EventBus


class TaskWorker(QThread):
    task_progress = Signal(str, int, int)
    task_completed = Signal(str, object)
    task_failed = Signal(str, str)
    task_cancelled = Signal(str)
    log = Signal(str, str)

    def __init__(self, task: Task):
        super().__init__()
        self.task = task
        self._paused = False
        self._cancelled = False
        self._mutex = QMutex()

    def pause(self):
        with QMutexLocker(self._mutex):
            self._paused = True

    def resume(self):
        with QMutexLocker(self._mutex):
            self._paused = False

    def cancel(self):
        with QMutexLocker(self._mutex):
            self._cancelled = True

    def _check_pause(self):
        while True:
            with QMutexLocker(self._mutex):
                if self._cancelled:
                    return False
                if not self._paused:
                    return True
            self.msleep(100)

    def run(self):
        try:
            self.task.status = TaskStatus.RUNNING
            self.task.started_at = datetime.now()
            result = None
            if self.task.task_type == TaskType.RENAME:
                result = self._do_rename()
            elif self.task.task_type == TaskType.MOVE:
                result = self._do_move()
            elif self.task.task_type == TaskType.DELETE_REJECT:
                result = self._do_delete_reject()
            elif self.task.task_type == TaskType.COMPRESS:
                result = self._do_compress()
            elif self.task.task_type == TaskType.GENERATE_MANIFEST:
                result = self._do_generate_manifest()
            elif self.task.task_type == TaskType.DETECT_DUPLICATES:
                result = self._do_detect_duplicates()
            elif self.task.task_type == TaskType.APPLY_TAGS:
                result = self._do_apply_tags()
            elif self.task.task_type == TaskType.BATCH:
                result = self._do_batch()

            was_cancelled = False
            with QMutexLocker(self._mutex):
                was_cancelled = self._cancelled

            if result is not None:
                self.task.result = result
                if result.get("cancelled"):
                    was_cancelled = True

            if was_cancelled:
                self.task.status = TaskStatus.CANCELLED
                self.task_cancelled.emit(self.task.task_id)
            else:
                self.task.status = TaskStatus.COMPLETED
                self.task.completed_at = datetime.now()
                self.task_completed.emit(self.task.task_id, self.task.result)
        except Exception as e:
            self.task.status = TaskStatus.FAILED
            self.task.error_message = str(e)
            self.task_failed.emit(self.task.task_id, str(e))

    def _emit_progress(self, current: int, total: int):
        self.task.progress = current
        self.task.total = total
        self.task_progress.emit(self.task.task_id, current, total)

    def _is_cancelled(self) -> bool:
        with QMutexLocker(self._mutex):
            return self._cancelled

    def _do_rename(self) -> dict:
        pattern = self.task.parameters.get("pattern", "{original}{ext}")
        photos = self.task.parameters.get("photos", [])
        rename_map = {}
        completed = []
        skipped = []
        total = len(photos)
        cancelled = False
        for i, photo in enumerate(photos):
            if self._is_cancelled():
                cancelled = True
                skipped.extend([p.filename for p in photos[i:]])
                break
            if not self._check_pause():
                cancelled = True
                skipped.extend([p.filename for p in photos[i:]])
                break
            new_name = image_utils.apply_rename_pattern(pattern, i + 1, photo, total)
            old_path = photo.file_path
            old_filename = photo.filename
            new_path = old_path.parent / new_name
            actual_new_name = new_name
            if old_path != new_path:
                if new_path.exists():
                    new_path = old_path.parent / image_utils.unique_filename(str(old_path.parent), new_name)
                    actual_new_name = new_path.name
                try:
                    old_path.rename(new_path)
                    photo.file_path = new_path
                    photo.filename = new_path.name
                    rename_map[str(old_path)] = str(new_path)
                    completed.append({"old": old_filename, "new": actual_new_name})
                except Exception as e:
                    skipped.append(f"{old_filename} (错误: {e})")
            else:
                skipped.append(f"{old_filename} (名称未变)")
            self._emit_progress(i + 1, total)
        return {
            "rename_map": rename_map,
            "completed": completed,
            "skipped": skipped,
            "cancelled": cancelled,
            "total": total,
        }

    def _do_move(self) -> dict:
        target_dir = Path(self.task.parameters.get("target_directory", ""))
        photos = self.task.parameters.get("photos", [])
        target_dir.mkdir(parents=True, exist_ok=True)
        move_map = {}
        completed = []
        skipped = []
        total = len(photos)
        cancelled = False
        for i, photo in enumerate(photos):
            if self._is_cancelled():
                cancelled = True
                skipped.extend([p.filename for p in photos[i:]])
                break
            if not self._check_pause():
                cancelled = True
                skipped.extend([p.filename for p in photos[i:]])
                break
            old_path = photo.file_path
            new_path = target_dir / image_utils.unique_filename(str(target_dir), photo.filename)
            try:
                shutil.move(str(old_path), str(new_path))
                photo.file_path = new_path
                photo.filename = new_path.name
                photo.target_directory = target_dir
                move_map[str(old_path)] = str(new_path)
                completed.append({"filename": photo.filename, "from": str(old_path.parent), "to": str(new_path.parent)})
            except Exception as e:
                skipped.append(f"{photo.filename} (错误: {e})")
            self._emit_progress(i + 1, total)
        return {
            "move_map": move_map,
            "completed": completed,
            "skipped": skipped,
            "cancelled": cancelled,
            "total": total,
        }

    def _do_delete_reject(self) -> dict:
        photos = self.task.parameters.get("photos", [])
        rejected = [p for p in photos if p.status == PhotoStatus.REJECT]
        deleted = []
        skipped = []
        total = len(rejected)
        cancelled = False
        for i, photo in enumerate(rejected):
            if self._is_cancelled():
                cancelled = True
                skipped.extend([p.filename for p in rejected[i:]])
                break
            if not self._check_pause():
                cancelled = True
                skipped.extend([p.filename for p in rejected[i:]])
                break
            try:
                if photo.file_path.exists():
                    send2trash(str(photo.file_path))
                    deleted.append({"filename": photo.filename, "path": str(photo.file_path)})
                else:
                    skipped.append(f"{photo.filename} (文件不存在)")
            except Exception as e:
                skipped.append(f"{photo.filename} (错误: {e})")
            self._emit_progress(i + 1, total)
        return {
            "deleted": deleted,
            "skipped": skipped,
            "cancelled": cancelled,
            "total": total,
        }

    def _do_compress(self) -> dict:
        target_dir = Path(self.task.parameters.get("target_directory", ""))
        quality = self.task.parameters.get("quality", 80)
        photos = self.task.parameters.get("photos", [])
        target_dir.mkdir(parents=True, exist_ok=True)
        compressed = []
        completed = []
        skipped = []
        total = len(photos)
        cancelled = False
        for i, photo in enumerate(photos):
            if self._is_cancelled():
                cancelled = True
                skipped.extend([p.filename for p in photos[i:]])
                break
            if not self._check_pause():
                cancelled = True
                skipped.extend([p.filename for p in photos[i:]])
                break
            try:
                with Image.open(photo.file_path) as img:
                    out_name = photo.filename
                    out_path = target_dir / image_utils.unique_filename(str(target_dir), out_name)
                    save_kwargs = {}
                    if img.format == "JPEG" or photo.extension in (".jpg", ".jpeg"):
                        save_kwargs["quality"] = quality
                        save_kwargs["optimize"] = True
                    elif img.format == "PNG":
                        save_kwargs["optimize"] = True
                    img.save(str(out_path), **save_kwargs)
                    compressed.append(str(out_path))
                    completed.append({"filename": photo.filename, "output": str(out_path)})
            except Exception as e:
                skipped.append(f"{photo.filename} (错误: {e})")
            self._emit_progress(i + 1, total)
        return {
            "compressed": compressed,
            "count": len(completed),
            "completed": completed,
            "skipped": skipped,
            "cancelled": cancelled,
            "total": total,
        }

    def _do_generate_manifest(self) -> dict:
        output_path = Path(self.task.parameters.get("output_path", ""))
        photos = self.task.parameters.get("photos", [])
        format_type = self.task.parameters.get("format", "csv")
        completed = []
        skipped = []
        total = len(photos)
        cancelled = False
        rows = []
        temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
        processed_photos = []

        status_counts = {}
        tag_summary = {}

        for i, photo in enumerate(photos):
            row = {
                "文件名": photo.filename,
                "路径": str(photo.file_path),
                "尺寸": photo.dimensions_str,
                "拍摄时间": photo.shot_time.strftime("%Y-%m-%d %H:%M:%S") if photo.shot_time else "",
                "大小(MB)": photo.size_mb,
                "状态": photo.status.value,
                "标签": ", ".join(photo.tags),
            }
            rows.append(row)
            completed.append(photo.filename)
            processed_photos.append(photo)

            status_key = photo.status.value
            status_counts[status_key] = status_counts.get(status_key, 0) + 1
            for tag in photo.tags:
                tag_summary[tag] = tag_summary.get(tag, 0) + 1

            self._emit_progress(i + 1, total)

            if i < total - 1:
                if self._is_cancelled():
                    cancelled = True
                    skipped.extend([p.filename for p in photos[i + 1:]])
                    rows = rows[:i + 1]
                    processed_photos = processed_photos[:i + 1]
                    break
                if not self._check_pause():
                    cancelled = True
                    skipped.extend([p.filename for p in photos[i + 1:]])
                    rows = rows[:i + 1]
                    processed_photos = processed_photos[:i + 1]
                    break

        final_path = ""
        if rows and not cancelled:
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                if format_type == "csv":
                    with open(temp_path, "w", newline="", encoding="utf-8-sig") as f:
                        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                        writer.writeheader()
                        writer.writerows(rows)
                else:
                    with open(temp_path, "w", encoding="utf-8") as f:
                        json.dump(rows, f, ensure_ascii=False, indent=2)
                temp_path.rename(output_path)
                final_path = str(output_path)
            except Exception as e:
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except:
                        pass
                raise e
        else:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass

        return {
            "manifest_path": final_path,
            "output_directory": str(output_path.parent) if final_path else "",
            "count": len(rows),
            "total": total,
            "completed": completed,
            "skipped": skipped,
            "cancelled": cancelled,
            "status_counts": status_counts,
            "tag_summary": tag_summary,
        }

    def _do_detect_duplicates(self) -> dict:
        photos = self.task.parameters.get("photos", [])
        use_perceptual = self.task.parameters.get("use_perceptual", True)
        hash_map = {}
        total = len(photos)
        cancelled = False
        scanned = 0
        for i, photo in enumerate(photos):
            if self._is_cancelled():
                cancelled = True
                break
            if not self._check_pause():
                cancelled = True
                break
            if use_perceptual:
                h = photo.perceptual_hash or image_utils.compute_perceptual_hash(str(photo.file_path))
                photo.perceptual_hash = h
            else:
                h = photo.hash or image_utils.compute_file_hash(str(photo.file_path))
                photo.hash = h
            if h:
                hash_map.setdefault(h, []).append(photo)
            scanned = i + 1
            self._emit_progress(i + 1, total)
        duplicates = [g for g in hash_map.values() if len(g) > 1]
        groups_detail = []
        for gi, group in enumerate(duplicates):
            for photo in group[1:]:
                photo.status = PhotoStatus.DUPLICATE
            groups_detail.append({
                "group": gi + 1,
                "count": len(group),
                "photos": [p.filename for p in group],
                "keep": group[0].filename,
                "duplicates": [p.filename for p in group[1:]],
            })
        return {
            "duplicate_groups": duplicates,
            "total_duplicates": sum(len(g) - 1 for g in duplicates),
            "groups_detail": groups_detail,
            "scanned": scanned,
            "cancelled": cancelled,
            "total": total,
        }

    def _do_apply_tags(self) -> dict:
        tags = self.task.parameters.get("tags", [])
        photos = self.task.parameters.get("photos", [])
        store = self.task.parameters.get("store")
        total = len(photos)
        completed = []
        skipped = []
        cancelled = False
        for i, photo in enumerate(photos):
            if self._is_cancelled():
                cancelled = True
                skipped.extend([p.filename for p in photos[i:]])
                break
            if not self._check_pause():
                cancelled = True
                skipped.extend([p.filename for p in photos[i:]])
                break
            old_tags = list(photo.tags)
            added = []
            new_tags = list(photo.tags)
            for tag in tags:
                if tag not in new_tags:
                    new_tags.append(tag)
                    added.append(tag)
            if added:
                if store:
                    store.update_photo_tags(photo, new_tags)
                else:
                    photo.tags = new_tags
                completed.append({"filename": photo.filename, "added": added, "old_tags": old_tags, "new_tags": list(photo.tags)})
            else:
                skipped.append(f"{photo.filename} (标签已存在)")
            self._emit_progress(i + 1, total)
        return {
            "applied_tags": tags,
            "photo_count": len(completed),
            "completed": completed,
            "skipped": skipped,
            "cancelled": cancelled,
            "total": total,
        }

    def _do_batch(self) -> dict:
        sub_tasks = self.task.parameters.get("sub_tasks", [])
        results = []
        for sub in sub_tasks:
            if self._is_cancelled():
                break
            if not self._check_pause():
                break
            self.task.name = sub.get("name", self.task.name)
            task_type = sub.get("task_type")
            params = sub.get("parameters", {})
            if task_type == TaskType.RENAME:
                self.task.parameters = params
                results.append(("rename", self._do_rename()))
            elif task_type == TaskType.MOVE:
                self.task.parameters = params
                results.append(("move", self._do_move()))
            elif task_type == TaskType.COMPRESS:
                self.task.parameters = params
                results.append(("compress", self._do_compress()))
            elif task_type == TaskType.GENERATE_MANIFEST:
                self.task.parameters = params
                results.append(("manifest", self._do_generate_manifest()))
            elif task_type == TaskType.APPLY_TAGS:
                self.task.parameters = params
                results.append(("tags", self._do_apply_tags()))
            elif task_type == TaskType.DELETE_REJECT:
                self.task.parameters = params
                results.append(("delete", self._do_delete_reject()))
            elif task_type == TaskType.DETECT_DUPLICATES:
                self.task.parameters = params
                results.append(("dedup", self._do_detect_duplicates()))
        return {"sub_results": results}


class TaskManager(QObject):
    task_added = Signal(object)
    task_updated = Signal(object)

    def __init__(self):
        super().__init__()
        self._tasks: dict = {}
        self._queue: list = []
        self._current_worker: Optional[TaskWorker] = None
        self._bus = EventBus.instance()

    @property
    def all_tasks(self) -> List[Task]:
        return list(self._tasks.values())

    @property
    def queue_tasks(self) -> List[Task]:
        return [t for t in self._tasks.values() if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.PAUSED)]

    @property
    def finished_tasks(self) -> List[Task]:
        return [t for t in self._tasks.values() if t.is_finished]

    def create_task(self, task_type: TaskType, name: str, description: str = "",
                    parameters: dict = None, can_undo: bool = False) -> Task:
        task = Task(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            name=name,
            description=description,
            parameters=parameters or {},
            can_undo=can_undo,
        )
        self._tasks[task.task_id] = task
        self.task_added.emit(task)
        self._bus.task_added.emit(task)
        self._bus.log_message.emit("info", f"已添加任务: {name}")
        return task

    def enqueue_task(self, task: Task):
        self._queue.append(task.task_id)
        task.status = TaskStatus.PENDING
        self.task_updated.emit(task)
        self._bus.task_updated.emit(task)
        self._process_queue()

    def _process_queue(self):
        if self._current_worker is not None:
            return
        while self._queue:
            task_id = self._queue.pop(0)
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                self._start_worker(task)
                break

    def _start_worker(self, task: Task):
        worker = TaskWorker(task)
        worker.task_progress.connect(self._on_progress)
        worker.task_completed.connect(self._on_completed)
        worker.task_failed.connect(self._on_failed)
        worker.task_cancelled.connect(self._on_cancelled)
        worker.log.connect(lambda lvl, msg: self._bus.log_message.emit(lvl, msg))
        self._current_worker = worker
        task.status = TaskStatus.RUNNING
        self.task_updated.emit(task)
        self._bus.task_updated.emit(task)
        worker.start()

    def _on_progress(self, task_id: str, current: int, total: int):
        task = self._tasks.get(task_id)
        if task:
            task.progress = current
            task.total = total
            self.task_updated.emit(task)
            self._bus.task_updated.emit(task)

    def _on_completed(self, task_id: str, result):
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            self.task_updated.emit(task)
            self._bus.task_completed.emit(task)
            self._bus.log_message.emit("success", f"任务完成: {task.name}")
        self._current_worker = None
        self._process_queue()

    def _on_failed(self, task_id: str, error: str):
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = error
            self.task_updated.emit(task)
            self._bus.task_failed.emit(task)
            self._bus.log_message.emit("error", f"任务失败: {task.name} - {error}")
        self._current_worker = None
        self._process_queue()

    def _on_cancelled(self, task_id: str):
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.CANCELLED
            self.task_updated.emit(task)
            self._bus.task_updated.emit(task)
            self._bus.log_message.emit("warning", f"任务已取消: {task.name}")
        self._current_worker = None
        self._process_queue()

    def pause_current(self):
        if self._current_worker:
            self._current_worker.pause()
            task = self._current_worker.task
            task.status = TaskStatus.PAUSED
            self.task_updated.emit(task)
            self._bus.task_updated.emit(task)

    def resume_current(self):
        if self._current_worker:
            self._current_worker.resume()
            task = self._current_worker.task
            task.status = TaskStatus.RUNNING
            self.task_updated.emit(task)
            self._bus.task_updated.emit(task)

    def cancel_current(self):
        if self._current_worker:
            self._current_worker.cancel()

    def clear_finished(self):
        to_remove = [tid for tid, t in self._tasks.items() if t.is_finished]
        for tid in to_remove:
            del self._tasks[tid]
        self._bus.all_tasks_cleared.emit()

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    @property
    def is_busy(self) -> bool:
        return self._current_worker is not None

    @property
    def current_task(self) -> Optional[Task]:
        if self._current_worker:
            return self._current_worker.task
        return None
