#!/usr/bin/env python3
# smooth_circle_timer.py
#
# pip install PyQt6
# python smooth_circle_timer.py

import sys
import time
import math
import os

from PyQt6.QtCore import Qt, QTimer, QRectF, QUrl, QEvent
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLineEdit,
    QMenu,
    QFileDialog,
)
from PyQt6.QtMultimedia import QSoundEffect

GREEN = "#26ba35"


class CircleTimer(QWidget):
    def __init__(self):
        super().__init__()

        # Window Size configuration
        self.window_size = 360  # Initial default size matching old layout

        # Timer state
        self.total_seconds = 25 * 60
        self.remaining_seconds = self.total_seconds

        self.running = False
        self.editing = False
        self.input_digits = ""  # Track typed digits during edit mode
        self.mode = "timer"  # timer or stopwatch
        self.stopwatch_elapsed = 0.0

        # Audio setup using native QSoundEffect
        self.sound_effect = QSoundEffect(self)
        self.sound_effect.setLoopCount(3) 
        
        # Audio state flags: "muted", "custom", "default_tone"
        self.sound_state = "muted" 
        self.custom_wav_path = None
        
        # Automatic detection of default local wav file
        self.default_wav_path = os.path.join(os.path.dirname(__file__), "default_tone.wav")

        # smooth timing
        self.last_tick = time.time()
        self.display_seconds = float(self.remaining_seconds)

        self.setWindowTitle("Smooth Circle Timer")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # high frequency UI update (smooth animation & precise time tracking)
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_frame)
        self.ui_timer.start(16)  # ~60fps

        # Initialize single QLineEdit
        self.time_edit = QLineEdit(self)
        self.time_edit.setReadOnly(True)
        self.time_edit.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.time_edit.installEventFilter(self) # Catch keyboard and click entries natively

        self.button = QPushButton("▶", self)
        self.button.clicked.connect(self.toggle_timer)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Apply layout geometry and font scaling mapping
        self.update_layout_geometry()

        # Display initial time values
        self.update_display_text(self.remaining_seconds)

        # right click menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # dragging
        self.drag_pos = None

    def update_layout_geometry(self):
        """Calculates widget layouts and dynamic fonts using the old code baseline layout"""
        self.setFixedSize(self.window_size, self.window_size)
        
        # Proportional scale factor relative to standard size 360
        scale = self.window_size / 360.0

        tx = int(70 * scale)
        ty = int(105 * scale)
        tw = int(220 * scale)
        th = int(60 * scale)
        font_size = int(42 * scale)

        bx = int(130 * scale)
        by = int(170 * scale)
        bw = int(100 * scale)
        bh = int(100 * scale)

        input_style = f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: white;
                font-size: {font_size}px;
                font-weight: 600;
                padding: 0px;
            }}
        """
        btn_style = f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: white;
                font-size: {font_size}px;
            }}
            QPushButton:hover {{
                color: rgb(220,220,220);
            }}
        """

        self.time_edit.setStyleSheet(input_style)
        self.button.setStyleSheet(btn_style)

        self.time_edit.setGeometry(tx, ty, tw, th)
        self.time_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.button.setGeometry(bx, by, bw, bh)
        self.update()

    # ------------------------
    # Timer logic
    # ------------------------

    def toggle_timer(self):
        if self.sound_effect.isPlaying():
            self.sound_effect.stop()
            self.button.setText("▶")
            return

        if self.editing:
            self.finish_editing()
            if self.total_seconds > 0 and self.mode == "timer":
                self.running = True
                self.button.setText("⏸")
                self.last_tick = time.time()
            return

        self.running = not self.running
        self.button.setText("⏸" if self.running else "▶")
        self.last_tick = time.time()

    def play_alarm(self):
        if self.sound_state == "muted":
            return

        active_track = None
        if self.sound_state == "custom":
            active_track = self.custom_wav_path
        elif self.sound_state == "default_tone":
            active_track = self.default_wav_path

        if active_track and os.path.exists(active_track):
            self.sound_effect.setSource(QUrl.fromLocalFile(active_track))
            self.sound_effect.play()
        else:
            QApplication.beep()

    # ------------------------
    # Smooth animation frame
    # ------------------------

    def update_frame(self):
        now = time.time()
        
        if self.sound_effect.isPlaying():
            self.button.setText("✓")
        elif not self.editing:
            self.button.setText("⏸" if self.running else "▶")

        if self.running and not self.editing:
            delta = now - self.last_tick
            self.last_tick = now

            if self.mode == "timer":
                self.display_seconds -= delta
                if self.display_seconds <= 0:
                    self.display_seconds = 0
                    self.remaining_seconds = 0
                    self.running = False
                    self.play_alarm()
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
    # Custom Centered Digit Entry Logic
    # ------------------------

    def start_editing(self, event):
        if self.editing:
            return
        self.editing = True
        self.running = False
        self.button.setText("▶")
        self.input_digits = ""
        self.time_edit.setReadOnly(False)
        self.render_edit_display()

    def eventFilter(self, obj, event):
        if obj == self.time_edit:
            # Native click filtering handling replacement
            if event.type() == QEvent.Type.MouseButtonPress:
                self.start_editing(event)
                return True

            # Keystroke intercept pipeline
            if self.editing and event.type() == QEvent.Type.KeyPress:
                key = event.key()
                # Safely extract the integer value whether 'key' is an int or an Enum member
                key_val = key.value if hasattr(key, 'value') else key

                # Compare via explicit integer values to prevent cross-type crashes
                if Qt.Key.Key_0.value <= key_val <= Qt.Key.Key_9.value:
                    if len(self.input_digits) < 6:
                        self.input_digits += event.text()
                        self.render_edit_display()
                    return True

                elif key_val == Qt.Key.Key_Backspace.value:
                    if len(self.input_digits) > 0:
                        self.input_digits = self.input_digits[:-1]
                        self.render_edit_display()
                    return True

                elif key_val in (Qt.Key.Key_Return.value, Qt.Key.Key_Enter.value):
                    self.finish_editing()
                    return True

                elif key_val == Qt.Key.Key_Escape.value:
                    self.editing = False
                    self.time_edit.setReadOnly(True)
                    self.time_edit.clearFocus()
                    current_val = self.remaining_seconds if self.mode == "timer" else int(self.stopwatch_elapsed)
                    self.update_display_text(current_val)
                    return True

                # Swallow arbitrary text adjustments to protect the layout structure
                return True

        return super().eventFilter(obj, event)

    def render_edit_display(self):
        """Pads and constructs standard 00:00:00 view centered accurately"""
        padded = self.input_digits.zfill(6)
        formatted = f"{padded[0:2]}:{padded[2:4]}:{padded[4:6]}"
        
        self.time_edit.setText(formatted)
        self.time_edit.setCursorPosition(len(formatted))

    def finish_editing(self):
        if not self.editing:
            return
            
        self.editing = False
        self.time_edit.setReadOnly(True)
        self.time_edit.clearFocus()

        if self.input_digits:
            padded = self.input_digits.zfill(6)
            h = int(padded[0:2])
            m = int(padded[2:4])
            s = int(padded[4:6])
            
            total = h * 3600 + m * 60 + s
            if total > 0 and self.mode == "timer":
                self.total_seconds = total
                self.remaining_seconds = total
                self.display_seconds = float(total)

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
        sound_menu = menu.addMenu("Sound Options")
        mute_action = sound_menu.addAction("Muted")
        mute_action.setCheckable(True)
        mute_action.setChecked(self.sound_state == "muted")
        default_action = sound_menu.addAction("Default Tone")
        default_action.setCheckable(True)
        default_action.setChecked(self.sound_state == "default_tone")
        sound_menu.addSeparator()
        custom_sound_file_action = sound_menu.addAction("Choose Custom Sound File (.wav)...")
        
        menu.addSeparator()
        resize_menu = menu.addMenu("Resize Window")
        small_action = resize_menu.addAction("Small (280x280)")
        medium_action = resize_menu.addAction("Medium (360x360)")
        large_action = resize_menu.addAction("Large (440x440)")
        
        menu.addSeparator()
        exit_action = menu.addAction("Exit")

        action = menu.exec(self.mapToGlobal(pos))

        if action == timer_action:
            self.switch_to_timer()
        elif action == stopwatch_action:
            self.switch_to_stopwatch()
        elif action == mute_action:
            self.sound_state = "muted"
        elif action == default_action:
            self.sound_state = "default_tone"
        elif action == custom_sound_file_action:
            self.select_custom_sound()
            if self.custom_wav_path:
                self.sound_state = "custom"
        elif action == small_action:
            self.window_size = 280
            self.update_layout_geometry()
        elif action == medium_action:
            self.window_size = 360
            self.update_layout_geometry()
        elif action == large_action:
            self.window_size = 440
            self.update_layout_geometry()
        elif action == exit_action:
            self.close()

    def select_custom_sound(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Alarm Sound", "", "Audio Files (*.wav)")
        if file_path:
            self.custom_wav_path = file_path

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
        # Context manager protects painter life cycle pipelines
        with QPainter(self) as painter:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            painter.setBrush(QColor(28, 28, 28, 235))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(10, 10, self.window_size - 20, self.window_size - 20)

            rect = QRectF(20, 20, self.window_size - 40, self.window_size - 40)

            bg_pen = QPen(QColor(65, 65, 65), 14)
            bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(bg_pen)
            painter.drawArc(rect, 0, 360 * 16)

            if self.mode == "timer":
                progress = max(0.0, min(1.0, self.display_seconds / self.total_seconds))
                progress_pen = QPen(QColor(GREEN), 14)
                progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(progress_pen)

                start_angle = 90 * 16
                span_angle = 0 if progress <= 0 else round(-5760 * progress)
                painter.drawArc(rect, start_angle, span_angle)

    # ------------------------
    # Dynamic Trimming Logic
    # ------------------------

    def update_display_text(self, seconds):
        """Converts raw seconds into a cleanly formatted string without unneeded zeros"""
        if not self.editing:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = seconds % 60
            
            if h > 0:
                display_str = f"{h}:{m:02}:{s:02}"
            elif m > 0:
                display_str = f"{m}:{s:02}"
            else:
                display_str = f"{s}"
                
            self.time_edit.setText(display_str)

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

    def closeEvent(self, event):
        self.ui_timer.stop()
        if self.sound_effect.isPlaying():
            self.sound_effect.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CircleTimer()
    window.show()
    sys.exit(app.exec())