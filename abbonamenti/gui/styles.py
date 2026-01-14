"""
Modern stylesheet and theme management for Abbonamenti GUI
"""

"""
Modern 2026 UI Theme - Comune di Scalea
Authentic institutional colors inspired by Scalea's official coat of arms,
historic center architecture, and natural Riviera dei Cedri landscape
"""

# Authentic Scalea Color Palette 2026 - Based on Official Municipal Identity
COLORS = {
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
    
    # Neutral Modern Tones
    "dark": "#263238",             # Scuro moderno
    "light": "#F3F4F6",            # Grigio chiaro 2026
    "border": "#CFD8DC",           # Bordo neutro
    "text_primary": "#263238",     # Testo primario
    "text_secondary": "#607D8B",   # Testo secondario
    "background": "#FEFEFE",       # Sfondo principale
    "card_bg": "#FFFFFF",          # Sfondo carte/widget
    "surface": "#F8F9FA",          # Superficie elementi
}

SCALEA_2026_STYLESHEET = """
    /* Main Application - Clean Modern 2026 */
    QMainWindow {
        background-color: """ + COLORS["background"] + """;
        color: """ + COLORS["text_primary"] + """;
        font-family: 'Segoe UI', 'San Francisco', 'Helvetica Neue', Arial, sans-serif;
    }

    /* Menu Bar - Minimal Clean */
    QMenuBar {
        background-color: """ + COLORS["card_bg"] + """;
        color: """ + COLORS["text_primary"] + """;
        border-bottom: 1px solid """ + COLORS["border"] + """;
        padding: 6px;
        font-size: 13px;
        font-weight: 500;
    }

    QMenuBar::item:selected {
        background-color: """ + COLORS["primary"] + """;
        color: white;
        border-radius: 4px;
        padding: 4px 8px;
    }

    QMenu {
        background-color: """ + COLORS["card_bg"] + """;
        color: """ + COLORS["text_primary"] + """;
        border: 1px solid """ + COLORS["border"] + """;
        border-radius: 6px;
        font-size: 13px;
    }

    QMenu::item:selected {
        background-color: """ + COLORS["primary"] + """;
        color: white;
        padding: 6px 12px;
        border-radius: 4px;
    }

    /* Toolbar - Clean Professional */
    QToolBar {
        background-color: """ + COLORS["surface"] + """;
        border-bottom: 1px solid """ + COLORS["border"] + """;
        padding: 8px;
        spacing: 10px;
    }

    QToolBar QLineEdit {
        border: 1px solid """ + COLORS["border"] + """;
        border-radius: 6px;
        padding: 8px;
        background-color: """ + COLORS["card_bg"] + """;
        font-size: 13px;
    }

    QToolBar QLineEdit:focus {
        border: 2px solid """ + COLORS["primary"] + """;
        background-color: """ + COLORS["card_bg"] + """;
    }

    /* Buttons - Clean Modern */
    QPushButton {
        background-color: """ + COLORS["primary"] + """;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 13px;
        min-height: 20px;
    }

    QPushButton:hover {
        background-color: """ + COLORS["primary_dark"] + """;
    }

    QPushButton:pressed {
        background-color: """ + COLORS["primary_dark"] + """;
    }

    QPushButton:disabled {
        background-color: """ + COLORS["border"] + """;
        color: """ + COLORS["text_secondary"] + """;
    }

    QPushButton#deleteBtn {
        background-color: """ + COLORS["red_institutional"] + """;
    }

    QPushButton#deleteBtn:hover {
        background-color: #D32F2F;
    }

    QPushButton#successBtn {
        background-color: """ + COLORS["cedro_green"] + """;
    }

    QPushButton#successBtn:hover {
        background-color: """ + COLORS["success"] + """;
    }

    /* Table View - Clean Data Display */
    QTableView {
        background-color: """ + COLORS["card_bg"] + """;
        alternate-background-color: """ + COLORS["surface"] + """;
        gridline-color: """ + COLORS["border"] + """;
        border: 1px solid """ + COLORS["border"] + """;
        border-radius: 6px;
        font-size: 13px;
    }

    QTableView::item {
        padding: 8px;
        border-right: 1px solid """ + COLORS["border"] + """;
    }

    QTableView::item:selected {
        background-color: """ + COLORS["primary"] + """;
        color: white;
    }

    QTableView::item:hover {
        background-color: """ + COLORS["light"] + """;
    }

    QHeaderView::section {
        background-color: """ + COLORS["surface"] + """;
        color: """ + COLORS["text_primary"] + """;
        padding: 10px;
        border: none;
        border-right: 1px solid """ + COLORS["border"] + """;
        border-bottom: 1px solid """ + COLORS["border"] + """;
        font-weight: 600;
        font-size: 12px;
    }

    QHeaderView::section:hover {
        background-color: """ + COLORS["light"] + """;
    }

    /* Scroll Bars - Minimal */
    QScrollBar:vertical {
        border: none;
        background-color: """ + COLORS["surface"] + """;
        width: 10px;
        border-radius: 5px;
    }

    QScrollBar::handle:vertical {
        background-color: """ + COLORS["border"] + """;
        border-radius: 5px;
        min-height: 20px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: """ + COLORS["text_secondary"] + """;
    }

    QScrollBar:horizontal {
        border: none;
        background-color: """ + COLORS["surface"] + """;
        height: 10px;
        border-radius: 5px;
    }

    QScrollBar::handle:horizontal {
        background-color: """ + COLORS["border"] + """;
        border-radius: 5px;
        min-width: 20px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: """ + COLORS["text_secondary"] + """;
    }

    /* Status Bar - Simple Clean */
    QStatusBar {
        background-color: """ + COLORS["surface"] + """;
        border-top: 1px solid """ + COLORS["border"] + """;
        color: """ + COLORS["text_primary"] + """;
        font-size: 12px;
    }

    /* Labels - Clean Typography */
    QLabel {
        color: """ + COLORS["text_primary"] + """;
        font-weight: 400;
    }

    /* Input Fields - Modern Clean */
    QLineEdit {
        border: 1px solid """ + COLORS["border"] + """;
        border-radius: 6px;
        padding: 8px;
        background-color: """ + COLORS["card_bg"] + """;
        font-size: 13px;
    }

    QLineEdit:focus {
        border: 2px solid """ + COLORS["primary"] + """;
        background-color: """ + COLORS["card_bg"] + """;
    }

    /* Combo Box - Clean Dropdown */
    QComboBox {
        border: 1px solid """ + COLORS["border"] + """;
        border-radius: 6px;
        padding: 6px 10px;
        background-color: """ + COLORS["card_bg"] + """;
        font-size: 13px;
    }

    QComboBox:focus {
        border: 2px solid """ + COLORS["primary"] + """;
    }

    QComboBox::drop-down {
        border: none;
        border-left: 1px solid """ + COLORS["border"] + """;
        border-top-right-radius: 6px;
        border-bottom-right-radius: 6px;
        background-color: """ + COLORS["surface"] + """;
        width: 20px;
    }

    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 4px solid """ + COLORS["text_secondary"] + """;
        margin: 0px 6px;
    }

    /* Date Edit - Clean Calendar */
    QDateEdit {
        border: 1px solid """ + COLORS["border"] + """;
        border-radius: 6px;
        padding: 6px 10px;
        background-color: """ + COLORS["card_bg"] + """;
        font-size: 13px;
    }

    QDateEdit:focus {
        border: 2px solid """ + COLORS["primary"] + """;
    }

    /* Spin Box - Clean Numeric */
    QDoubleSpinBox {
        border: 1px solid """ + COLORS["border"] + """;
        border-radius: 6px;
        padding: 6px 10px;
        background-color: """ + COLORS["card_bg"] + """;
        font-size: 13px;
    }

    QDoubleSpinBox:focus {
        border: 2px solid """ + COLORS["primary"] + """;
    }

    /* Dialog - Clean Windows */
    QDialog {
        background-color: """ + COLORS["background"] + """;
    }

    /* Message Box - Clean Notifications */
    QMessageBox {
        background-color: """ + COLORS["background"] + """;
    }

    QMessageBox QLabel {
        color: """ + COLORS["text_primary"] + """;
        font-size: 14px;
        font-weight: 400;
    }

    /* Group Box - Clean Containers */
    QGroupBox {
        border: 1px solid """ + COLORS["border"] + """;
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 12px;
        font-weight: 600;
        font-size: 13px;
        color: """ + COLORS["text_primary"] + """;
        background-color: """ + COLORS["card_bg"] + """;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 4px 8px;
        background-color: """ + COLORS["surface"] + """;
        border: 1px solid """ + COLORS["border"] + """;
        border-radius: 4px;
        color: """ + COLORS["text_primary"] + """;
        font-weight: 600;
    }

    /* Tab Widget - Clean Navigation */
    QTabWidget::pane {
        border: 1px solid """ + COLORS["border"] + """;
        background-color: """ + COLORS["card_bg"] + """;
        border-radius: 6px;
    }

    QTabBar::tab {
        background-color: """ + COLORS["surface"] + """;
        color: """ + COLORS["text_primary"] + """;
        padding: 10px 20px;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-weight: 500;
        font-size: 13px;
        border: 1px solid """ + COLORS["border"] + """;
        border-bottom: none;
    }

    QTabBar::tab:selected {
        background-color: """ + COLORS["primary"] + """;
        color: white;
    }

    QTabBar::tab:hover:!selected {
        background-color: """ + COLORS["light"] + """;
    }

    /* Progress Dialog - Clean Loading */
    QProgressDialog {
        background-color: """ + COLORS["card_bg"] + """;
        border: 1px solid """ + COLORS["border"] + """;
        border-radius: 8px;
    }

    QProgressBar {
        border: 1px solid """ + COLORS["border"] + """;
        border-radius: 4px;
        background-color: """ + COLORS["surface"] + """;
        text-align: center;
    }

    QProgressBar::chunk {
        background-color: """ + COLORS["primary"] + """;
        border-radius: 3px;
    }
"""

def get_stylesheet() -> str:
    """Get the authentic 2026 Scalea municipal stylesheet"""
    return SCALEA_2026_STYLESHEET

def get_color(name: str) -> str:
    """Get a color by name"""
    return COLORS.get(name, "#000000")
