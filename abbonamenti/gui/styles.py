"""
Modern stylesheet and theme management for Abbonamenti GUI.
Adds Windows 11-aware light/dark selection using the current Qt palette.
"""

from __future__ import annotations

from string import Template
from typing import Dict

from PyQt5.QtGui import QGuiApplication, QPalette


# Authentic Scalea Color Palette 2026 - Based on Official Municipal Identity
BASE_COLORS: Dict[str, str] = {
    # Institutional Colors (Coat of Arms)
    "primary": "#1565C0",          # Azzurro istituzionale (institutional azure)
    "primary_dark": "#0D47A1",     # Azzurro profondo (deep azure)
    "gold": "#FFB300",             # Oro stemma (coat gold)
    "red_institutional": "#C62828", # Rosso stemma (coat red)

    # Historic Center Colors
    "stone_gray": "#546E7A",       # Pietra a vista (exposed stone)
    "anthracite": "#37474F",       # Grigio antracite (anthracite gray)
    "terracotta": "#D7CCC8",       # Terracotta pastello
    "off_white": "#FAFAFA",        # Bianco sporco
    "ochre": "#FFE0B2",           # Ocra chiaro
    "pale_pink": "#F8BBD9",       # Rosa tenue

    # Natural Landscape Colors
    "turquoise": "#00ACC1",        # Turchese Riviera dei Cedri
    "cobalt_blue": "#1976D2",      # Blu cobalto mare
    "cedro_green": "#66BB6A",      # Verde cedro brillante
    "sunrise_gold": "#FFC107",     # Oro alba/tramonto
    "sunset_orange": "#FF8A65",    # Arancio tramonto

    # Modern 2026 UI Colors
    "success": "#66BB6A",          # Verde cedro (success states)
    "warning": "#FFB300",          # Oro (warning states)
    "danger": "#C62828",           # Rosso istituzionale (danger states)
    "info": "#00ACC1",             # Turchese (info states)

    # Neutral Modern Tones (light defaults)
    "dark": "#263238",             # Scuro moderno
    "light": "#F3F4F6",            # Grigio chiaro 2026
    "border": "#CFD8DC",          # Bordo neutro
    "text_primary": "#263238",     # Testo primario
    "text_secondary": "#607D8B",   # Testo secondario
    "background": "#FEFEFE",       # Sfondo principale
    "card_bg": "#FFFFFF",          # Sfondo carte/widget
    "surface": "#F8F9FA",          # Superficie elementi
}


