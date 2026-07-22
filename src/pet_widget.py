# src/pet_widget.py
"""
桌面宠物核心窗口
"""

import random
from PySide6.QtWidgets import QWidget, QLabel, QApplication
from PySide6.QtCore import Qt, QTimer, QPoint, Signal
from PySide6.QtGui import QPixmap, QMovie, QCursor, QTransform

from pathlib import Path
from typing import List, Optional

from config_manager import ConfigManager
from behavior_engine import BehaviorEngine


class PetWidget(QWidget):
    """桌面宠物主窗口"""

    state_changed = Signal(str)
    right_clicked = Signal(QPoint)

    def __init__(self, config: ConfigManager):
        super().__init__()
        self.config = config

        # 窗口属性
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint

            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        # 动画组件
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.current_state: str = "idle"
        self.current_frames: List[str] = []
        self.current_frame_index: int = 0
        self.is_gif: bool = False
        self.movie: Optional[QMovie] = None

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._next_frame)

        # ========== 移动相关 ==========
        self._move_timer = QTimer(self)
        self._move_timer.setInterval(30)
        self._move_timer.timeout.connect(self._on_move_tick)

        self._walk_duration_timer = QTimer(self)
        self._walk_duration_timer.setSingleShot(True)
        self._walk_duration_timer.timeout.connect(self._on_walk_duration_expired)

        self._target_pos: Optional[QPoint] = None
        self._move_speed = self.config.get("move_speed", 6)
        self._facing_left: bool = False
        self._walk_active: bool = False  # 防止重复触发
        # ==============================

        # 交互状态
        self._dragging = False
        self._drag_offset = QPoint()
        self._hovering = False

        # 行为引擎
        self.behavior_engine: Optional[BehaviorEngine] = None
        self._init_behavior_engine()

        # 初始化
        self._load_state("idle")
        self._restore_position()
        self._apply_scale()

    def _init_behavior_engine(self) -> None:
        from behavior_manager import BehaviorManager
        bm = BehaviorManager()
        self.behavior_engine = BehaviorEngine(bm.get_all())
        self.behavior_engine.trigger_action.connect(self._on_behavior_trigger)
        self.behavior_engine.start()

    def _on_behavior_trigger(self, state_name: str, duration: int) -> None:
        """行为引擎触发的动作"""
        if self._dragging:
            return
        self._load_state(state_name, duration)

    def _interrupt_behavior(self) -> None:
        """打断当前自动行为"""
        self._stop_walk()
        if self.behavior_engine:
            self.behavior_engine.pause()
            QTimer.singleShot(2000, self.behavior_engine.resume)

    # ==================== 移动逻辑 ====================

    def update_move_speed(self):
        """更新速度"""
        self._move_speed = self.config.get("move_speed", 6)

    def _pick_new_target(self) -> None:
        """随机选取一个新的目标点"""
        screen = QApplication.primaryScreen()
        if screen is None:
            return

        screen_geo = screen.availableGeometry()
        pet_w = self.width() or 100
        pet_h = self.height() or 100

        max_x = screen_geo.width() - pet_w
        max_y = screen_geo.height() - pet_h
        if max_x <= 0 or max_y <= 0:
            return

        target_x = random.randint(screen_geo.x(), screen_geo.x() + max_x)
        target_y = random.randint(screen_geo.y(), screen_geo.y() + max_y)
        self._target_pos = QPoint(target_x, target_y)

        # 更新朝向
        self._facing_left = target_x < self.x()

    def _start_walk(self, duration_sec: int) -> None:
        """
        开始行走
        duration_sec: 行走总时长（秒），0 表示无限走（不推荐）
        """
        if self._walk_active:
            return

        self._walk_active = True
        self._pick_new_target()
        self._move_timer.start()

        # 时长控制：到期后无论在哪都停止
        if duration_sec > 0:
            self._walk_duration_timer.start(duration_sec * 1000)
        else:
            # 兜底：最多走 60 秒，防止无限走
            self._walk_duration_timer.start(60 * 1000)

    def _stop_walk(self) -> None:
        """停止行走，恢复 idle"""
        if not self._walk_active:
            return

        self._walk_active = False
        self._move_timer.stop()
        self._walk_duration_timer.stop()
        self._target_pos = None
        self._facing_left = False

        if self.current_state == "walk":
            self._load_state("idle")

    def _on_move_tick(self) -> None:
        """每 tick 向目标移动一步"""
        if self._target_pos is None or not self._walk_active:
            self._stop_walk()
            return

        current = self.pos()
        dx = self._target_pos.x() - current.x()
        dy = self._target_pos.y() - current.y()
        distance = (dx * dx + dy * dy) ** 0.5

        # ★ 到达目标 → 不终止，选新目标继续走
        if distance <= self._move_speed:
            self.move(self._target_pos)
            self.config.set_position(self.x(), self.y())
            self._pick_new_target()  # ← 关键：继续找下一个目标
            return

        # 归一化 × 速度
        step_x = int(dx / distance * self._move_speed)
        step_y = int(dy / distance * self._move_speed)
        self.move(QPoint(current.x() + step_x, current.y() + step_y))

    def _on_walk_duration_expired(self) -> None:
        """行走时长到期 → 停止，没走到就算了"""
        self.config.set_position(self.x(), self.y())
        self._stop_walk()
        
    # ==================== 动画控制 ====================

    def _load_state(self, state_name: str, duration: int = 0) -> None:
        """
        加载指定状态
        duration: 行为引擎传入的持续秒数（仅 walk 用到）
        """
        # 非 walk 状态 → 确保行走停止
        if state_name != "walk":
            if self._walk_active:
                self._move_timer.stop()
                self._walk_duration_timer.stop()
                self._target_pos = None
                self._walk_active = False
                self._facing_left = False  # ← 重置方向

        # walk 状态 → 启动移动
        if state_name == "walk":
            self._start_walk(duration)

        # 加载图片
        images = self.config.get_state_images(state_name)

        if not images:
            self.image_label.setText(f"[{state_name}]")
            self.image_label.setStyleSheet(
                "color: white; font-size: 14px; background: rgba(0,0,0,128); "
                "border-radius: 8px; padding: 10px;"
            )
            self.anim_timer.stop()
            self.current_state = state_name
            self.state_changed.emit(state_name)
            return
        else:
            self.image_label.setStyleSheet(None)

        self.current_state = state_name
        self.current_frames = images
        self.current_frame_index = 0

        first_img = images[0]
        ext = Path(first_img).suffix.lower()

        if ext == '.gif':
            self._play_gif(first_img)
        else:
            self._play_png_sequence()

        self.state_changed.emit(state_name)

    def _play_gif(self, gif_path: str) -> None:
        self.anim_timer.stop()
        self.is_gif = True
        self.movie = QMovie(gif_path)
        self.image_label.setMovie(self.movie)
        self.movie.start()
        self.movie.frameChanged.connect(self._adjust_size_to_movie)
        self._adjust_size_to_movie()

    def _play_png_sequence(self) -> None:
        self.is_gif = False
        if self.movie:
            self.movie.stop()
            self.movie = None
        self.image_label.setMovie(None)

        fps = self.config.get("animation_fps", 8)
        interval = max(1, int(1000 / fps))
        self.anim_timer.start(interval)
        self._show_frame(0)

    def _next_frame(self) -> None:
        if not self.current_frames:
            return
        self.current_frame_index += 1
        if self.current_frame_index >= len(self.current_frames):
            states = self.config.get_all_states()
            state_cfg = states.get(self.current_state, {})
            if state_cfg.get("loop", True):
                self.current_frame_index = 0
            else:
                self.anim_timer.stop()
                QTimer.singleShot(500, lambda: self._load_state("idle"))
                return
        self._show_frame(self.current_frame_index)

    def _show_frame(self, index: int) -> None:
        if index >= len(self.current_frames):
            return
        img_path = self.current_frames[index]
        pixmap = QPixmap(img_path)
        if pixmap.isNull():
            return

        scale = self.config.get("scale", 1.0)
        if scale != 1.0:
            new_w = int(pixmap.width() * scale)
            new_h = int(pixmap.height() * scale)
            pixmap = pixmap.scaled(
                new_w, new_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

        # walk 状态 + 向左走 → 水平翻转
        if self.current_state == "walk" and self._facing_left:
            pixmap = pixmap.transformed(QTransform().scale(-1, 1))

        self.image_label.setPixmap(pixmap)
        self.image_label.setFixedSize(pixmap.size())
        self.setFixedSize(pixmap.size())

    def _adjust_size_to_movie(self) -> None:
        if self.movie:
            pixmap = self.movie.currentPixmap()
            scale = self.config.get("scale", 1.0)
            if scale != 1.0:
                new_w = int(pixmap.width() * scale)
                new_h = int(pixmap.height() * scale)
                pixmap = pixmap.scaled(
                    new_w, new_h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            self.image_label.setFixedSize(pixmap.size())
            self.setFixedSize(pixmap.size())

    def _apply_scale(self) -> None:
        if self.is_gif and self.movie:
            self._adjust_size_to_movie()
        elif self.current_frames:
            self._show_frame(self.current_frame_index)

    # ==================== 鼠标交互 ====================

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            self._stop_walk()
            self._load_state("drag")
            self._interrupt_behavior()

        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self._dragging:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            self.move(new_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._dragging:
                self._dragging = False
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
                self.config.set_position(self.x(), self.y())

                move_dist = (
                    event.globalPosition().toPoint() - self.pos() - self._drag_offset
                ).manhattanLength()

                if move_dist < 5:
                    self._on_left_click()
                else:
                    self._load_state("idle")
                    self._interrupt_behavior()

    def enterEvent(self, event):
        self._hovering = True
        if not self._dragging:
            self._stop_walk()
            self._load_state("hover")
            self._interrupt_behavior()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovering = False
        if not self._dragging:
            self._load_state("idle")
        super().leaveEvent(event)

    def _on_left_click(self):
        interaction_map = self.config.get_interaction_mapping()
        target_state = interaction_map.get("left_click", "click")
        self._load_state(target_state)
        self._interrupt_behavior()

    # ==================== 位置与显示 ====================

    def _restore_position(self) -> None:
        x, y = self.config.get_position()
        self.move(x, y)

    def set_always_on_top(self, on_top: bool) -> None:
        flags = self.windowFlags()
        if on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def refresh_state(self) -> None:
        self._load_state(self.current_state)

    def reload_behavior_engine(self) -> None:
        if self.behavior_engine:
            from behavior_manager import BehaviorManager
            bm = BehaviorManager()
            self.behavior_engine.update_behaviors(bm.get_all())