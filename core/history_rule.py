from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class HistoryRule:
    rule_id: str
    name: str
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    use_count: int = 0

    rename_pattern: Optional[str] = None
    target_directory: Optional[str] = None
    compress_quality: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    keep_status_only: bool = True
    delete_rejected: bool = False
    detect_duplicates: bool = False
    generate_manifest: bool = False
    extra_config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "use_count": self.use_count,
            "rename_pattern": self.rename_pattern,
            "target_directory": self.target_directory,
            "compress_quality": self.compress_quality,
            "tags": self.tags,
            "keep_status_only": self.keep_status_only,
            "delete_rejected": self.delete_rejected,
            "detect_duplicates": self.detect_duplicates,
            "generate_manifest": self.generate_manifest,
            "extra_config": self.extra_config,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryRule":
        return cls(
            rule_id=data["rule_id"],
            name=data["name"],
            description=data.get("description", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            use_count=data.get("use_count", 0),
            rename_pattern=data.get("rename_pattern"),
            target_directory=data.get("target_directory"),
            compress_quality=data.get("compress_quality"),
            tags=data.get("tags", []),
            keep_status_only=data.get("keep_status_only", True),
            delete_rejected=data.get("delete_rejected", False),
            detect_duplicates=data.get("detect_duplicates", False),
            generate_manifest=data.get("generate_manifest", False),
            extra_config=data.get("extra_config", {}),
        )
