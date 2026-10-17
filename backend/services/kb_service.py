"""
DermaSense Clinical Knowledge Base Service.
Loads, validates, and serves verified dermatological condition guides.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from backend.config import KNOWLEDGE_BASE_DIR


class KnowledgeBaseService:
    def __init__(self, kb_dir: Path = KNOWLEDGE_BASE_DIR):
        self.kb_dir = kb_dir
        self._conditions: Dict[str, dict] = {}
        self.reload()

    def reload(self):
        """Scans and caches all condition JSON records from the knowledge base directory."""
        self._conditions.clear()
        if not self.kb_dir.exists():
            return

        for json_path in self.kb_dir.glob("*.json"):
            if json_path.name == "conditions.json":
                continue
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cid = data.get("condition_id")
                    if cid:
                        self._conditions[cid] = data
            except Exception as e:
                print(f"[WARN] Error reading knowledge base file {json_path}: {e}")

    def get(self, condition_id: str) -> Optional[dict]:
        """Fetches guidance record by condition identifier."""
        return self._conditions.get(condition_id)

    def get_all(self) -> List[dict]:
        """Returns all loaded condition records."""
        return list(self._conditions.values())

    def get_summaries(self) -> List[dict]:
        """Returns concise summary objects for the conditions catalog."""
        summaries = []
        for c in self._conditions.values():
            summaries.append({
                "condition_id": c.get("condition_id", ""),
                "name": c.get("name", ""),
                "local_names": c.get("local_names", []),
                "description": c.get("description", ""),
                "severity_level": c.get("severity_level", "low"),
                "contagious": c.get("contagious", False),
                "reviewed_by_clinician": c.get("reviewed_by_clinician", False),
            })
        return summaries


# Singleton instance
kb_service = KnowledgeBaseService()

