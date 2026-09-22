# System Colors — Pure Black & BMW M-Red Only
COLOR_BG_DARK = "#000000"
COLOR_TOPBAR = "#000000"
COLOR_PRIMARY = "#E7222E"      # BMW Red
COLOR_TEXT_MAIN = "#E7222E"
COLOR_TEXT_MUTED = "#E7222E"

GLOBAL_STYLE = f"""
    QWidget {{
        background-color: {COLOR_BG_DARK};
        color: {COLOR_PRIMARY};
        font-family: Arial, sans-serif;
    }}

    QLabel {{
        background: transparent;
        background-color: transparent;
        color: {COLOR_PRIMARY};
    }}
"""

TOPBAR_BTN_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {COLOR_PRIMARY};
        font-size: 18px;
        font-weight: bold;
        border: none;
        border-bottom: 3px solid transparent;
        padding: 10px 20px;
    }}
    QPushButton:checked {{
        color: {COLOR_BG_DARK};
        background-color: {COLOR_PRIMARY};
        border-bottom: 3px solid {COLOR_PRIMARY};
    }}
    QPushButton:hover:!checked {{
        background-color: {COLOR_BG_DARK};
        border: 1px solid {COLOR_PRIMARY};
    }}
"""