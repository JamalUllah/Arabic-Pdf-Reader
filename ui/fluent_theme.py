COLORS = {
    "primary": "#0A84FF",
    "primary_hover": "#0070E0",
    "primary_pressed": "#0060C0",
    "background": "#FFFFFF",
    "sidebar": "#F5F5F7",
    "canvas": "#F0F0F2",
    "border": "#E5E5E5",
    "text_primary": "#202124",
    "text_secondary": "#5F6368",
    "hover_bg": "#E8F0FE",
    "selected_bg": "#0A84FF",
    "selected_text": "#FFFFFF",
}

FONT_FAMILY = '"Segoe UI", "Segoe UI Variable", sans-serif'


def build_stylesheet() -> str:
    c = COLORS
    return f"""
    * {{
        font-family: {FONT_FAMILY};
        font-size: 13px;
        color: {c["text_primary"]};
    }}
    QMainWindow {{
        background: {c["background"]};
    }}
    QWidget#AppHeader {{
        background: {c["background"]};
        border-bottom: 1px solid {c["border"]};
    }}
    QWidget#PrimaryToolbar {{
        background: {c["background"]};
        border-bottom: 1px solid {c["border"]};
    }}
    QWidget#SidebarPanel {{
        background: {c["sidebar"]};
        border-right: 1px solid {c["border"]};
    }}
    QWidget#DocumentViewport {{
        background: {c["canvas"]};
    }}
    QWidget#EmptyState {{
        background: {c["canvas"]};
    }}
    QPushButton {{
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 6px 10px;
        color: {c["text_primary"]};
    }}
    QPushButton:hover {{
        background: {c["hover_bg"]};
    }}
    QPushButton:pressed {{
        background: #D2E3FC;
    }}
    QPushButton:checked, QPushButton#ActiveTool {{
        background: {c["primary"]};
        color: {c["selected_text"]};
    }}
    QPushButton#WindowControl:hover {{
        background: {c["hover_bg"]};
    }}
    QPushButton#WindowClose:hover {{
        background: #E81123;
        color: white;
    }}
    QPushButton#PrimaryButton {{
        background: {c["primary"]};
        color: white;
        font-weight: 600;
        padding: 10px 24px;
        min-width: 120px;
    }}
    QPushButton#PrimaryButton:hover {{
        background: {c["primary_hover"]};
    }}
    QPushButton#BackButton {{
        background: {c["primary"]};
        color: white;
        border-radius: 6px;
        min-width: 36px;
        max-width: 36px;
        min-height: 36px;
        max-height: 36px;
        padding: 0;
        font-size: 16px;
    }}
    QLineEdit, QSpinBox {{
        background: {c["background"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 4px 8px;
        min-height: 28px;
    }}
    QLineEdit:focus {{
        border: 1px solid {c["primary"]};
    }}
    QTabWidget::pane {{
        border: none;
        background: {c["sidebar"]};
    }}
    QTabBar::tab {{
        background: transparent;
        color: {c["text_secondary"]};
        padding: 10px 16px;
        min-height: 40px;
        border: none;
        border-bottom: 2px solid transparent;
    }}
    QTabBar::tab:selected {{
        color: {c["text_primary"]};
        border-bottom: 2px solid {c["primary"]};
        font-weight: 600;
    }}
    QTabBar::tab:hover:!selected {{
        background: {c["hover_bg"]};
    }}
    QListWidget {{
        background: transparent;
        border: none;
        outline: none;
    }}
    QListWidget::item {{
        padding: 10px 12px;
        border-radius: 6px;
        margin: 2px 8px;
        color: {c["text_primary"]};
    }}
    QListWidget::item:hover {{
        background: {c["hover_bg"]};
    }}
    QListWidget::item:selected {{
        background: {c["selected_bg"]};
        color: {c["selected_text"]};
    }}
    QDialog {{
        background: {c["background"]};
        border: 1px solid {c["border"]};
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QFrame#ToolbarDivider {{
        background: {c["border"]};
        max-width: 1px;
        min-width: 1px;
        margin: 8px 4px;
    }}
    QStatusBar {{
        background: {c["background"]};
        border-top: 1px solid {c["border"]};
        color: {c["text_secondary"]};
        font-size: 12px;
    }}
    QMenu {{
        background: {c["background"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 8px 24px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background: {c["hover_bg"]};
    }}
    QLabel#HeaderTitle {{
        font-size: 14px;
        color: {c["text_primary"]};
    }}
    QLabel#HeaderDot {{
        color: {c["text_secondary"]};
    }}
    QLabel#HeaderFilename {{
        font-size: 14px;
        color: {c["text_secondary"]};
    }}
    QLabel#SidebarSectionTitle {{
        font-size: 13px;
        font-weight: 600;
        color: {c["text_primary"]};
        padding: 8px 12px;
    }}
    QLabel#EmptyTitle {{
        font-size: 18px;
        font-weight: 600;
        color: {c["text_primary"]};
    }}
    QLabel#EmptySubtitle {{
        font-size: 13px;
        color: {c["text_secondary"]};
    }}
    QLabel#ZoomLabel {{
        min-width: 48px;
        qproperty-alignment: AlignCenter;
        color: {c["text_primary"]};
    }}
    QFormLayout > QLabel {{
        color: {c["text_primary"]};
        padding-top: 4px;
    }}
    """
