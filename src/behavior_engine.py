# src/behavior_engine.py
"""
行为引擎
独立线程，负责根据规则自动触发宠物状态切换
"""

import time
import random
from PySide6.QtCore import QThread, Signal, QTimer
from typing import List, Dict

class BehaviorEngine(QThread):
    """行为引擎线程"""

    # 信号：触发状态切换 (state_name, duration_seconds)
    trigger_action = Signal(str, int)

    def __init__(self, behaviors: List[Dict], parent=None):
        super().__init__(parent)
        self.behaviors = behaviors
        self._running = True
        self._paused = False  # 被打断时暂停
        
        # 记录每个规则的上次触发时间
        self._last_trigger_time = {}
        # 记录当前正在执行的动作结束时间
        self._current_action_end_time = 0

    def pause(self) -> None:
        """暂停引擎（被打断时调用）"""
        self._paused = True
        # 重置所有规则的计时器，防止恢复后立刻触发
        self._last_trigger_time = {i: time.time() for i in range(len(self.behaviors))}

    def resume(self) -> None:
        """恢复引擎"""
        self._paused = False
        self._last_trigger_time = {i: time.time() for i in range(len(self.behaviors))}

    def stop(self) -> None:
        self._running = False

    def update_behaviors(self, behaviors: List[Dict]) -> None:
        """更新规则列表"""
        self.behaviors = behaviors
        self._last_trigger_time = {i: time.time() for i in range(len(self.behaviors))}

    def run(self) -> None:
        """线程主循环"""
        # 初始化时间
        for i in range(len(self.behaviors)):
            self._last_trigger_time[i] = time.time()

        while self._running:
            if self._paused:
                self.msleep(500)
                continue

            now = time.time()

            # 如果当前正在执行某个动作，等待其结束
            if now < self._current_action_end_time:
                self.msleep(200)
                continue

            # 遍历规则（按优先级，即列表顺序）
            triggered = False
            for i, rule in enumerate(self.behaviors):
                if not rule.get("enabled", True):
                    continue

                trigger_type = rule.get("trigger", "idle")
                trigger_val = rule.get("trigger_value", 10)
                last_time = self._last_trigger_time.get(i, now)
                elapsed = now - last_time

                should_trigger = False

                if trigger_type == "idle":
                    # 空闲触发：超过指定秒数
                    if elapsed >= trigger_val:
                        should_trigger = True
                elif trigger_type == "timer":
                    # 定时触发：每隔指定秒数
                    if elapsed >= trigger_val:
                        should_trigger = True
                elif trigger_type == "random":
                    # 随机触发：每秒有 (trigger_val/100) 的概率触发
                    # 这里简化为每秒判定一次
                    if elapsed >= 1.0:
                        if random.randint(1, 100) <= trigger_val:
                            should_trigger = True

                if should_trigger:
                    state = rule.get("action_state", "idle")
                    duration = rule.get("action_duration", 5)
                    self.trigger_action.emit(state, duration)
                    
                    # 更新状态
                    self._last_trigger_time[i] = now
                    self._current_action_end_time = now + duration
                    triggered = True
                    break  # 触发一个后跳出，等待动作结束

            # 休眠一小段时间，避免 CPU 占用过高
            self.msleep(500)