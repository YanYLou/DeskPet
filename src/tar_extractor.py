# src/tar_extractor.py
"""
TAR 图片包解压与缓存管理
支持从 .tar 中提取 .png 和 .gif 图片
tar 内部按子目录组织，目录名即为状态名：

    test_pet.tar
    ├── idle/
    │   ├── frame_001.png
    │   └── frame_002.png
    ├── click/
    │   └── frame_001.png
    ├── hover/
    │   └── ...
    └── walk/
        └── ...
"""

import tarfile
import os
import tempfile
from pathlib import Path, PurePosixPath
from typing import List, Dict, Optional


class TarExtractor:
    """
    从 res/ 目录读取 .tar 包，解压图片到临时缓存目录。
    支持 .png 和 .gif 格式。
    按 tar 内子目录名自动归类为对应状态。
    """

    SUPPORTED_EXTENSIONS = {'.png', '.gif'}

    def __init__(self, res_dir: str = None, cache_dir: str = None):
        # 资源目录
        if res_dir is None:
            project_root = Path(__file__).parent.parent
            res_dir = project_root / "res"
        self.res_dir = Path(res_dir)

        # 缓存目录（解压后的图片存放处）
        if cache_dir is None:
            cache_dir = Path(tempfile.gettempdir()) / "desktop_pet_cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 记录已解压的 tar -> {状态名: [图片路径]} 映射
        self._extracted: Dict[str, Dict[str, List[str]]] = {}

    def scan_tar_files(self) -> List[Path]:
        """扫描 res/ 目录下所有 .tar 文件"""
        if not self.res_dir.exists():
            print(f"[TarExtractor] 资源目录不存在: {self.res_dir}")
            return []
        return sorted(self.res_dir.glob("*.tar"))

    def extract_tar(self, tar_path: Path) -> Dict[str, List[str]]:
        """
        解压单个 .tar 文件。
        返回 {状态名(子目录名): [图片绝对路径列表]} 的字典。
        已解压过的不会重复解压。
        """
        tar_key = str(tar_path)
        if tar_key in self._extracted:
            return self._extracted[tar_key]

        # 为每个 tar 创建独立子目录，避免文件名冲突
        tar_name = tar_path.stem  # 去掉 .tar 后缀
        extract_to = self.cache_dir / tar_name
        extract_to.mkdir(parents=True, exist_ok=True)

        state_images: Dict[str, List[str]] = {}

        try:
            with tarfile.open(tar_path, 'r') as tar:
                # 安全过滤：防止路径穿越攻击，只提取支持的图片
                members = []
                for member in tar.getmembers():
                    ext = Path(member.name).suffix.lower()
                    if ext not in self.SUPPORTED_EXTENSIONS:
                        continue
                    if not member.isfile():
                        continue
                    # 安全检查
                    if PurePosixPath(member.name).is_absolute():
                        continue
                    if '..' in member.name:
                        continue
                    members.append(member)

                tar.extractall(path=extract_to, members=members)

                # 按子目录归类
                for member in members:
                    img_path = extract_to / member.name
                    if not img_path.exists():
                        continue

                    # 提取子目录名作为状态名
                    # 例如 "idle/frame_001.png" -> 状态名 "idle"
                    # 例如 "walk/left/001.png"  -> 状态名 "walk/left"（取第一级）
                    parts = PurePosixPath(member.name).parts
                    if len(parts) >= 2:
                        state_name = parts[0]  # 第一级目录名
                    else:
                        # 没有子目录的图片归入 "default"
                        state_name = "default"

                    if state_name not in state_images:
                        state_images[state_name] = []
                    state_images[state_name].append(str(img_path.resolve()))

        except (tarfile.TarError, IOError) as e:
            print(f"[TarExtractor] 解压失败 {tar_path.name}: {e}")
            return {}

        # 每个状态内的图片按文件名排序，保证帧顺序
        for state_name in state_images:
            state_images[state_name].sort(key=lambda p: Path(p).name)

        self._extracted[tar_key] = state_images

        total = sum(len(v) for v in state_images.values())
        states_str = ", ".join(
            f"{k}({len(v)}帧)" for k, v in state_images.items()
        )
        print(f"[TarExtractor] 已解压 {tar_path.name}: 共 {total} 张图片 [{states_str}]")

        return state_images

    def extract_all(self) -> Dict[str, Dict[str, List[str]]]:
        """
        解压 res/ 下所有 .tar 文件。
        返回 {tar文件名: {状态名: [图片路径列表]}} 的字典。
        """
        result: Dict[str, Dict[str, List[str]]] = {}
        for tar_path in self.scan_tar_files():
            state_images = self.extract_tar(tar_path)
            if state_images:
                result[tar_path.name] = state_images
        return result

    def get_merged_states(self) -> Dict[str, List[str]]:
        """
        解压所有 tar 并合并。
        如果多个 tar 包含同名状态目录，后者的图片追加到前者。
        返回 {状态名: [图片路径列表]}。
        """
        all_tars = self.extract_all()
        merged: Dict[str, List[str]] = {}
        for tar_name, states in all_tars.items():
            for state_name, images in states.items():
                if state_name not in merged:
                    merged[state_name] = []
                merged[state_name].extend(images)
        return merged

    def cleanup_cache(self) -> None:
        """清理缓存目录（程序退出时可选调用）"""
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir, ignore_errors=True)
            print("[TarExtractor] 缓存已清理")