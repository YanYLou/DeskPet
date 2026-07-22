# src/skin_manager.py
"""
皮肤管理器
负责管理 AppData 下的皮肤文件，以及当前激活的皮肤
"""

import shutil
import os
from pathlib import Path
from typing import List, Dict, Optional

from config_manager import ConfigManager
from tar_extractor import TarExtractor

class SkinManager:
    """皮肤管理器"""

    def __init__(self, config: ConfigManager, tar_extractor: TarExtractor):
        self.config = config
        self.tar_extractor = tar_extractor

        # 设定 AppData 路径
        app_data_local = Path(os.getenv('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
        self.skins_dir = app_data_local / "DesktopPet" / "Skins"
        self.skins_dir.mkdir(parents=True, exist_ok=True)

        # 同时扫描内置 res 目录
        self.res_dir = tar_extractor.res_dir

    def get_available_skins(self) -> List[str]:
        """获取所有可用的皮肤名称（.tar 文件名）"""
        skins = set()
        # 扫描 AppData
        if self.skins_dir.exists():
            for p in self.skins_dir.glob("*.tar"):
                skins.add(p.name)
        # 扫描 res 目录
        if self.res_dir.exists():
            for p in self.res_dir.glob("*.tar"):
                skins.add(p.name)
        return sorted(list(skins))

    def import_skin(self, source_path: str) -> bool:
        """从外部导入皮肤到 AppData"""
        src = Path(source_path)
        if not src.exists() or src.suffix.lower() != '.tar':
            return False
        
        dest = self.skins_dir / src.name
        try:
            shutil.copy2(src, dest)
            print(f"[SkinManager] 已导入皮肤: {src.name} -> {dest}")
            return True
        except IOError as e:
            print(f"[SkinManager] 导入失败: {e}")
            return False

    def delete_skin(self, skin_name: str) -> bool:
        """删除 AppData 中的皮肤（不能删除 res 目录下的）"""
        target = self.skins_dir / skin_name
        if target.exists():
            try:
                target.unlink()
                return True
            except IOError:
                return False
        return False

    def get_active_skin(self) -> str:
        """获取当前激活的皮肤名"""
        return self.config.get("active_skin", "")

    def set_active_skin(self, skin_name: str) -> None:
        """设置并应用激活的皮肤"""
        self.config.set("active_skin", skin_name)
        # 重新加载该皮肤的图片到配置中
        self._apply_skin_to_config(skin_name)

    def _apply_skin_to_config(self, skin_name: str) -> None:
        """将指定皮肤的 tar 内容覆盖到 config 的 states 中"""
        # 查找 tar 文件路径
        tar_path = self.skins_dir / skin_name
        if not tar_path.exists():
            tar_path = self.res_dir / skin_name
        
        if not tar_path.exists():
            print(f"[SkinManager] 找不到皮肤文件: {skin_name}")
            return

        # 强制重新解压并获取状态映射
        # 清除缓存以确保获取最新
        if str(tar_path) in self.tar_extractor._extracted:
            del self.tar_extractor._extracted[str(tar_path)]
            
        state_images = self.tar_extractor.extract_tar(tar_path)
        
        # 覆盖配置中的图片
        for state_name, images in state_images.items():
            self.config.set_state_images(state_name, images)
        
        print(f"[SkinManager] 已应用皮肤: {skin_name}, 包含状态: {list(state_images.keys())}")

    def refresh(self) -> None:
        """刷新皮肤列表（热更新）"""
        # 这里不需要做太多，get_available_skins 每次都会重新扫描
        pass