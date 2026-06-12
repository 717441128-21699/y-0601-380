import json
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from core.history_rule import HistoryRule


APP_DATA_DIR = Path.home() / ".PhotoFlow"
RULES_FILE = APP_DATA_DIR / "rules.json"


def ensure_app_data_dir():
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)


class RuleManager:
    def __init__(self):
        ensure_app_data_dir()
        self.rules: List[HistoryRule] = []
        self._load()

    def _load(self):
        if RULES_FILE.exists():
            try:
                with open(RULES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.rules = [HistoryRule.from_dict(item) for item in data.get("rules", [])]
            except Exception:
                self.rules = []

    def _save(self):
        try:
            with open(RULES_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {"rules": [r.to_dict() for r in self.rules]},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception:
            pass

    def save_rule(self, rule: HistoryRule) -> HistoryRule:
        if not rule.rule_id:
            rule.rule_id = str(uuid.uuid4())
        rule.created_at = datetime.now()
        self.rules.append(rule)
        self._save()
        return rule

    def update_rule(self, rule: HistoryRule):
        for i, r in enumerate(self.rules):
            if r.rule_id == rule.rule_id:
                self.rules[i] = rule
                self._save()
                return

    def delete_rule(self, rule_id: str):
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        self._save()

    def mark_used(self, rule_id: str):
        for r in self.rules:
            if r.rule_id == rule_id:
                r.last_used = datetime.now()
                r.use_count += 1
                self._save()
                return

    def get_recent(self, limit: int = 10) -> List[HistoryRule]:
        sorted_rules = sorted(
            self.rules,
            key=lambda r: (r.last_used or r.created_at),
            reverse=True,
        )
        return sorted_rules[:limit]

    def get_all(self) -> List[HistoryRule]:
        return sorted(self.rules, key=lambda r: r.created_at, reverse=True)