STYLE_TEMPLATE = Template(
    r"""
    /* Main Application - Clean Modern 2026 */
    QMainWindow {
        background-color: $background;
        color: $text_primary;
        font-family: 'Segoe UI', 'San Francisco', 'Helvetica Neue', Arial, sans-serif;
    }

    /* Force readable defaults on all widgets (avoids Windows dark-mode white-on-white) */
    QWidget {
        color: $text_primary;
        background-color: $background;
    }

    /* Menu Bar - Higher Contrast */
    QMenuBar {
        background-color: $surface;
        color: $text_primary;
        border-bottom: 1px solid $border;
        padding: 6px 10px;
        font-size: 13px;
        font-weight: 600;
    }

    QMenuBar::item {
        padding: 6px 10px;
        color: $text_primary;
        background: transparent;
    }

    QMenuBar::item:selected,
    QMenuBar::item:pressed {
        background-color: $primary;
        color: white;
        border-radius: 5px;
    }

    QMenu {
        background-color: $card_bg;
        color: $text_primary;
        border: 1px solid $border;
        border-radius: 6px;
        font-size: 13px;
    }

    QMenu::item:selected {
        background-color: $primary;
        color: white;
        padding: 6px 12px;
        border-radius: 4px;
    }

    /* Toolbar - Clean Professional */
    QToolBar {
        background-color: $surface;
        color: $text_primary;
        border-bottom: 1px solid $border;
        padding: 8px 12px;
        spacing: 12px;
    }

    /* Ensure toolbar child widgets stay visually on the same bar */
    QToolBar QWidget {
        background: transparent;
    }

    QToolBar QLabel,
    QToolBar QLineEdit,
    QToolBar QPushButton {
        color: $text_primary;
    }

    QToolBar::separator {
        background: $border;
        width: 1px;
        margin: 0 8px;
    }

    QToolButton {
        background: transparent;
        color: $text_primary;
        padding: 6px 10px;
        border-radius: 5px;
    }

    QToolButton:hover {
        background-color: $surface;
    }

    QToolBar QLineEdit {
        border: 1px solid $border;
        border-radius: 6px;
        padding: 8px;
        background-color: $surface;
        font-size: 13px;
    }

    QToolBar QLineEdit:focus {
        border: 2px solid $primary;
        background-color: $surface;
    }

    /* Buttons - Clean Modern */
    QPushButton {
        background-color: $primary;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 13px;
        min-height: 20px;
    }

    QPushButton:hover {
        background-color: $primary_dark;
    }

    QPushButton:pressed {
        background-color: $primary_dark;
    }

    QPushButton:disabled {
        background-color: $border;
        color: $text_secondary;
    }

    QPushButton#deleteBtn {
        background-color: $red_institutional;
    }

    QPushButton#deleteBtn:hover {
        background-color: #D32F2F;
    }

    QPushButton#successBtn {
        background-color: $cedro_green;
    }

    QPushButton#successBtn:hover {
        background-color: $success;
    }

    /* Table View - Clean Data Display */
    QTableView {
        background-color: $card_bg;
        alternate-background-color: $surface;
        gridline-color: $border;
        border: 1px solid $border;
        border-radius: 6px;
        font-size: 13px;
        color: $text_primary;
    }

    QTableView::item {
        padding: 8px;
        border-right: 1px solid $border;
        color: $text_primary;
    }

    QTableView::item:selected {
        background-color: $primary;
        color: white;
    }

    QTableView::item:hover {
        background-color: $light;
    }

    QHeaderView::section {
        background-color: $surface;
        color: $text_primary;
        padding: 10px;
        border: none;
        border-right: 1px solid $border;
        border-bottom: 1px solid $border;
        font-weight: 600;
        font-size: 12px;
    }

    QHeaderView::section:hover {
        background-color: $light;
    }

    /* Scroll Bars - Minimal */
    QScrollBar:vertical {
        border: none;
        background-color: $surface;
        width: 10px;
        border-radius: 5px;
    }

    QScrollBar::handle:vertical {
        background-color: $border;
        border-radius: 5px;
        min-height: 20px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: $text_secondary;
    }

    QScrollBar:horizontal {
        border: none;
        background-color: $surface;
        height: 10px;
        border-radius: 5px;
    }

    QScrollBar::handle:horizontal {
        background-color: $border;
        border-radius: 5px;
        min-width: 20px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: $text_secondary;
    }

    /* Status Bar - Simple Clean */
    QStatusBar {
        background-color: $surface;
        border-top: 1px solid $border;
        color: $text_primary;
        font-size: 12px;
    }

    /* Labels - Clean Typography */
    QLabel {
        color: $text_primary;
        font-weight: 400;
    }

    /* Input Fields - Modern Clean */
    QLineEdit {
        border: 1px solid $border;
        border-radius: 6px;
        padding: 8px;
        background-color: $card_bg;
        font-size: 13px;
        color: $text_primary;
    }

    QLineEdit:focus {
        border: 2px solid $primary;
        background-color: $card_bg;
        color: $text_primary;
    }

    QLineEdit::placeholder {
        color: $text_secondary;
    }

    /* Combo Box - Clean Dropdown */
    QComboBox {
        border: 1px solid $border;
        border-radius: 6px;
        padding: 6px 10px;
        background-color: $card_bg;
        font-size: 13px;
        color: $text_primary;
    }

    QComboBox:focus {
        border: 2px solid $primary;
        color: $text_primary;
    }

    QComboBox::drop-down {
        border: none;
        border-left: 1px solid $border;
        border-top-right-radius: 6px;
        border-bottom-right-radius: 6px;
        background-color: $surface;
        width: 20px;
    }

    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 4px solid $text_secondary;
        margin: 0px 6px;
    }

    /* Date Edit - Clean Calendar */
    QDateEdit {
        border: 1px solid $border;
        border-radius: 6px;
        padding: 6px 10px;
        background-color: $card_bg;
        font-size: 13px;
        color: $text_primary;
    }

    QDateEdit:focus {
        border: 2px solid $primary;
        color: $text_primary;
    }

    /* Spin Box - Clean Numeric */
    QDoubleSpinBox {
        border: 1px solid $border;
        border-radius: 6px;
        padding: 6px 10px;
        background-color: $card_bg;
        font-size: 13px;
        color: $text_primary;
    }

    QDoubleSpinBox:focus {
        border: 2px solid $primary;
        color: $text_primary;
    }

    /* Dialog - Clean Windows */
    QDialog {
        background-color: $background;
    }

    /* Message Box - Clean Notifications */
    QMessageBox {
        background-color: $background;
    }

    QMessageBox QLabel {
        color: $text_primary;
        font-size: 14px;
        font-weight: 400;
    }

    /* Group Box - Clean Containers */
    QGroupBox {
        border: 1px solid $border;
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 12px;
        font-weight: 600;
        font-size: 13px;
        color: $text_primary;
        background-color: $card_bg;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 4px 8px;
        background-color: $surface;
        border: 1px solid $border;
        border-radius: 4px;
        color: $text_primary;
        font-weight: 600;
    }

    /* Tab Widget - Clean Navigation */
    QTabWidget::pane {
        border: 1px solid $border;
        background-color: $card_bg;
        border-radius: 6px;
    }

    QTabBar::tab {
        background-color: $surface;
        color: $text_primary;
        padding: 10px 20px;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-weight: 500;
        font-size: 13px;
        border: 1px solid $border;
        border-bottom: none;
    }

    QTabBar::tab:selected {
        background-color: $primary;
        color: white;
    }

    QTabBar::tab:hover:!selected {
        background-color: $light;
    }

    /* Progress Dialog - Clean Loading */
    QProgressDialog {
        background-color: $card_bg;
        border: 1px solid $border;
        border-radius: 8px;
    }

    QProgressBar {
        border: 1px solid $border;
        border-radius: 4px;
        background-color: $surface;
        text-align: center;
    }

    QProgressBar::chunk {
        background-color: $primary;
        border-radius: 3px;
    }
"""
)


