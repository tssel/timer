#!/usr/bin/env python3
# smooth_circle_timer.py
#
# pip install PyQt6
# python smooth_circle_timer.py

import sys
import time

from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLineEdit,
    QMenu,
)


WINDOW_SIZE = 360
GREEN = "#26ba35"


class CircleTimer(QWidget):
    def __init__(self):
        super().__init__()

        # Timer state
        self.total_seconds = 25 * 60
        self.remaining_seconds = self.total_seconds

        self.running = False
        self.editing = False
        self.mode = "timer"  # timer or stopwatch
        self.stopwatch_elapsed = 0.0

        # smooth timing
        self.last_tick = time.time()
        self.display_seconds = float(self.remaining_seconds)

        self.setWindowTitle("Smooth Circle Timer")
        self.setFixedSize(WINDOW_SIZE, WINDOW_SIZE)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # high frequency UI update (smooth animation)
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_frame)
        self.ui_timer.start(16)  # ~60fps

        # real second timer (keeps accuracy)
        self.sec_timer = QTimer()
        self.sec_timer.timeout.connect(self.tick_second)
        self.sec_timer.start(1000)

        # time display
        self.time_edit = QLineEdit(self.format_time(self.remaining_seconds), self)
        self.time_edit.setGeometry(70, 105, 220, 60)
        self.time_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_edit.setReadOnly(True)

        self.time_edit.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: white;
                font-size: 42px;
                font-weight: 600;
            }
        """)

        self.time_edit.mousePressEvent = self.start_editing
        self.time_edit.returnPressed.connect(self.finish_editing)

        # play/pause button
        self.button = QPushButton("▶", self)
        self.button.setGeometry(130, 170, 100, 100)

        self.button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: white;
                font-size: 42px;
            }

            QPushButton:hover {
                color: rgb(220,220,220);
            }
        """)

        self.button.clicked.connect(self.toggle_timer)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)

        # right click menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # dragging
        self.drag_pos = None

    # ------------------------
    # Timer logic
    # ------------------------

    def toggle_timer(self):
        if self.editing:
            return

        self.running = not self.running
        self.button.setText("⏸" if self.running else "▶")

        self.last_tick = time.time()

    def tick_second(self):
        if not self.running or self.editing:
            return

        if self.mode == "timer":
            if self.remaining_seconds > 0:
                self.remaining_seconds -= 1

            if self.remaining_seconds <= 0:
                self.remaining_seconds = 0
                self.display_seconds = 0
                self.running = False
                self.button.setText("▶")

    # ------------------------
    # Smooth animation frame
    # ------------------------

    def update_frame(self):
        now = time.time()

        if self.running and not self.editing:
            delta = now - self.last_tick
            self.last_tick = now

            if self.mode == "timer":
                self.display_seconds -= delta

                if self.display_seconds <= 0:
                    self.display_seconds = 0
                    self.remaining_seconds = 0
                    self.running = False
                    self.button.setText("▶")

                self.time_edit.setText(
                    self.format_time(int(self.display_seconds))
                )

            elif self.mode == "stopwatch":
                self.stopwatch_elapsed += delta

                self.time_edit.setText(
                    self.format_time(int(self.stopwatch_elapsed))
                )

        self.update()

    # ------------------------
    # Editing
    # ------------------------

    def start_editing(self, event):
        if self.editing:
            return

        self.editing = True
        self.running = False
        self.button.setText("▶")

        self.time_edit.setReadOnly(False)
        self.time_edit.setFocus()
        self.time_edit.selectAll()

    def finish_editing(self):
        text = self.time_edit.text().strip()

        try:
            m, s = text.split(":")
            total = int(m) * 60 + int(s)

            if total > 0 and self.mode == "timer":
                self.total_seconds = total
                self.remaining_seconds = total
                self.display_seconds = float(total)

        except:
            pass

        self.time_edit.setText(
            self.format_time(self.remaining_seconds)
        )

        self.time_edit.setReadOnly(True)
        self.editing = False
    # ------------------------
    # Context menu
    # ------------------------

    def show_context_menu(self, pos):
        menu = QMenu(self)

        timer_action = menu.addAction("Timer")
        stopwatch_action = menu.addAction("Stopwatch")

        action = menu.exec(self.mapToGlobal(pos))

        if action == timer_action:
            self.switch_to_timer()

        elif action == stopwatch_action:
            self.switch_to_stopwatch()

    def switch_to_timer(self):
        self.mode = "timer"

        self.running = False
        self.button.setText("▶")

        self.total_seconds = 25 * 60
        self.remaining_seconds = self.total_seconds
        self.display_seconds = float(self.total_seconds)

        self.time_edit.setText(
            self.format_time(self.remaining_seconds)
        )

        self.update()

    def switch_to_stopwatch(self):
        self.mode = "stopwatch"

        self.running = False
        self.button.setText("▶")

        self.stopwatch_elapsed = 0

        self.time_edit.setText("00:00")

        self.update()

    # ------------------------
    # Drawing
    # ------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # background circle
        painter.setBrush(QColor(28, 28, 28, 235))
        painter.setPen(Qt.PenStyle.NoPen)

        painter.drawEllipse(
            10,
            10,
            WINDOW_SIZE - 20,
            WINDOW_SIZE - 20
        )

        rect = QRectF(
            20,
            20,
            WINDOW_SIZE - 40,
            WINDOW_SIZE - 40
        )

        # background ring
        bg_pen = QPen(QColor(65, 65, 65), 14)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        painter.setPen(bg_pen)
        painter.drawArc(rect, 0, 360 * 16)

        # only draw ring in timer mode
        if self.mode == "timer":
            progress = max(
                0.0,
                min(
                    1.0,
                    self.display_seconds / self.total_seconds
                )
            )

            progress_pen = QPen(QColor(GREEN), 14)
            progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)

            painter.setPen(progress_pen)

            start_angle = 90 * 16

            if progress <= 0:
                span_angle = 0
            else:
                span_angle = round(-5760 * progress)

            painter.drawArc(
                rect,
                start_angle,
                span_angle
            )

    # ------------------------
    # Utils
    # ------------------------

    def format_time(self, seconds):
        m = seconds // 60
        s = seconds % 60
        return f"{m:02}:{s:02}"

    # ------------------------
    # Dragging
    # ------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.drag_pos:
            delta = event.globalPosition().toPoint() - self.drag_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None


app = QApplication(sys.argv)
window = CircleTimer()
window.show()
sys.exit(app.exec())