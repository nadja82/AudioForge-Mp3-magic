"""Color themes for AudioForge."""
from __future__ import annotations

THEMES = {
    "Dark Purple": {
        "window": "#202124", "panel": "#2b2d31", "panel2": "#303134", "text": "#f1f3f4", "muted": "#b7bbc3", "border": "#3c4043", "button": "#34363b", "button_hover": "#40434a", "primary": "#7c4dff", "primary_hover": "#8e66ff", "selection": "#3f5f8f", "progress": "#7c4dff", "log": "#2b2d31",
    },
    "Invertiert": {
        "window": "#f3f2ee", "panel": "#ffffff", "panel2": "#e8e5dd", "text": "#171717", "muted": "#505050", "border": "#c8c2b8", "button": "#ece7dd", "button_hover": "#ded7ca", "primary": "#111111", "primary_hover": "#333333", "selection": "#c8d7ff", "progress": "#111111", "log": "#ffffff",
    },
    "Cyberpunk": {
        "window": "#120018", "panel": "#1f1029", "panel2": "#2b1538", "text": "#f8efff", "muted": "#d3a8ff", "border": "#663399", "button": "#2b1538", "button_hover": "#3d1e55", "primary": "#ff2bd6", "primary_hover": "#ff62e2", "selection": "#5a1a78", "progress": "#00e5ff", "log": "#1a0c22",
    },
    "Studio Grau": {
        "window": "#262626", "panel": "#333333", "panel2": "#3a3a3a", "text": "#f0f0f0", "muted": "#bdbdbd", "border": "#555555", "button": "#414141", "button_hover": "#4d4d4d", "primary": "#d7a84f", "primary_hover": "#e7bb64", "selection": "#69552e", "progress": "#d7a84f", "log": "#2e2e2e",
    },
    "Terminal Grün": {
        "window": "#071007", "panel": "#0d1a0d", "panel2": "#102410", "text": "#c8ffd0", "muted": "#88c891", "border": "#1f5f2a", "button": "#102410", "button_hover": "#173617", "primary": "#38ff6a", "primary_hover": "#72ff96", "selection": "#1f5f2a", "progress": "#38ff6a", "log": "#081408",
    },
}

DEFAULT_THEME = "Dark Purple"


def get_stylesheet(theme_name: str) -> str:
    t = THEMES.get(theme_name, THEMES[DEFAULT_THEME])
    return f"""
    QWidget {{ font-size: 13px; color: {t['text']}; }}
    QMainWindow {{ background: {t['window']}; }}
    QLabel {{ color: {t['text']}; }}
    QGroupBox {{ color: {t['text']}; border: 1px solid {t['border']}; border-radius: 10px; margin-top: 12px; padding: 10px; background: transparent; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; }}
    QTableWidget, QPlainTextEdit, QLineEdit, QComboBox {{ background: {t['panel']}; color: {t['text']}; border: 1px solid {t['border']}; border-radius: 8px; padding: 5px; }}
    QPlainTextEdit {{ background: {t['log']}; }}
    QTableWidget::item:selected {{ background: {t['selection']}; color: {t['text']}; }}
    QHeaderView::section {{ background: {t['panel2']}; color: {t['text']}; border: 0; padding: 6px; }}
    QPushButton {{ background: {t['button']}; color: {t['text']}; border: 1px solid {t['border']}; border-radius: 8px; padding: 8px 10px; }}
    QPushButton:hover {{ background: {t['button_hover']}; }}
    QPushButton:disabled {{ color: {t['muted']}; background: {t['panel2']}; }}
    QPushButton#PrimaryButton {{ background: {t['primary']}; border: 1px solid {t['primary_hover']}; font-weight: bold; }}
    QPushButton#PrimaryButton:hover {{ background: {t['primary_hover']}; }}
    QLabel#HeaderBanner {{ background: {t['panel']}; border: 1px solid {t['border']}; border-radius: 12px; color: {t['muted']}; }}
    QLabel#CoverPreview {{ background: {t['panel']}; border: 1px dashed {t['border']}; border-radius: 12px; color: {t['muted']}; }}
    QLabel#MutedLabel {{ color: {t['muted']}; }}
    QProgressBar {{ background: {t['panel']}; color: {t['text']}; border: 1px solid {t['border']}; border-radius: 8px; text-align: center; height: 18px; }}
    QProgressBar::chunk {{ background: {t['progress']}; border-radius: 8px; }}
    QCheckBox {{ color: {t['text']}; }}
    QMenuBar {{ background: {t['window']}; color: {t['text']}; }}
    QMenu {{ background: {t['panel']}; color: {t['text']}; border: 1px solid {t['border']}; }}
    QScrollArea#RightScrollArea {{ background: transparent; border: 0; }}
    """