def _detect_system_theme() -> str:
    """Return 'dark' or 'light' based on the current Qt palette (Windows 11 aware)."""

    app = QGuiApplication.instance()
    if app is None:
        return "light"

    palette = app.palette()
    if palette is None:
        return "light"

    window_color = palette.color(QPalette.ColorRole.Window)
    # Qt returns 0-255; normalize via lightnessF (0.0 = black, 1.0 = white)
    try:
        lightness = window_color.lightnessF()
    except Exception:
        lightness = window_color.lightness() / 255.0

    return "dark" if lightness < 0.45 else "light"


def _resolve_colors() -> Dict[str, str]:
    colors = dict(BASE_COLORS)
    if _detect_system_theme() == "dark":
        colors.update(
            {
                "background": "#1f1f1f",
                "surface": "#262626",
                "card_bg": "#1f1f1f",
                "light": "#2e2e2e",
                "border": "#3a3a3a",
                "text_primary": "#f2f2f2",
                "text_secondary": "#c8c8c8",
            }
        )
    return colors


def get_stylesheet() -> str:
    """Return the stylesheet adapted to the current system (Windows 11) theme."""

    colors = _resolve_colors()
    return STYLE_TEMPLATE.substitute(colors)


def get_color(name: str) -> str:
    """Get a color by name, aligned to the current theme."""

    return _resolve_colors().get(name, "#000000")
