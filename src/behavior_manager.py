# src/behavior_manager.py
"""
行为配置管理器
独立管理 behaviors.json，负责自动行为规则的读写
"""

import json
from pathlib import Path
from typing import List, Dict, Optional

# 默认行为规则（如果文件不存在则生成）
DEFAULT_BEHAVIORS = [
    {
        "name": "默认待机",
        "enabled": True,
        "trigger": "idle",       # idle(空闲), timer(定时), random(随机)
        "trigger_value": 10,     # idle: 空闲秒数, timer: 间隔秒数, random: 概率(0-100)
        "action_state": "walk",  # 切换到的状态
        "action_duration": 5     # 动作持续秒数（0表示一直播放直到被打断）
    }
]

class BehaviorManager:
    """行为规则管理器单例"""

    _instance: Optional['BehaviorManager'] = None

    def __new__(cls, config_dir: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_dir: str = None):
        if self._initialized:
            return
        self._initialized = True

        if config_dir is None:
            project_root = Path(__file__).parent.parent
            config_dir = project_root / "config"
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_path = self.config_dir / "behaviors.json"
        self.behaviors: List[Dict] = []
        self.load()

    def load(self) -> None:
        """加载行为配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.behaviors = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.behaviors = DEFAULT_BEHAVIORS.copy()
                self.save()
        else:
            self.behaviors = DEFAULT_BEHAVIORS.copy()
            self.save()

    def save(self) -> None:
        """保存行为配置"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.behaviors, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[BehaviorManager] 保存失败: {e}")

    def get_all(self) -> List[Dict]:
        return self.behaviors

    def set_all(self, behaviors: List[Dict]) -> None:
        self.behaviors = behaviors
        self.save()

    def add(self, behavior: Dict) -> None:
        self.behaviors.append(behavior)
        self.save()

    def remove(self, index: int) -> None:
        if 0 <= index < len(self.behaviors):
            self.behaviors.pop(index)
            self.save()

    def update(self, index: int, behavior: Dict) -> None:
        if 0 <= index < len(self.behaviors):
            self.behaviors[index] = behavior
            self.save()

    def move_up(self, index: int) -> None:
        if index > 0:
            self.behaviors[index], self.behaviors[index-1] = self.behaviors[index-1], self.behaviors[index]
            self.save()

    def move_down(self, index: int) -> None:
        if index < len(self.behaviors) - 1:
            self.behaviors[index], self.behaviors[index+1] = self.behaviors[index+1], self.behaviors[index]
            self.save()