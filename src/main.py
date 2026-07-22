# src/main.py (修改后的完整版本)
"""
桌面宠物 - 主入口
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import QPoint

from config_manager import ConfigManager
from tar_extractor import TarExtractor
from skin_manager import SkinManager
from behavior_manager import BehaviorManager
from pet_widget import PetWidget
from settings_dialog import SettingsDialog


class DesktopPetApp:
    """桌面宠物应用主类"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # 加载输出版本信息
        metadata_path = Path(__file__).parent.parent / "metadata.json"
        print("[提示] 正在加载版本信息...")
        if metadata_path.exists():
            try:
                import json
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                print("=" * 40)
                print(f"  {meta.get('name', '桌面宠物')}")
                print(f"  版本：{meta.get('version', '未知')}")
                print(f"  作者：{meta.get('author', '')}")
                print(f"  协议：{meta.get('license', '')}")
                print("=" * 40)
            except Exception as e:
                print(f"[警告] 读取 metadata.json 失败：{e}")
        else:
            print("[提示] 未找到 metadata.json，跳过版本信息")

        # 初始化核心模块
        self.config = ConfigManager()
        self.tar_extractor = TarExtractor()
        self.skin_manager = SkinManager(self.config, self.tar_extractor)
        self.behavior_manager = BehaviorManager()

        # 首次启动：自动解压 res 目录下的 tar
        self._auto_extract_res()

        # 应用当前皮肤
        active_skin = self.skin_manager.get_active_skin()
        if active_skin:
            self.skin_manager._apply_skin_to_config(active_skin)

        # 创建宠物窗口
        self.pet_widget = PetWidget(self.config)

        # 创建设置对话框（延迟创建）
        self.settings_dialog = None

        # 创建系统托盘
        self._create_tray()

        # 连接信号
        self.pet_widget.right_clicked.connect(self._show_context_menu)

    def _auto_extract_res(self) -> None:
        """自动解压 res 目录下的所有 tar 文件"""
        res_dir = self.tar_extractor.res_dir
        if res_dir.exists():
            for tar_file in res_dir.glob("*.tar"):
                self.tar_extractor.extract_tar(tar_file)

    def _create_tray(self) -> None:
        """创建系统托盘图标"""
        self.tray = QSystemTrayIcon()
        self.tray.setToolTip("桌面宠物")

        # 尝试加载图标
        icon_path = Path(__file__).parent.parent / "res" / "icon.png"
        if icon_path.exists():
            self.tray.setIcon(QIcon(str(icon_path)))
        else:
            self.tray.setIcon(self.app.style().standardIcon(
                self.app.style().StandardPixmap.SP_ComputerIcon
            ))

        # 托盘菜单
        tray_menu = QMenu()

        action_settings = QAction("⚙️ 设置", None)
        action_settings.triggered.connect(self._open_settings)
        tray_menu.addAction(action_settings)

        action_refresh = QAction("🔄 刷新皮肤", None)
        action_refresh.triggered.connect(self._refresh_skin)
        tray_menu.addAction(action_refresh)

        tray_menu.addSeparator()

        action_quit = QAction("❌ 退出", None)
        action_quit.triggered.connect(self._quit)
        tray_menu.addAction(action_quit)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        """托盘图标双击打开设置"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._open_settings()

    def _show_context_menu(self, global_pos: QPoint) -> None:
        """右键菜单"""
        menu = QMenu()

        action_settings = QAction("⚙️ 设置", menu)
        action_settings.triggered.connect(self._open_settings)
        menu.addAction(action_settings)

        action_refresh = QAction("🔄 刷新皮肤", menu)
        action_refresh.triggered.connect(self._refresh_skin)
        menu.addAction(action_refresh)

        menu.addSeparator()

        action_quit = QAction("❌ 退出", menu)
        action_quit.triggered.connect(self._quit)
        menu.addAction(action_quit)

        menu.exec(global_pos)

    def _open_settings(self) -> None:
        """打开设置对话框"""
        if self.settings_dialog is None or not self.settings_dialog.isVisible():
            self.settings_dialog = SettingsDialog(
                self.config, self.tar_extractor, self.skin_manager
            )
            self.settings_dialog.settings_applied.connect(self._on_settings_applied)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def _on_settings_applied(self) -> None:
        """设置应用后的回调"""
        # 刷新宠物显示
        self.pet_widget.refresh_state()
        self.pet_widget._apply_scale()
        self.pet_widget.update_move_speed()

        # 置顶设置
        always_on_top = self.config.get("always_on_top", True)
        self.pet_widget.set_always_on_top(always_on_top)

        # 重新加载行为引擎
        self.pet_widget.reload_behavior_engine()

    def _refresh_skin(self) -> None:
        """刷新皮肤"""
        active_skin = self.skin_manager.get_active_skin()
        if active_skin:
            self.skin_manager._apply_skin_to_config(active_skin)
            self.pet_widget.refresh_state()

    def _quit(self) -> None:
        """退出应用"""
        # 保存窗口位置
        self.config.set_position(self.pet_widget.x(), self.pet_widget.y())
        self.config.save()

        # 停止行为引擎
        if self.pet_widget.behavior_engine:
            self.pet_widget.behavior_engine.stop()
            self.pet_widget.behavior_engine.wait(2000)

        self.tray.hide()
        self.app.quit()

    def run(self) -> int:
        """运行应用"""
        self.pet_widget.show()
        return self.app.exec()


def main():
    app = DesktopPetApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()