"""
ui/styles.py
------------
Centralised dark-theme stylesheet for ClipVault.
Import DARK_THEME and pass it to QApplication.setStyleSheet().

Targets used in this file
--------------------------
#centralWidget      — main background
#headerBar          — top title bar
#appTitle           — "ClipVault" heading
#searchBar          — QLineEdit search field
#sectionTitle       — "RECENT" label above the list
#clipItem           — each clipboard card (QFrame)
#itemText           — preview text inside a card
#itemTime           — timestamp inside a card
#lineBadge          — "N lines" pill badge inside a card
#copyBtn            — Copy button inside a card
#deleteBtn          — Delete (✕) button inside a card
#emptyLabel         — shown when the list is empty
#footerLabel        — bottom status bar
"""

DARK_THEME = """
/* ── Global ─────────────────────────────────────────── */
* {
    font-family: 'Segoe UI', 'Ubuntu', sans-serif;
    font-size: 13px;
    color: #E2E8F0;
}

QMainWindow, QWidget#centralWidget {
    background-color: #0F1117;
}

/* ── Search bar ──────────────────────────────────────── */
QLineEdit#searchBar {
    background-color: #1E2130;
    border: 1px solid #2D3250;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    color: #E2E8F0;
    selection-background-color: #424769;
}

QLineEdit#searchBar:focus {
    border: 1px solid #7C83D0;
    background-color: #252A3D;
}

QLineEdit#searchBar::placeholder {
    color: #555E7A;
}

/* ── Scroll area ─────────────────────────────────────── */
QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

QScrollBar:vertical {
    background: #1E2130;
    width: 6px;
    margin: 0;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #424769;
    border-radius: 3px;
    min-height: 30px;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

/* ── Clipboard item cards ────────────────────────────── */
QFrame#clipItem {
    background-color: #1A1E2E;
    border: 1px solid #252A3D;
    border-radius: 8px;
    max-height: 68px;
}

QFrame#clipItem:hover {
    background-color: #1E2438;
    border: 1px solid #3A4060;
}

QLabel#itemText {
    color: #CBD5E1;
    font-size: 13px;
    padding: 0;
}

QLabel#itemTime {
    color: #555E7A;
    font-size: 10px;
}

/* ── Multiline badge ("N lines") ─────────────────────── */
QLabel#lineBadge {
    color: #7C83D0;
    font-size: 9px;
    background-color: #252A3D;
    border: 1px solid #2D3250;
    border-radius: 4px;
    padding: 0px 4px;
}

/* ── Copy button ─────────────────────────────────────── */
QPushButton#copyBtn {
    background-color: #2D3250;
    border: none;
    border-radius: 5px;
    padding: 4px 8px;
    color: #A0AACC;
    font-size: 11px;
}

QPushButton#copyBtn:hover {
    background-color: #424769;
    color: #E2E8F0;
}

QPushButton#copyBtn:pressed {
    background-color: #7C83D0;
    color: #ffffff;
}

/* ── Delete button ───────────────────────────────────── */
QPushButton#deleteBtn {
    background-color: transparent;
    border: 1px solid #2A1E25;
    border-radius: 5px;
    padding: 4px 6px;
    color: #5A3A45;
    font-size: 12px;
    font-weight: bold;
}

QPushButton#deleteBtn:hover {
    background-color: #301520;
    border: 1px solid #6B3040;
    color: #E05070;
}

QPushButton#deleteBtn:pressed {
    background-color: #4A1525;
    color: #FF6080;
}

/* ── Empty-state label ───────────────────────────────── */
QLabel#emptyLabel {
    color: #3A4060;
    font-size: 14px;
}

/* ── Footer ──────────────────────────────────────────── */
QLabel#footerLabel {
    background-color: #0B0D14;
    color: #424769;
    font-size: 11px;
    padding: 4px 12px;
    border-top: 1px solid #1A1E2E;
}

/* ── Section title ───────────────────────────────────── */
QLabel#sectionTitle {
    color: #555E7A;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}

/* ── Top header bar ──────────────────────────────────── */
QFrame#headerBar {
    background-color: #0B0D14;
    border-bottom: 1px solid #1A1E2E;
}

QLabel#appTitle {
    color: #7C83D0;
    font-size: 16px;
    font-weight: bold;
    letter-spacing: 1px;
}
"""
