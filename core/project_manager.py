"""
DataForge Project Manager

Saves and loads project state using a local JSON store.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class ProjectManager:
    """Manages DataForge project persistence."""

    def __init__(self):
        self.projects_dir = Path.home() / '.dataforge' / 'projects'
        self.prefs_file = Path.home() / '.dataforge' / 'preferences.json'
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self._preferences: Dict[str, Any] = self._load_preferences()

    def save_project(self, name: str, data: Dict[str, Any]) -> str:
        project_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        project_file = self.projects_dir / f"{project_id}_{name[:30]}.json"

        save_data = {
            'id': project_id,
            'name': name,
            'saved_at': datetime.now().isoformat(),
            'dialect': data.get('dialect', 'snowflake'),
            'row_count': data.get('row_count', 0),
            'column_count': data.get('column_count', 0),
            'table_name': data.get('table_name', ''),
            'source_file': data.get('source_file', ''),
            'data': data,
        }

        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, default=str)

        self._preferences['last_project'] = str(project_file)
        self._save_preferences()
        return project_id

    def list_projects(self, limit: int = 10) -> List[Dict[str, Any]]:
        projects = []
        for f in sorted(self.projects_dir.glob('*.json'), reverse=True)[:limit]:
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)
                projects.append({
                    'id': data.get('id', ''),
                    'name': data.get('name', ''),
                    'dialect': data.get('dialect', ''),
                    'row_count': data.get('row_count', 0),
                    'saved_at': data.get('saved_at', ''),
                })
            except Exception:
                continue
        return projects

    def load_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        for f in self.projects_dir.glob(f'{project_id}*.json'):
            with open(f, 'r', encoding='utf-8') as fp:
                return json.load(fp)
        return None

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self._preferences.get(key, default)

    def set_preference(self, key: str, value: Any):
        self._preferences[key] = value
        self._save_preferences()

    def _load_preferences(self) -> Dict[str, Any]:
        if self.prefs_file.exists():
            try:
                with open(self.prefs_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {'default_dialect': 'snowflake'}

    def _save_preferences(self):
        with open(self.prefs_file, 'w', encoding='utf-8') as f:
            json.dump(self._preferences, f, indent=2)
