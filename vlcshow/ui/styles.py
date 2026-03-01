"""Global Qt stylesheet — GitHub-dark-inspired palette, touch-friendly sizing.

Colours
-------
Background    #0d1117   (deepest surface)
Surface       #161b22   (panels, cards)
Border        #30363d
Primary       #1f6feb   (blue – interactive elements)
Primary light #58a6ff
Text primary  #e6edf3
Text muted    #8b949e
"""

APP_STYLESHEET = """

/* ═══════════════════════════════════════════════════════════
   Base
═══════════════════════════════════════════════════════════ */

* {
    font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
    font-size: 14px;
    outline: none;
    box-sizing: border-box;
}

QMainWindow,
QWidget {
    background-color: #0d1117;
    color: #e6edf3;
}

QFrame {
    background-color: transparent;
}

/* ═══════════════════════════════════════════════════════════
   Buttons  (touch target ≥ 52 px tall via min-height)
═══════════════════════════════════════════════════════════ */

QPushButton {
    background-color: #21262d;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    min-height: 52px;
    min-width: 80px;
    padding: 8px 18px;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
}

QPushButton:pressed {
    background-color: #161b22;
    border-color: #58a6ff;
}

QPushButton:disabled {
    background-color: #161b22;
    color: #484f58;
    border-color: #21262d;
}

/* Accent (primary action) variant – set via setProperty("accent", True) */
QPushButton[accent="true"] {
    background-color: #1f6feb;
    border-color: #388bfd;
    color: #ffffff;
}

QPushButton[accent="true"]:hover {
    background-color: #388bfd;
}

QPushButton[accent="true"]:pressed {
    background-color: #1158c7;
}

/* ═══════════════════════════════════════════════════════════
   Sliders — large handle, easy to grab on touch
═══════════════════════════════════════════════════════════ */

QSlider::groove:horizontal {
    background: #21262d;
    height: 6px;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #1f6feb;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #58a6ff;
    width: 22px;
    height: 22px;
    border-radius: 11px;
    margin: -8px 0;
    border: 2px solid #1f6feb;
}

QSlider::handle:horizontal:hover {
    background: #79c0ff;
    border-color: #388bfd;
}

QSlider::handle:horizontal:disabled {
    background: #30363d;
    border-color: #21262d;
}

QSlider::groove:horizontal:disabled {
    background: #161b22;
}

/* ═══════════════════════════════════════════════════════════
   Scroll bars — thin but still touch-usable
═══════════════════════════════════════════════════════════ */

QScrollBar:vertical {
    background: #161b22;
    width: 10px;
    border-radius: 5px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 5px;
    min-height: 40px;
}

QScrollBar::handle:vertical:hover {
    background: #484f58;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: #161b22;
    height: 10px;
    border-radius: 5px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #30363d;
    border-radius: 5px;
    min-width: 40px;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ═══════════════════════════════════════════════════════════
   Status bar
═══════════════════════════════════════════════════════════ */

QStatusBar {
    background: #0d1117;
    color: #8b949e;
    font-size: 12px;
    border-top: 1px solid #21262d;
}

/* ═══════════════════════════════════════════════════════════
   Tool tips
═══════════════════════════════════════════════════════════ */

QToolTip {
    background: #161b22;
    color: #e6edf3;
    border: 1px solid #30363d;
    padding: 4px 8px;
    border-radius: 4px;
}

/* ═══════════════════════════════════════════════════════════
   Labels
═══════════════════════════════════════════════════════════ */

QLabel {
    background: transparent;
    color: #e6edf3;
}

/* ═══════════════════════════════════════════════════════════
   File dialog (inherits theme automatically via QPalette)
═══════════════════════════════════════════════════════════ */

QFileDialog {
    background: #161b22;
}

"""
