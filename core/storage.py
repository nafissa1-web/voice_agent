"""
Very small local "database" for missions, backed by a JSON file.
This is what lets you close the app and come back later to see every
task/idea/summary you've ever recorded, instead of losing it on refresh.

Swap this for SQLite/Postgres later without touching app.py — only the
function bodies below would need to change.
"""

import json
import os
import uuid
from datetime import datetime
from threading import Lock

STORAGE_PATH = os.getenv("MISSIONS_STORE", "missions.json")
_lock = Lock()


def _read_all() -> list:
    if not os.path.exists(STORAGE_PATH):
        return []
    with open(STORAGE_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _write_all(missions: list) -> None:
    with open(STORAGE_PATH, "w", encoding="utf-8") as f:
        json.dump(missions, f, ensure_ascii=False, indent=2)


def load_missions() -> list:
    with _lock:
        return _read_all()


def add_mission(source_text: str, insights: dict) -> dict:
    mission = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source_text": source_text,
        "done": False,
        "notion_page_id": None,
        **insights,
    }
    with _lock:
        missions = _read_all()
        missions.append(mission)
        _write_all(missions)
    return mission


def update_mission(mission_id: str, updates: dict) -> None:
    with _lock:
        missions = _read_all()
        for m in missions:
            if m["id"] == mission_id:
                m.update(updates)
                break
        _write_all(missions)


def delete_mission(mission_id: str) -> None:
    with _lock:
        missions = _read_all()
        missions = [m for m in missions if m["id"] != mission_id]
        _write_all(missions)
