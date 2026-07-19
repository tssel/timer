#!/usr/bin/env python3
# smooth_circle_timer.py
#
# pip install PyQt6
# python smooth_circle_timer.py

import sys
import time
import math
import os

from PyQt6.QtCore import Qt, QTimer, QRectF, QUrl
from PyQt6.QtGui import QColor, QPainter, QPen, QIntValidator
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLineEdit,
    QLabel,
    QMenu,
    QFileDialog,
)
from PyQt6.QtMultimedia import QSoundEffect

GREEN = "#26ba35"


class CircleTimer(QWidget):
    def __init__(self):
        super().__init__()

        # Window Size configuration
        self.window_size = 360  # Initial medium size

        # Timer state
        self.total_seconds = 25 * 60
        self.remaining_seconds = self.total_seconds

        self.running = False
        self.editing = False
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

        # Initialize Widgets
        self.mins_edit = QLineEdit(self, placeholderText="00")
        self.mins_edit.setReadOnly(True)
        self.mins_edit.setValidator(QIntValidator(0, 99))
        self.mins_edit.setMaxLength(2)
        self.mins_edit.mousePressEvent = self.start_editing
        self.mins_edit.textChanged.connect(self.auto_focus_next)
        self.mins_edit.returnPressed.connect(self.finish_editing)

        self.colon_label = QLabel(":", self)

        self.secs_edit = QLineEdit(self, placeholderText="00")
        self.secs_edit.setReadOnly(True)
        self.secs_edit.setValidator(QIntValidator(0, 59))
        self.secs_edit.setMaxLength(2)
        self.secs_edit.mousePressEvent = self.start_editing
        self.secs_edit.returnPressed.connect(self.finish_editing)

        self.button = QPushButton("▶", self)
        self.button.clicked.connect(self.toggle_timer)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Apply layout geometry and font scaling mapping
        self.update_layout_geometry()

        # Monitor focus changes to detect clicking outside the entire timer block
        QApplication.instance().focusChanged.connect(self.handle_focus_change)

        # Display initial time values
        self.update_display_text(self.remaining_seconds)

        # right click menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # dragging
        self.drag_pos = None

    def update_layout_geometry(self):
        """Calculates widget layouts and dynamic font sizing centered on window size"""
        self.setFixedSize(self.window_size, self.window_size)
        center = self.window_size // 2

        # Scale down fonts on the small window setting
        if self.window_size == 280:
            font_size = 32
            span_half_width = 80
            input_w = 75
            colon_w = 10
            text_y_offset = 60
            btn_y_offset = 0
        else:
            font_size = 42
            span_half_width = 105
            input_w = 95
            colon_w = 20
            text_y_offset = 75
            btn_y_offset = 5

        # Build dynamic sheets
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
        label_style = f"""
            QLabel {{
                color: white;
                font-size: {font_size}px;
                font-weight: 600;
                background: transparent;
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

        self.mins_edit.setStyleSheet(input_style)
        self.secs_edit.setStyleSheet(input_style)
        self.colon_label.setStyleSheet(label_style)
        self.button.setStyleSheet(btn_style)

        # Horizontal coordinates using dynamic component widths
        start_x = center - span_half_width
        text_y = center - text_y_offset
        btn_y = center - btn_y_offset

        # Apply spatial coordinates
        self.mins_edit.setGeometry(start_x, text_y, input_w, 60)
        self.mins_edit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.colon_label.setGeometry(start_x + input_w, text_y - 4, colon_w, 60)
        self.colon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.secs_edit.setGeometry(start_x + input_w + colon_w, text_y, input_w, 60)
        self.secs_edit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.button.setGeometry(center - 50, btn_y, 100, 60)
        self.update()

    # ------------------------
    # Timer logic
    # ------------------------

    def toggle_timer(self):
        if self.editing:
            return
        # Stop sound playback if button clicked while ringing
        if self.sound_effect.isPlaying():
            self.sound_effect.stop()
            self.button.setText("▶")
            return

        self.running = not self.running
        self.button.setText("⏸" if self.running else "▶")
        self.last_tick = time.time()

    def play_alarm(self):
        """Triggers alarm logic handling mute, custom tracks, and default track fallbacks."""
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
            # Final hardware/OS fallback if track doesn't exist
            QApplication.beep()

    # ------------------------
    # Smooth animation frame
    # ------------------------

    def update_frame(self):
        now = time.time()
        
        # Override standard button text if the alarm is currently ringing
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
        
        # Audio Configuration Submenu
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
        
        # Resize Submenu
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
        """Opens file selection dialog explicitly filtered only for .wav formats"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Alarm Sound", 
            "", 
            "Audio Files (*.wav)"
        )
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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # background circle
        painter.setBrush(QColor(28, 28, 28, 235))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(10, 10, self.window_size - 20, self.window_size - 20)

        rect = QRectF(20, 20, self.window_size - 40, self.window_size - 40)

        # background ring
        bg_pen = QPen(QColor(65, 65, 65), 14)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 0, 360 * 16)

        # only draw ring in timer mode
        if self.mode == "timer":
            progress = max(0.0, min(1.0, self.display_seconds / self.total_seconds))
            progress_pen = QPen(QColor(GREEN), 14)
            progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(progress_pen)

            start_angle = 90 * 16
            span_angle = 0 if progress <= 0 else round(-5760 * progress)
            painter.drawArc(rect, start_angle, span_angle)

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
        if self.sound_effect.isPlaying():
            self.sound_effect.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CircleTimer()
    window.show()
    sys.exit(app.exec())