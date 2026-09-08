# System Colors
COLOR_BG_DARK = "#121212"
COLOR_TOPBAR = "#1E1E1E"
COLOR_PRIMARY = "#1DB954"     # Spotify Green
COLOR_TEXT_MAIN = "#FFFFFF"
COLOR_TEXT_MUTED = "#A0A0A0"

GLOBAL_STYLE = f"""
    QWidget {{
        background-color: {COLOR_BG_DARK};
        color: {COLOR_TEXT_MAIN};
        font-family: Arial, sans-serif;
    }}
"""

TOPBAR_BTN_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {COLOR_TEXT_MUTED};
        font-size: 18px;
        font-weight: bold;
        border: none;
        border-bottom: 3px solid transparent;
        padding: 10px 20px;
    }}
    QPushButton:checked {{
        color: {COLOR_TEXT_MAIN};
        border-bottom: 3px solid {COLOR_PRIMARY};
    }}
    QPushButton:hover:!checked {{
        background-color: #2A2A2A;
    }}
"""