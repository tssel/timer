#!/usr/bin/env python3
# smooth_circle_timer.py
#
# pip install PyQt6
# python smooth_circle_timer.py

import sys
import time
import math

from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QIntValidator
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLineEdit,
    QLabel,
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

        # high frequency UI update (smooth animation & precise time tracking)
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_frame)
        self.ui_timer.start(16)  # ~60fps

        # Shared QLineEdit Stylesheet (Kept at original 42px)
        input_style = """
            QLineEdit {
                background: transparent;
                border: none;
                color: white;
                font-size: 42px;
                font-weight: 600;
                padding: 0px;
            }
        """

        # Recalculated Geometry for 42px Text
        # Total width = 95 (mins) + 20 (colon) + 95 (secs) = 210
        # Center of 360 is 180. Start X = 180 - (210 / 2) = 75
        
        # Minutes Box
        self.mins_edit = QLineEdit(self, placeholderText="00")
        self.mins_edit.setGeometry(75, 105, 95, 60)
        self.mins_edit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.mins_edit.setReadOnly(True)
        self.mins_edit.setStyleSheet(input_style)
        self.mins_edit.setValidator(QIntValidator(0, 99))
        self.mins_edit.setMaxLength(2)
        self.mins_edit.mousePressEvent = self.start_editing
        self.mins_edit.textChanged.connect(self.auto_focus_next)
        self.mins_edit.returnPressed.connect(self.finish_editing)

        # Fixed Colon Label
        self.colon_label = QLabel(":", self)
        self.colon_label.setGeometry(170, 101, 20, 60)
        self.colon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.colon_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 42px;
                font-weight: 600;
                background: transparent;
                padding: 0px;
            }
        """)

        # Seconds Box
        self.secs_edit = QLineEdit(self, placeholderText="00")
        self.secs_edit.setGeometry(190, 105, 95, 60)
        self.secs_edit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.secs_edit.setReadOnly(True)
        self.secs_edit.setStyleSheet(input_style)
        self.secs_edit.setValidator(QIntValidator(0, 59))
        self.secs_edit.setMaxLength(2)
        self.secs_edit.mousePressEvent = self.start_editing
        self.secs_edit.returnPressed.connect(self.finish_editing)

        # Monitor focus changes to detect clicking outside the entire timer block
        QApplication.instance().focusChanged.connect(self.handle_focus_change)

        # Display initial time values
        self.update_display_text(self.remaining_seconds)

        # play/pause button (Perfect alignment directly under the large text)
        self.button = QPushButton("▶", self)
        self.button.setGeometry(130, 175, 100, 60)

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
                else:
                    self.remaining_seconds = int(self.display_seconds)

                self.update_display_text(math.ceil(self.display_seconds))

            elif self.mode == "stopwatch":
                self.stopwatch_elapsed += delta
                self.update_display_text(int(self.stopwatch_elapsed))

        else:
            self.last_tick = now

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

        self.mins_edit.setText("")
        self.secs_edit.setText("")
        
        self.mins_edit.setReadOnly(False)
        self.secs_edit.setReadOnly(False)
        
        self.mins_edit.setFocus()

    def auto_focus_next(self, text):
        if len(text) == 2 and self.editing:
            self.secs_edit.setFocus()

    def handle_focus_change(self, old_widget, new_widget):
        if not self.editing:
            return
        
        if new_widget not in (self.mins_edit, self.secs_edit):
            self.finish_editing()

    def finish_editing(self):
        if not self.editing:
            return

        try:
            m = int(self.mins_edit.text()) if self.mins_edit.text() else 0
            s = int(self.secs_edit.text()) if self.secs_edit.text() else 0
            
            if s > 59:
                s = 59

            total = m * 60 + s

            if total > 0 and self.mode == "timer":
                self.total_seconds = total
                self.remaining_seconds = total
                self.display_seconds = float(total)
        except Exception:
            pass

        self.editing = False
        
        self.mins_edit.setReadOnly(True)
        self.secs_edit.setReadOnly(True)
        
        self.mins_edit.clearFocus()
        self.secs_edit.clearFocus()

        current_val = self.remaining_seconds if self.mode == "timer" else int(self.stopwatch_elapsed)
        self.update_display_text(current_val)

    # ------------------------
    # Context menu
    # ------------------------

    def show_context_menu(self, pos):
        menu = QMenu(self)

        timer_action = menu.addAction("Timer")
        stopwatch_action = menu.addAction("Stopwatch")
        menu.addSeparator()
        exit_action = menu.addAction("Exit")

        action = menu.exec(self.mapToGlobal(pos))

        if action == timer_action:
            self.switch_to_timer()
        elif action == stopwatch_action:
            self.switch_to_stopwatch()
        elif action == exit_action:
            self.close()

    def switch_to_timer(self):
        self.mode = "timer"

        self.running = False
        self.button.setText("▶")

        self.total_seconds = 25 * 60
        self.remaining_seconds = self.total_seconds
        self.display_seconds = float(self.total_seconds)

        self.update_display_text(self.remaining_seconds)
        self.update()

    def switch_to_stopwatch(self):
        self.mode = "stopwatch"

        self.running = False
        self.button.setText("▶")

        self.stopwatch_elapsed = 0
        self.update_display_text(0)
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

    def update_display_text(self, seconds):
        if not self.editing:
            m = seconds // 60
            s = seconds % 60
            self.mins_edit.setText(f"{m:02}")
            self.secs_edit.setText(f"{s:02}")

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

    # ------------------------
    # Safe Exit Fix
    # ------------------------
    def closeEvent(self, event):
        self.ui_timer.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CircleTimer()
    window.show()
    sys.exit(app.exec())