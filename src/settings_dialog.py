# src/settings_dialog.py (修改后的完整版本)
"""
桌面宠物 - 设置对话框
"""

import os
from pathlib import Path
from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTabWidget, QWidget, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QSpinBox, QDoubleSpinBox, QCheckBox,
    QFileDialog, QGroupBox, QComboBox, QMessageBox,
    QAbstractItemView, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialogButtonBox, QFormLayout
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QIcon

from config_manager import ConfigManager
from tar_extractor import TarExtractor
from skin_manager import SkinManager
from behavior_manager import BehaviorManager


class AnimationPreview(QLabel):
    """动画预览组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(128, 128)
        self.setMaximumSize(200, 200)
        self.setStyleSheet(
            "background: rgba(40, 40, 40, 200); "
            "border: 1px solid #555; border-radius: 6px;"
        )
        self._frames: List[str] = []
        self._index: int = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next_frame)

    def set_frames(self, frames: List[str], fps: int = 8) -> None:
        self._frames = frames
        self._index = 0
        if frames:
            interval = max(1, int(1000 / fps))
            self._timer.start(interval)
            self._show_current()
        else:
            self._timer.stop()
            self.setText("无图片")

    def stop(self) -> None:
        self._timer.stop()

    def _next_frame(self) -> None:
        if not self._frames: return
        self._index = (self._index + 1) % len(self._frames)
        self._show_current()

    def _show_current(self) -> None:
        if self._index >= len(self._frames): return
        pixmap = QPixmap(self._frames[self._index])
        if pixmap.isNull(): return
        scaled = pixmap.scaled(
            self.width() - 20, self.height() - 20,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled)


class StateEditorTab(QWidget):
    """单个状态的编辑页"""

    images_changed = Signal(str, list)

    def __init__(self, state_name: str, state_config: Dict,
                 tar_extractor: TarExtractor, parent=None):
        super().__init__(parent)
        self.state_name = state_name
        self.state_config = state_config
        self.tar_extractor = tar_extractor
        self._init_ui()
        self._load_images()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        desc = self.state_config.get("description", "")
        if desc:
            desc_label = QLabel(f"说明：{desc}")
            desc_label.setStyleSheet("color: #888; font-size: 12px;")
            layout.addWidget(desc_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：图片列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        list_label = QLabel(f"图片列表（{self.state_name}）：")
        left_layout.addWidget(list_label)

        self.image_list = QListWidget()
        self.image_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.image_list.itemSelectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.image_list)

        # 按钮行
        btn_layout = QHBoxLayout()
        self.btn_add_tar = QPushButton("从资源包添加")
        self.btn_add_tar.clicked.connect(self._add_from_tar)
        btn_layout.addWidget(self.btn_add_tar)

        self.btn_add_local = QPushButton("从本地添加")
        self.btn_add_local.clicked.connect(self._add_from_local)
        btn_layout.addWidget(self.btn_add_local)

        self.btn_remove = QPushButton("移除选中")
        self.btn_remove.setEnabled(False)
        self.btn_remove.clicked.connect(self._remove_selected)
        btn_layout.addWidget(self.btn_remove)
        left_layout.addLayout(btn_layout)

        # 上移/下移
        order_layout = QHBoxLayout()
        self.btn_up = QPushButton("↑ 上移")
        self.btn_up.setEnabled(False)
        self.btn_up.clicked.connect(self._move_up)
        order_layout.addWidget(self.btn_up)

        self.btn_down = QPushButton("↓ 下移")
        self.btn_down.setEnabled(False)
        self.btn_down.clicked.connect(self._move_down)
        order_layout.addWidget(self.btn_down)
        order_layout.addStretch()
        left_layout.addLayout(order_layout)

        splitter.addWidget(left_widget)

        # 右侧：预览
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        preview_label = QLabel("预览：")
        right_layout.addWidget(preview_label)

        self.preview = AnimationPreview()
        right_layout.addWidget(self.preview)

        self.btn_preview = QPushButton("▶ 播放预览")
        self.btn_preview.clicked.connect(self._start_preview)
        right_layout.addWidget(self.btn_preview)
        right_layout.addStretch()
        splitter.addWidget(right_widget)

        splitter.setSizes([350, 200])
        layout.addWidget(splitter)

    def _load_images(self) -> None:
        self.image_list.clear()
        images = self.state_config.get("images", [])
        for img_path in images:
            item = QListWidgetItem(img_path)
            item.setText(Path(img_path).name)
            item.setToolTip(img_path)
            item.setData(Qt.ItemDataRole.UserRole, img_path)
            self.image_list.addItem(item)
        self._update_preview()

    def _get_all_image_paths(self) -> List[str]:
        paths = []
        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            paths.append(item.data(Qt.ItemDataRole.UserRole))
        return paths

    def _add_from_tar(self) -> None:
        merged = self.tar_extractor.get_merged_states()
        if not merged:
            QMessageBox.information(self, "提示", "没有找到已解压的资源包图片。")
            return

        all_images = []
        for state, imgs in merged.items():
            for img in imgs:
                all_images.append(f"[{state}] {Path(img).name}  →  {img}")

        from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("选择资源包中的图片")
        dlg.setMinimumSize(500, 400)
        dlg_layout = QVBoxLayout(dlg)

        info_label = QLabel("选择要添加的图片（可多选）：")
        dlg_layout.addWidget(info_label)

        list_widget = QListWidget()
        list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for entry in all_images:
            list_widget.addItem(entry)
        dlg_layout.addWidget(list_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        dlg_layout.addWidget(buttons)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected = list_widget.selectedItems()
            for item in selected:
                text = item.text()
                if "→" in text:
                    img_path = text.split("→")[-1].strip()
                else:
                    img_path = text.strip()
                self._add_image_item(img_path)
            self._emit_change()

    def _add_from_local(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "选择图片文件", "", "图片文件 (*.png *.gif);;所有文件 (*)")
        if files:
            for f in files:
                self._add_image_item(f)
            self._emit_change()

    def _add_image_item(self, img_path: str) -> None:
        existing = self._get_all_image_paths()
        if img_path in existing: return
        item = QListWidgetItem(Path(img_path).name)
        item.setToolTip(img_path)
        item.setData(Qt.ItemDataRole.UserRole, img_path)
        self.image_list.addItem(item)

    def _remove_selected(self) -> None:
        selected = self.image_list.selectedItems()
        for item in selected:
            row = self.image_list.row(item)
            self.image_list.takeItem(row)
        self._emit_change()

    def _move_up(self) -> None:
        row = self.image_list.currentRow()
        if row > 0:
            item = self.image_list.takeItem(row)
            self.image_list.insertItem(row - 1, item)
            self.image_list.setCurrentRow(row - 1)
            self._emit_change()

    def _move_down(self) -> None:
        row = self.image_list.currentRow()
        if row < self.image_list.count() - 1:
            item = self.image_list.takeItem(row)
            self.image_list.insertItem(row + 1, item)
            self.image_list.setCurrentRow(row + 1)
            self._emit_change()

    def _on_selection_changed(self) -> None:
        has_selection = len(self.image_list.selectedItems()) > 0
        self.btn_remove.setEnabled(has_selection)
        row = self.image_list.currentRow()
        self.btn_up.setEnabled(row > 0)
        self.btn_down.setEnabled(0 <= row < self.image_list.count() - 1)

    def _start_preview(self) -> None:
        images = self._get_all_image_paths()
        self.preview.set_frames(images, 8)

    def _update_preview(self) -> None:
        images = self._get_all_image_paths()
        if images:
            pixmap = QPixmap(images[0])
            if not pixmap.isNull():
                scaled = pixmap.scaled(160, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.preview.setPixmap(scaled)
            else:
                self.preview.setText("无法加载")
        else:
            self.preview.setText("无图片")

    def _emit_change(self) -> None:
        self._update_preview()
        self.images_changed.emit(self.state_name, self._get_all_image_paths())


class BehaviorRuleDialog(QDialog):
    """添加/编辑单条行为规则的对话框"""

    def __init__(self, rule: Dict = None, available_states: List[str] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑行为规则")
        self.setMinimumWidth(350)
        self.rule = rule or {}
        self.available_states = available_states or ["idle"]
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QFormLayout(self)

        self.input_name = QComboBox()
        self.input_name.setEditable(True)
        layout.addRow("规则名称:", self.input_name)

        self.chk_enabled = QCheckBox("启用")
        layout.addRow(self.chk_enabled)

        self.combo_trigger = QComboBox()
        self.combo_trigger.addItems(["idle", "timer", "random"])
        self.combo_trigger.currentTextChanged.connect(self._on_trigger_changed)
        layout.addRow("触发类型:", self.combo_trigger)

        self.spin_value = QSpinBox()
        self.spin_value.setRange(1, 3600)
        layout.addRow("触发参数:", self.spin_value)

        self.combo_state = QComboBox()
        self.combo_state.addItems(self.available_states)
        layout.addRow("动作状态:", self.combo_state)

        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(0, 3600)
        self.spin_duration.setSpecialValueText("永久")
        layout.addRow("持续秒数:", self.spin_duration)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        # 填充数据
        self._load_data()

    def _load_data(self) -> None:
        self.input_name.setCurrentText(self.rule.get("name", "新规则"))
        self.chk_enabled.setChecked(self.rule.get("enabled", True))
        
        trigger = self.rule.get("trigger", "idle")
        self.combo_trigger.setCurrentText(trigger)
        
        self.spin_value.setValue(self.rule.get("trigger_value", 10))
        
        action_state = self.rule.get("action_state", "idle")
        if action_state in self.available_states:
            self.combo_state.setCurrentText(action_state)
            
        self.spin_duration.setValue(self.rule.get("action_duration", 5))

    def _on_trigger_changed(self, text: str) -> None:
        if text == "random":
            self.spin_value.setRange(1, 100)
            self.spin_value.setSuffix(" %")
        else:
            self.spin_value.setSuffix(" 秒")
            self.spin_value.setRange(1, 3600)

    def get_rule(self) -> Dict:
        return {
            "name": self.input_name.currentText(),
            "enabled": self.chk_enabled.isChecked(),
            "trigger": self.combo_trigger.currentText(),
            "trigger_value": self.spin_value.value(),
            "action_state": self.combo_state.currentText(),
            "action_duration": self.spin_duration.value()
        }


class SettingsDialog(QDialog):
    """设置主对话框"""

    settings_applied = Signal()

    def __init__(self, config: ConfigManager, tar_extractor: TarExtractor,
                 skin_manager: SkinManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.tar_extractor = tar_extractor
        self.skin_manager = skin_manager
        self.behavior_manager = BehaviorManager()

        self.setWindowTitle("桌面宠物 - 设置")
        self.setMinimumSize(700, 550)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        # Tab 1: 皮肤管理
        self._build_skin_tab()
        # Tab 2: 状态图片配置
        self._build_states_tab()
        # Tab 3: 自动行为
        self._build_behavior_tab()
        # Tab 4: 通用设置
        self._build_general_tab()

        main_layout.addWidget(self.tabs)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_apply = QPushButton("应用")
        self.btn_apply.clicked.connect(self._apply_settings)
        btn_layout.addWidget(self.btn_apply)

        self.btn_ok = QPushButton("确定")
        self.btn_ok.clicked.connect(self._ok)
        btn_layout.addWidget(self.btn_ok)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(btn_layout)

    def _build_skin_tab(self) -> None:
        """构建皮肤管理选项卡"""
        skin_widget = QWidget()
        layout = QVBoxLayout(skin_widget)

        info_label = QLabel("管理你的宠物皮肤（.tar 文件）。\n内置皮肤位于 res/ 目录，用户皮肤位于 AppData 目录。")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # 皮肤列表
        self.skin_list = QListWidget()
        layout.addWidget(self.skin_list)

        # 按钮行
        btn_layout = QHBoxLayout()
        
        self.btn_add_skin = QPushButton("➕ 添加皮肤")
        self.btn_add_skin.clicked.connect(self._add_skin)
        btn_layout.addWidget(self.btn_add_skin)

        self.btn_delete_skin = QPushButton("🗑️ 删除皮肤")
        self.btn_delete_skin.clicked.connect(self._delete_skin)
        btn_layout.addWidget(self.btn_delete_skin)

        self.btn_refresh_skins = QPushButton("🔄 刷新列表")
        self.btn_refresh_skins.clicked.connect(self._refresh_skin_list)
        btn_layout.addWidget(self.btn_refresh_skins)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 当前激活的皮肤
        active_layout = QHBoxLayout()
        active_layout.addWidget(QLabel("当前激活皮肤:"))
        self.combo_active_skin = QComboBox()
        active_layout.addWidget(self.combo_active_skin)
        layout.addLayout(active_layout)

        self._refresh_skin_list()
        self.tabs.addTab(skin_widget, "皮肤管理")

    def _refresh_skin_list(self) -> None:
        """刷新皮肤列表"""
        self.skin_list.clear()
        self.combo_active_skin.clear()
        
        skins = self.skin_manager.get_available_skins()
        active_skin = self.skin_manager.get_active_skin()

        for skin in skins:
            self.skin_list.addItem(skin)
            self.combo_active_skin.addItem(skin)
        
        if active_skin in skins:
            self.combo_active_skin.setCurrentText(active_skin)

    def _add_skin(self) -> None:
        """添加新皮肤"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择皮肤文件 (.tar)", "", "Tar 文件 (*.tar)")
        if file_path:
            if self.skin_manager.import_skin(file_path):
                self._refresh_skin_list()
                QMessageBox.information(self, "成功", "皮肤添加成功！")
            else:
                QMessageBox.warning(self, "失败", "皮肤添加失败，请检查文件。")

    def _delete_skin(self) -> None:
        """删除选中的皮肤"""
        current_item = self.skin_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一个皮肤。")
            return

        skin_name = current_item.text()
        reply = QMessageBox.question(self, "确认删除", f"确定要删除皮肤 '{skin_name}' 吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.skin_manager.delete_skin(skin_name):
                self._refresh_skin_list()
            else:
                QMessageBox.warning(self, "失败", "无法删除该皮肤（可能是内置皮肤）。")

    def _build_states_tab(self) -> None:
        """构建状态图片配置选项卡"""
        states = self.config.get_all_states()
        self.state_editors: Dict[str, StateEditorTab] = {}

        states_widget = QWidget()
        states_layout = QVBoxLayout(states_widget)

        self.state_tabs = QTabWidget()
        self.state_tabs.setTabPosition(QTabWidget.TabPosition.West)

        for state_name, state_cfg in states.items():
            editor = StateEditorTab(state_name, state_cfg, self.tar_extractor)
            editor.images_changed.connect(self._on_images_changed)
            self.state_editors[state_name] = editor
            self.state_tabs.addTab(editor, state_name)

        states_layout.addWidget(self.state_tabs)
        self.tabs.addTab(states_widget, "状态图片")

    def _build_behavior_tab(self) -> None:
        """构建自动行为选项卡"""
        behavior_widget = QWidget()
        layout = QVBoxLayout(behavior_widget)

        info_label = QLabel("配置宠物的自动行为规则。规则按从上到下的顺序执行，越靠上优先级越高。\n用户交互（点击、悬停、拖拽）会暂时打断自动行为。")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # 规则表格
        self.behavior_table = QTableWidget()
        self.behavior_table.setColumnCount(5)
        self.behavior_table.setHorizontalHeaderLabels(["启用", "规则名称", "触发类型", "动作状态", "持续秒数"])
        self.behavior_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.behavior_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.behavior_table)

        # 按钮行
        btn_layout = QHBoxLayout()
        
        self.btn_add_rule = QPushButton("➕ 添加规则")
        self.btn_add_rule.clicked.connect(self._add_behavior_rule)
        btn_layout.addWidget(self.btn_add_rule)

        self.btn_edit_rule = QPushButton("✏️ 编辑规则")
        self.btn_edit_rule.clicked.connect(self._edit_behavior_rule)
        btn_layout.addWidget(self.btn_edit_rule)

        self.btn_remove_rule = QPushButton("🗑️ 删除规则")
        self.btn_remove_rule.clicked.connect(self._remove_behavior_rule)
        btn_layout.addWidget(self.btn_remove_rule)

        btn_layout.addStretch()

        self.btn_move_up = QPushButton("↑ 上移")
        self.btn_move_up.clicked.connect(self._move_rule_up)
        btn_layout.addWidget(self.btn_move_up)

        self.btn_move_down = QPushButton("↓ 下移")
        self.btn_move_down.clicked.connect(self._move_rule_down)
        btn_layout.addWidget(self.btn_move_down)

        layout.addLayout(btn_layout)

        self._refresh_behavior_table()
        self.tabs.addTab(behavior_widget, "自动行为")
        
    def _refresh_behavior_table(self) -> None:
        """刷新行为规则表格"""
        behaviors = self.behavior_manager.get_all()
        self.behavior_table.setRowCount(len(behaviors))

        for row, rule in enumerate(behaviors):
            # 启用状态
            chk = QCheckBox()
            chk.setChecked(rule.get("enabled", True))
            chk.stateChanged.connect(lambda state, r=row: self._on_rule_check_changed(r, state))
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.addWidget(chk)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            self.behavior_table.setCellWidget(row, 0, chk_widget)

            # 规则名称
            name_item = QTableWidgetItem(rule.get("name", "未命名"))
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.behavior_table.setItem(row, 1, name_item)

            # 触发类型
            trigger = rule.get("trigger", "idle")
            trigger_val = rule.get("trigger_value", 10)
            if trigger == "idle":
                trigger_text = f"空闲 {trigger_val}秒"
            elif trigger == "timer":
                trigger_text = f"定时 {trigger_val}秒"
            elif trigger == "random":
                trigger_text = f"随机 {trigger_val}%"
            else:
                trigger_text = trigger
            trigger_item = QTableWidgetItem(trigger_text)
            trigger_item.setFlags(trigger_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.behavior_table.setItem(row, 2, trigger_item)

            # 动作状态
            action_item = QTableWidgetItem(rule.get("action_state", "idle"))
            action_item.setFlags(action_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.behavior_table.setItem(row, 3, action_item)

            # 持续秒数
            duration = rule.get("action_duration", 5)
            dur_text = "永久" if duration == 0 else f"{duration}秒"
            dur_item = QTableWidgetItem(dur_text)
            dur_item.setFlags(dur_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.behavior_table.setItem(row, 4, dur_item)

    def _on_rule_check_changed(self, row: int, state: int) -> None:
        """规则启用/禁用复选框变化"""
        behaviors = self.behavior_manager.get_all()
        if 0 <= row < len(behaviors):
            behaviors[row]["enabled"] = (state == Qt.CheckState.Checked.value)
            self.behavior_manager.save()

    def _add_behavior_rule(self) -> None:
        """添加新规则"""
        available_states = list(self.config.get_all_states().keys())
        dlg = BehaviorRuleDialog(rule=None, available_states=available_states, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_rule = dlg.get_rule()
            self.behavior_manager.add(new_rule)
            self._refresh_behavior_table()

    def _edit_behavior_rule(self) -> None:
        """编辑选中规则"""
        row = self.behavior_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择一条规则。")
            return

        behaviors = self.behavior_manager.get_all()
        if row >= len(behaviors):
            return

        available_states = list(self.config.get_all_states().keys())
        dlg = BehaviorRuleDialog(rule=behaviors[row], available_states=available_states, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            updated_rule = dlg.get_rule()
            self.behavior_manager.update(row, updated_rule)
            self._refresh_behavior_table()

    def _remove_behavior_rule(self) -> None:
        """删除选中规则"""
        row = self.behavior_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择一条规则。")
            return

        reply = QMessageBox.question(self, "确认删除", "确定要删除这条行为规则吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.behavior_manager.remove(row)
            self._refresh_behavior_table()

    def _move_rule_up(self) -> None:
        """上移规则"""
        row = self.behavior_table.currentRow()
        if row > 0:
            self.behavior_manager.move_up(row)
            self._refresh_behavior_table()
            self.behavior_table.setCurrentCell(row - 1, 0)

    def _move_rule_down(self) -> None:
        """下移规则"""
        row = self.behavior_table.currentRow()
        behaviors = self.behavior_manager.get_all()
        if 0 <= row < len(behaviors) - 1:
            self.behavior_manager.move_down(row)
            self._refresh_behavior_table()
            self.behavior_table.setCurrentCell(row + 1, 0)

    def _build_general_tab(self) -> None:
        """构建通用设置选项卡"""
        general_widget = QWidget()
        layout = QVBoxLayout(general_widget)

        # 动画帧率
        fps_group = QGroupBox("动画设置")
        fps_layout = QFormLayout()

        self.spin_fps = QSpinBox()
        self.spin_fps.setRange(1, 60)
        self.spin_fps.setValue(self.config.get("animation_fps", 8))
        self.spin_fps.setSuffix(" FPS")
        fps_layout.addRow("帧率:", self.spin_fps)

        self.spin_scale = QDoubleSpinBox()
        self.spin_scale.setRange(0.25, 4.0)
        self.spin_scale.setSingleStep(0.25)
        self.spin_scale.setValue(self.config.get("scale", 1.0))
        self.spin_scale.setSuffix(" x")
        fps_layout.addRow("缩放:", self.spin_scale)

        fps_group.setLayout(fps_layout)
        layout.addWidget(fps_group)

        # 动画设置
        move_group = QGroupBox("移动设置")
        move_layout = QFormLayout()

        self.spin_move_speed = QSpinBox()
        self.spin_move_speed.setRange(1, 20)
        self.spin_move_speed.setValue(self.config.get("move_speed", 6))
        self.spin_move_speed.setSuffix(" 像素/帧")
        move_layout.addRow("移动速度:", self.spin_move_speed)

        move_group.setLayout(move_layout)
        layout.addWidget(move_group)

        # 窗口设置
        win_group = QGroupBox("窗口设置")
        win_layout = QFormLayout()

        self.chk_always_on_top = QCheckBox("始终置顶")
        self.chk_always_on_top.setChecked(self.config.get("always_on_top", True))
        win_layout.addRow(self.chk_always_on_top)

        self.chk_click_through = QCheckBox("鼠标穿透（仅显示，不可交互）")
        self.chk_click_through.setChecked(self.config.get("click_through", False))
        win_layout.addRow(self.chk_click_through)

        win_group.setLayout(win_layout)
        layout.addWidget(win_group)

        # 交互映射
        interaction_group = QGroupBox("交互映射")
        interaction_layout = QFormLayout()

        states = list(self.config.get_all_states().keys())
        interaction_map = self.config.get_interaction_mapping()

        self.combo_left_click = QComboBox()
        self.combo_left_click.addItems(states)
        self.combo_left_click.setCurrentText(interaction_map.get("left_click", "click"))
        interaction_layout.addRow("左键点击 →", self.combo_left_click)

        self.combo_double_click = QComboBox()
        self.combo_double_click.addItems(states)
        self.combo_double_click.setCurrentText(interaction_map.get("double_click", "click"))
        interaction_layout.addRow("双击 →", self.combo_double_click)

        interaction_group.setLayout(interaction_layout)
        layout.addWidget(interaction_group)

        layout.addStretch()
        self.tabs.addTab(general_widget, "通用设置")

    # ==================== 信号处理 ====================

    def _on_images_changed(self, state_name: str, images: List[str]) -> None:
        """状态图片变更回调"""
        self.config.set_state_images(state_name, images)

    def _apply_settings(self) -> None:
        """应用所有设置"""
        # 通用设置
        self.config.set("animation_fps", self.spin_fps.value())
        self.config.set("scale", self.spin_scale.value())
        self.config.set("move_speed", self.spin_move_speed.value())
        self.config.set("always_on_top", self.chk_always_on_top.isChecked())
        self.config.set("click_through", self.chk_click_through.isChecked())

        # 交互映射
        self.config.set("interaction_mapping", {
            "left_click": self.combo_left_click.currentText(),
            "double_click": self.combo_double_click.currentText()
        })

        # 皮肤切换
        active_skin = self.combo_active_skin.currentText()
        if active_skin and active_skin != self.skin_manager.get_active_skin():
            self.skin_manager.set_active_skin(active_skin)

        # 保存所有配置
        self.config.save()

        # 发出信号通知主窗口刷新
        self.settings_applied.emit()

    def _ok(self) -> None:
        """确定按钮"""
        self._apply_settings()
        self.accept()