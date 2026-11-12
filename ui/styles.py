"""
ui/styles.py
Stylesheets and theme palettes for ClipVault (Dark and Light modes).
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

/* ── Scroll area & List View ─────────────────────────── */
QScrollArea, QListView#clipListView {
    border: none;
    background-color: transparent;
    outline: none;
}

QListView#clipListView {
    padding: 4px 6px;
}

QListView#clipListView::item {
    background: transparent;
    border: none;
    padding: 0;
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

QPushButton#themeToggleBtn {
    background-color: transparent;
    border: 1px solid #2D3250;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 14px;
    color: #E2E8F0;
}

QPushButton#themeToggleBtn:hover {
    background-color: #252A3D;
    border: 1px solid #7C83D0;
}
"""

LIGHT_THEME = """
/* ── Global ─────────────────────────────────────────── */
* {
    font-family: 'Segoe UI', 'Ubuntu', sans-serif;
    font-size: 13px;
    color: #0F172A;
}

QMainWindow, QWidget#centralWidget {
    background-color: #F8FAFC;
}

/* ── Search bar ──────────────────────────────────────── */
QLineEdit#searchBar {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    color: #0F172A;
    selection-background-color: #E0E7FF;
    selection-color: #1E1B4B;
}

QLineEdit#searchBar:focus {
    border: 1px solid #6366F1;
    background-color: #FFFFFF;
}

QLineEdit#searchBar::placeholder {
    color: #94A3B8;
}

/* ── Scroll area & List View ─────────────────────────── */
QScrollArea, QListView#clipListView {
    border: none;
    background-color: transparent;
    outline: none;
}

QListView#clipListView {
    padding: 4px 6px;
}

QListView#clipListView::item {
    background: transparent;
    border: none;
    padding: 0;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

QScrollBar:vertical {
    background: #F1F5F9;
    width: 6px;
    margin: 0;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 3px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

/* ── Empty-state label ───────────────────────────────── */
QLabel#emptyLabel {
    color: #94A3B8;
    font-size: 14px;
}

/* ── Footer ──────────────────────────────────────────── */
QLabel#footerLabel {
    background-color: #F1F5F9;
    color: #64748B;
    font-size: 11px;
    padding: 4px 12px;
    border-top: 1px solid #E2E8F0;
}

/* ── Section title ───────────────────────────────────── */
QLabel#sectionTitle {
    color: #64748B;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}

/* ── Top header bar ──────────────────────────────────── */
QFrame#headerBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
}

QLabel#appTitle {
    color: #4F46E5;
    font-size: 16px;
    font-weight: bold;
    letter-spacing: 1px;
}

QPushButton#themeToggleBtn {
    background-color: transparent;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 14px;
    color: #475569;
}

QPushButton#themeToggleBtn:hover {
    background-color: #F1F5F9;
    border: 1px solid #6366F1;
    color: #0F172A;
}
"""

# ── Dynamic Palette Mapping for ClipboardItemDelegate ────────────────
DELEGATE_PALETTES = {
    "dark": {
        "unpinned_bg": "#1A1E2E",
        "unpinned_bg_hover": "#1E2438",
        "unpinned_border": "#252A3D",
        "unpinned_border_hover": "#3A4060",
        "pinned_bg": "#22253B",
        "pinned_bg_hover": "#262942",
        "pinned_border": "#4B5280",
        "pinned_border_hover": "#5C659E",
        "selected_bg": "#2D3250",
        "text_primary": "#CBD5E1",
        "text_secondary": "#555E7A",
        "badge_bg": "#252A3D",
        "badge_border": "#2D3250",
        "badge_text": "#7C83D0",
        "pin_active": "#F59E0B",
        "pin_inactive": "#4A4F6B",
        "pin_hover": "#A0AACC",
        "pin_hover_bg": "#2D3250",
        "copy_bg": "#2D3250",
        "copy_bg_hover": "#424769",
        "copy_fg": "#A0AACC",
        "copy_fg_hover": "#E2E8F0",
        "copy_success_bg": "#2D6A4F",
        "copy_success_fg": "#B7E4C7",
        "del_border": "#2A1E25",
        "del_border_hover": "#6B3040",
        "del_bg_hover": "#301520",
        "del_fg": "#5A3A45",
        "del_fg_hover": "#E05070",
    },
    "light": {
        "unpinned_bg": "#FFFFFF",
        "unpinned_bg_hover": "#F8FAFC",
        "unpinned_border": "#E2E8F0",
        "unpinned_border_hover": "#CBD5E1",
        "pinned_bg": "#FEF3C7",
        "pinned_bg_hover": "#FDE68A",
        "pinned_border": "#F59E0B",
        "pinned_border_hover": "#D97706",
        "selected_bg": "#E0E7FF",
        "text_primary": "#0F172A",
        "text_secondary": "#64748B",
        "badge_bg": "#EEF2FF",
        "badge_border": "#C7D2FE",
        "badge_text": "#4F46E5",
        "pin_active": "#D97706",
        "pin_inactive": "#94A3B8",
        "pin_hover": "#475569",
        "pin_hover_bg": "#E2E8F0",
        "copy_bg": "#F1F5F9",
        "copy_bg_hover": "#E2E8F0",
        "copy_fg": "#475569",
        "copy_fg_hover": "#0F172A",
        "copy_success_bg": "#DCFCE7",
        "copy_success_fg": "#15803D",
        "del_border": "#FEE2E2",
        "del_border_hover": "#FECACA",
        "del_bg_hover": "#FEE2E2",
        "del_fg": "#991B1B",
        "del_fg_hover": "#DC2626",
    },
}
