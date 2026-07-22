# src/config_manager.py (修改后的完整版本)
"""
配置管理器
管理 pet_config.json 的读写
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DEFAULT_CONFIG = {
    "active_skin": "",
    "animation_fps": 8,
    "scale": 1.0,
    "move_speed": 6.0,
    "always_on_top": True,
    "click_through": False,
    "position": {"x": 100, "y": 100},
    "interaction_mapping": {
        "left_click": "click",
        "double_click": "click"
    },
    "states": {
        "idle": {
            "description": "待机状态",
            "loop": True,
            "images": []
        },
        "walk": {
            "description": "行走状态",
            "loop": True,
            "images": []
        },
        "click": {
            "description": "点击反应",
            "loop": False,
            "images": []
        },
        "hover": {
            "description": "悬停状态",
            "loop": True,
            "images": []
        },
        "drag": {
            "description": "拖拽状态",
            "loop": True,
            "images": []
        },
        "sleep": {
            "description": "睡眠状态",
            "loop": True,
            "images": []
        }
    }
}


class ConfigManager:
    """配置管理器单例"""

    _instance: Optional['ConfigManager'] = None

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

        self.config_path = self.config_dir / "pet_config.json"
        self._data: Dict = {}
        self.load()

    def load(self) -> None:
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = DEFAULT_CONFIG.copy()
                self.save()
        else:
            self._data = DEFAULT_CONFIG.copy()
            self.save()

    def save(self) -> None:
        """保存配置"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[ConfigManager] 保存失败: {e}")

    def get(self, key: str, default=None):
        """获取配置项"""
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        """设置配置项"""
        self._data[key] = value

    # ==================== 状态相关 ====================

    def get_all_states(self) -> Dict:
        return self._data.get("states", {})

    def get_state_images(self, state_name: str) -> List[str]:
        states = self._data.get("states", {})
        state = states.get(state_name, {})
        return state.get("images", [])

    def set_state_images(self, state_name: str, images: List[str]) -> None:
        if "states" not in self._data:
            self._data["states"] = {}
        if state_name not in self._data["states"]:
            self._data["states"][state_name] = {"description": "", "loop": True, "images": []}
        self._data["states"][state_name]["images"] = images

    # ==================== 位置相关 ====================

    def get_position(self) -> Tuple[int, int]:
        pos = self._data.get("position", {"x": 100, "y": 100})
        return pos.get("x", 100), pos.get("y", 100)

    def set_position(self, x: int, y: int) -> None:
        self._data["position"] = {"x": x, "y": y}

    # ==================== 交互映射 ====================

    def get_interaction_mapping(self) -> Dict[str, str]:
        return self._data.get("interaction_mapping", {
            "left_click": "click",
            "double_click": "click"
        })