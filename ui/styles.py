"""
ui/styles.py
Stylesheets, theme palettes, color schemes, and font configuration helpers for ClipVault.
"""

import re

# ── Font Configuration Constants ──────────────────────────────────────
DEFAULT_FONT_FAMILY = "System Default"
DEFAULT_FONT_STYLE = "Regular"
DEFAULT_FONT_SIZE = 13
MIN_FONT_SIZE = 10
MAX_FONT_SIZE = 22

# Maps preset names to (QSS font-family stack, Qt QFont primary family)
FONT_FAMILY_PRESETS = {
    "System Default": ("'Segoe UI', 'Ubuntu', sans-serif", "Ubuntu"),
    "Ubuntu": ("'Ubuntu', sans-serif", "Ubuntu"),
    "Sans Serif": ("sans-serif", "Sans Serif"),
    "Monospace": ("'Ubuntu Mono', 'DejaVu Sans Mono', monospace", "Ubuntu Mono"),
    "Serif": ("'Georgia', 'DejaVu Serif', serif", "Serif"),
}

# Maps style labels to (QSS font-weight, QSS font-style, QFont bold, QFont italic)
FONT_STYLE_OPTIONS = {
    "Regular": ("normal", "normal", False, False),
    "Bold": ("bold", "normal", True, False),
    "Italic": ("normal", "italic", False, True),
    "Bold Italic": ("bold", "italic", True, True),
}

# ── Color Scheme Configuration ────────────────────────────────────────
DEFAULT_COLOR_SCHEME = "Classic"

COLOR_SCHEME_DESCRIPTIONS = {
    "Classic": "ClipVault Indigo",
    "Cyan": "Ocean Teal",
    "One Dark": "VS Code Slate",
    "Dracula": "Vampire Purple",
    "Nord": "Arctic Frost",
    "Tokyo Night": "Midnight Blue",
    "Monokai": "Charcoal & Lime",
    "Gruvbox": "Retro Warm",
    "Solarized": "Precision Contrast",
    "Catppuccin": "Pastel Mocha",
}

_CLASSIC_QSS_COLORS = {
    "dark": {
        "text": "#E2E8F0",
        "window_bg": "#0F1117",
        "search_bg": "#1E2130",
        "search_border": "#2D3250",
        "search_sel_bg": "#424769",
        "search_sel_fg": "#E2E8F0",
        "search_focus_border": "#7C83D0",
        "search_focus_bg": "#252A3D",
        "placeholder": "#555E7A",
        "scroll_bg": "#1E2130",
        "scroll_handle": "#424769",
        "scroll_handle_hover": "#5C659E",
        "empty_fg": "#3A4060",
        "footer_bg": "#0B0D14",
        "footer_fg": "#424769",
        "footer_border": "#1A1E2E",
        "section_fg": "#555E7A",
        "header_bg": "#0B0D14",
        "header_border": "#1A1E2E",
        "title_fg": "#7C83D0",
        "btn_border": "#2D3250",
        "btn_fg": "#E2E8F0",
        "btn_hover_bg": "#252A3D",
        "btn_hover_border": "#7C83D0",
        "btn_hover_fg": "#E2E8F0",
        "dialog_bg": "#141824",
        "input_bg": "#1E2130",
        "input_border": "#2D3250",
        "input_hover_bg": "#252A3D",
        "preview_bg": "#1A1E2E",
        "preview_border": "#2D3250",
        "muted_fg": "#94A3B8",
        "primary_bg": "#5C659E",
        "primary_hover_bg": "#7C83D0",
        "primary_fg": "#FFFFFF",
    },
    "light": {
        "text": "#0F172A",
        "window_bg": "#F8FAFC",
        "search_bg": "#FFFFFF",
        "search_border": "#CBD5E1",
        "search_sel_bg": "#E0E7FF",
        "search_sel_fg": "#1E1B4B",
        "search_focus_border": "#6366F1",
        "search_focus_bg": "#FFFFFF",
        "placeholder": "#94A3B8",
        "scroll_bg": "#F1F5F9",
        "scroll_handle": "#CBD5E1",
        "scroll_handle_hover": "#94A3B8",
        "empty_fg": "#94A3B8",
        "footer_bg": "#F1F5F9",
        "footer_fg": "#64748B",
        "footer_border": "#E2E8F0",
        "section_fg": "#64748B",
        "header_bg": "#FFFFFF",
        "header_border": "#E2E8F0",
        "title_fg": "#4F46E5",
        "btn_border": "#CBD5E1",
        "btn_fg": "#475569",
        "btn_hover_bg": "#F1F5F9",
        "btn_hover_border": "#6366F1",
        "btn_hover_fg": "#0F172A",
        "dialog_bg": "#FFFFFF",
        "input_bg": "#F8FAFC",
        "input_border": "#CBD5E1",
        "input_hover_bg": "#EEF2FF",
        "preview_bg": "#F8FAFC",
        "preview_border": "#CBD5E1",
        "muted_fg": "#64748B",
        "primary_bg": "#4F46E5",
        "primary_hover_bg": "#6366F1",
        "primary_fg": "#FFFFFF",
    },
}

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


def _build_scheme_variant(
    *,
    is_dark: bool,
    window_bg: str,
    chrome_bg: str,
    surface: str,
    surface_hover: str,
    elevated: str,
    border: str,
    border_hover: str,
    accent: str,
    accent_hover: str,
    text: str,
    muted: str,
    pinned_bg: str,
    pinned_bg_hover: str,
    pinned_border: str,
    pinned_border_hover: str,
    pin_active: str,
    selected_bg: str,
    badge_bg: str,
    badge_border: str,
    primary_fg: str = "#FFFFFF",
) -> dict[str, dict[str, str]]:
    """Derive matched QSS and delegate palette dicts from semantic scheme tokens."""
    if is_dark:
        copy_success_bg = "#1E4D3B"
        copy_success_fg = "#A7F3D0"
        del_border = border
        del_border_hover = "#7F1D1D"
        del_bg_hover = "#3B161E"
        del_fg = muted
        del_fg_hover = "#FB7185"
    else:
        copy_success_bg = "#DCFCE7"
        copy_success_fg = "#15803D"
        del_border = "#FECACA"
        del_border_hover = "#FCA5A5"
        del_bg_hover = "#FEE2E2"
        del_fg = "#B91C1C"
        del_fg_hover = "#DC2626"

    qss = {
        "text": text,
        "window_bg": window_bg,
        "search_bg": surface,
        "search_border": border,
        "search_sel_bg": selected_bg,
        "search_sel_fg": text,
        "search_focus_border": accent,
        "search_focus_bg": surface_hover,
        "placeholder": muted,
        "scroll_bg": chrome_bg,
        "scroll_handle": border_hover,
        "scroll_handle_hover": accent,
        "empty_fg": muted,
        "footer_bg": chrome_bg,
        "footer_fg": muted,
        "footer_border": border,
        "section_fg": muted,
        "header_bg": chrome_bg,
        "header_border": border,
        "title_fg": accent,
        "btn_border": border,
        "btn_fg": text,
        "btn_hover_bg": elevated,
        "btn_hover_border": accent,
        "btn_hover_fg": text,
        "dialog_bg": window_bg,
        "input_bg": surface,
        "input_border": border,
        "input_hover_bg": selected_bg,
        "preview_bg": surface,
        "preview_border": border,
        "muted_fg": muted,
        "primary_bg": accent,
        "primary_hover_bg": accent_hover,
        "primary_fg": primary_fg,
    }
    delegate = {
        "unpinned_bg": surface,
        "unpinned_bg_hover": surface_hover,
        "unpinned_border": border,
        "unpinned_border_hover": border_hover,
        "pinned_bg": pinned_bg,
        "pinned_bg_hover": pinned_bg_hover,
        "pinned_border": pinned_border,
        "pinned_border_hover": pinned_border_hover,
        "selected_bg": selected_bg,
        "text_primary": text,
        "text_secondary": muted,
        "badge_bg": badge_bg,
        "badge_border": badge_border,
        "badge_text": accent,
        "pin_active": pin_active,
        "pin_inactive": muted,
        "pin_hover": accent,
        "pin_hover_bg": elevated,
        "copy_bg": elevated,
        "copy_bg_hover": selected_bg,
        "copy_fg": text,
        "copy_fg_hover": accent,
        "copy_success_bg": copy_success_bg,
        "copy_success_fg": copy_success_fg,
        "del_border": del_border,
        "del_border_hover": del_border_hover,
        "del_bg_hover": del_bg_hover,
        "del_fg": del_fg,
        "del_fg_hover": del_fg_hover,
    }
    return {"qss": qss, "delegate": delegate}


COLOR_SCHEMES = {
    "Classic": {
        "dark": {"qss": _CLASSIC_QSS_COLORS["dark"], "delegate": DELEGATE_PALETTES["dark"]},
        "light": {"qss": _CLASSIC_QSS_COLORS["light"], "delegate": DELEGATE_PALETTES["light"]},
    },
    "Cyan": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#071318",
            chrome_bg="#050E12",
            surface="#0C1F26",
            surface_hover="#112933",
            elevated="#163542",
            border="#164E63",
            border_hover="#0891B2",
            accent="#22D3EE",
            accent_hover="#67E8F9",
            text="#ECFEFF",
            muted="#67A9B8",
            pinned_bg="#0E2A33",
            pinned_bg_hover="#133642",
            pinned_border="#06B6D4",
            pinned_border_hover="#22D3EE",
            pin_active="#22D3EE",
            selected_bg="#155E75",
            badge_bg="#083344",
            badge_border="#0E7490",
            primary_fg="#042F2E",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#F0FDFA",
            chrome_bg="#FFFFFF",
            surface="#FFFFFF",
            surface_hover="#ECFEFF",
            elevated="#E0F7FA",
            border="#A5F3FC",
            border_hover="#22D3EE",
            accent="#0891B2",
            accent_hover="#0E7490",
            text="#083344",
            muted="#0E7490",
            pinned_bg="#CFFAFE",
            pinned_bg_hover="#A5F3FC",
            pinned_border="#06B6D4",
            pinned_border_hover="#0891B2",
            pin_active="#0891B2",
            selected_bg="#CFFAFE",
            badge_bg="#ECFEFF",
            badge_border="#67E8F9",
        ),
    },
    "One Dark": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#21252B",
            chrome_bg="#1B1E23",
            surface="#282C34",
            surface_hover="#2C313C",
            elevated="#353B45",
            border="#3E4451",
            border_hover="#528BFF",
            accent="#61AFEF",
            accent_hover="#7EC0F5",
            text="#ABB2BF",
            muted="#7F848E",
            pinned_bg="#2F333D",
            pinned_bg_hover="#373C48",
            pinned_border="#E5C07B",
            pinned_border_hover="#F0CE8E",
            pin_active="#E5C07B",
            selected_bg="#3A4150",
            badge_bg="#2C313C",
            badge_border="#4B5263",
            primary_fg="#1B1E23",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#FAFAFA",
            chrome_bg="#F0F0F1",
            surface="#FFFFFF",
            surface_hover="#F3F4F6",
            elevated="#EAEAEB",
            border="#D4D4D8",
            border_hover="#4078F2",
            accent="#4078F2",
            accent_hover="#2563EB",
            text="#383A42",
            muted="#696C77",
            pinned_bg="#FEF3C7",
            pinned_bg_hover="#FDE68A",
            pinned_border="#C18401",
            pinned_border_hover="#986801",
            pin_active="#C18401",
            selected_bg="#E5EBF1",
            badge_bg="#EFF4FF",
            badge_border="#BFDBFE",
        ),
    },
    "Dracula": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#21222C",
            chrome_bg="#191A21",
            surface="#282A36",
            surface_hover="#2F3240",
            elevated="#383B4D",
            border="#44475A",
            border_hover="#BD93F9",
            accent="#BD93F9",
            accent_hover="#D6B8FF",
            text="#F8F8F2",
            muted="#8B96BF",
            pinned_bg="#332E47",
            pinned_bg_hover="#3C3654",
            pinned_border="#FF79C6",
            pinned_border_hover="#FF92D0",
            pin_active="#FF79C6",
            selected_bg="#44475A",
            badge_bg="#343746",
            badge_border="#6272A4",
            primary_fg="#191A21",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#F8F7FC",
            chrome_bg="#FFFFFF",
            surface="#FFFFFF",
            surface_hover="#F3EFFE",
            elevated="#EDE9FE",
            border="#DDD6FE",
            border_hover="#8B5CF6",
            accent="#7C3AED",
            accent_hover="#6D28D9",
            text="#1E1B4B",
            muted="#6D6A8A",
            pinned_bg="#FCE7F3",
            pinned_bg_hover="#FBCFE8",
            pinned_border="#EC4899",
            pinned_border_hover="#DB2777",
            pin_active="#DB2777",
            selected_bg="#EDE9FE",
            badge_bg="#F5F3FF",
            badge_border="#C4B5FD",
        ),
    },
    "Nord": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#242933",
            chrome_bg="#1F242D",
            surface="#2E3440",
            surface_hover="#353C4A",
            elevated="#3B4252",
            border="#434C5E",
            border_hover="#88C0D0",
            accent="#88C0D0",
            accent_hover="#8FBCBB",
            text="#ECEFF4",
            muted="#9AA5BA",
            pinned_bg="#333C4B",
            pinned_bg_hover="#3B4657",
            pinned_border="#EBCB8B",
            pinned_border_hover="#F3D9A4",
            pin_active="#EBCB8B",
            selected_bg="#434C5E",
            badge_bg="#3B4252",
            badge_border="#4C566A",
            primary_fg="#242933",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#ECEFF4",
            chrome_bg="#E5E9F0",
            surface="#FFFFFF",
            surface_hover="#F8FAFC",
            elevated="#E5E9F0",
            border="#D8DEE9",
            border_hover="#5E81AC",
            accent="#5E81AC",
            accent_hover="#4C6E96",
            text="#2E3440",
            muted="#4C566A",
            pinned_bg="#FEF3C7",
            pinned_bg_hover="#FDE68A",
            pinned_border="#D08770",
            pinned_border_hover="#B86B53",
            pin_active="#D08770",
            selected_bg="#D8DEE9",
            badge_bg="#E5E9F0",
            badge_border="#CBD5E1",
        ),
    },
    "Tokyo Night": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#16161E",
            chrome_bg="#13131A",
            surface="#1A1B26",
            surface_hover="#212332",
            elevated="#292E42",
            border="#2F3549",
            border_hover="#7AA2F7",
            accent="#7AA2F7",
            accent_hover="#89B4FA",
            text="#C0CAF5",
            muted="#737AA2",
            pinned_bg="#23263A",
            pinned_bg_hover="#2A2E47",
            pinned_border="#BB9AF7",
            pinned_border_hover="#CFAFFF",
            pin_active="#E0AF68",
            selected_bg="#2E3450",
            badge_bg="#24283B",
            badge_border="#3B4261",
            primary_fg="#13131A",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#E8EAF2",
            chrome_bg="#F4F5FA",
            surface="#FFFFFF",
            surface_hover="#F8F9FC",
            elevated="#DFE2EE",
            border="#C4C8DA",
            border_hover="#2467CC",
            accent="#2467CC",
            accent_hover="#1B53A8",
            text="#2B4C9B",
            muted="#52629E",
            pinned_bg="#EFE6FA",
            pinned_bg_hover="#E2D1F7",
            pinned_border="#7847BD",
            pinned_border_hover="#5F329F",
            pin_active="#8C6C3E",
            selected_bg="#D4DDF7",
            badge_bg="#E6ECFB",
            badge_border="#B4C6F5",
        ),
    },
    "Monokai": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#1E1F1C",
            chrome_bg="#171814",
            surface="#272822",
            surface_hover="#2F3029",
            elevated="#3E3D32",
            border="#49483E",
            border_hover="#A6E22E",
            accent="#A6E22E",
            accent_hover="#BEF252",
            text="#F8F8F2",
            muted="#90908A",
            pinned_bg="#333227",
            pinned_bg_hover="#3E3D30",
            pinned_border="#FD971F",
            pinned_border_hover="#FFB152",
            pin_active="#FD971F",
            selected_bg="#49483E",
            badge_bg="#33342C",
            badge_border="#57564A",
            primary_fg="#171814",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#FAF8F5",
            chrome_bg="#F1EFEA",
            surface="#FFFFFF",
            surface_hover="#F7F5F0",
            elevated="#EAE6DF",
            border="#DDD7CD",
            border_hover="#6B8E23",
            accent="#558B2F",
            accent_hover="#33691E",
            text="#2D2B28",
            muted="#757168",
            pinned_bg="#FFF3E0",
            pinned_bg_hover="#FFE0B2",
            pinned_border="#EF6C00",
            pinned_border_hover="#E65100",
            pin_active="#EF6C00",
            selected_bg="#E8E4DC",
            badge_bg="#F1F8E9",
            badge_border="#C5E1A5",
        ),
    },
    "Gruvbox": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#1D2021",
            chrome_bg="#171A1B",
            surface="#282828",
            surface_hover="#32302F",
            elevated="#3C3836",
            border="#504945",
            border_hover="#FABD2F",
            accent="#FABD2F",
            accent_hover="#FBD058",
            text="#EBDBB2",
            muted="#A89984",
            pinned_bg="#3A3127",
            pinned_bg_hover="#473C30",
            pinned_border="#FE8019",
            pinned_border_hover="#FF9B42",
            pin_active="#FE8019",
            selected_bg="#504945",
            badge_bg="#3C3836",
            badge_border="#665C54",
            primary_fg="#1D2021",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#FBF1C7",
            chrome_bg="#F2E5BC",
            surface="#FFFDF2",
            surface_hover="#F9F5D7",
            elevated="#EBDBB2",
            border="#D5C4A1",
            border_hover="#B57614",
            accent="#B57614",
            accent_hover="#945E0B",
            text="#3C3836",
            muted="#7C6F64",
            pinned_bg="#F9E2AF",
            pinned_bg_hover="#F5D08A",
            pinned_border="#AF3A03",
            pinned_border_hover="#8F2E00",
            pin_active="#AF3A03",
            selected_bg="#EBDBB2",
            badge_bg="#F2E5BC",
            badge_border="#D5C4A1",
        ),
    },
    "Solarized": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#00212B",
            chrome_bg="#001B24",
            surface="#002B36",
            surface_hover="#073642",
            elevated="#0D4554",
            border="#165363",
            border_hover="#2AA198",
            accent="#2AA198",
            accent_hover="#3BC1B7",
            text="#EEE8D5",
            muted="#839496",
            pinned_bg="#0B3B45",
            pinned_bg_hover="#104954",
            pinned_border="#B58900",
            pinned_border_hover="#D4A406",
            pin_active="#B58900",
            selected_bg="#073642",
            badge_bg="#073642",
            badge_border="#1B6477",
            primary_fg="#00212B",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#FDF6E3",
            chrome_bg="#EEE8D5",
            surface="#FFFBF0",
            surface_hover="#FDF6E3",
            elevated="#EEE8D5",
            border="#DCD3BA",
            border_hover="#268BD2",
            accent="#268BD2",
            accent_hover="#1E6FA8",
            text="#073642",
            muted="#586E75",
            pinned_bg="#F5EBC9",
            pinned_bg_hover="#EDE0B3",
            pinned_border="#CB4B16",
            pinned_border_hover="#A63A0F",
            pin_active="#CB4B16",
            selected_bg="#E4DEC8",
            badge_bg="#EEE8D5",
            badge_border="#C9C0A6",
        ),
    },
    "Catppuccin": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#181825",
            chrome_bg="#11111B",
            surface="#1E1E2E",
            surface_hover="#26263A",
            elevated="#313244",
            border="#45475A",
            border_hover="#CBA6F7",
            accent="#CBA6F7",
            accent_hover="#DEC2FF",
            text="#CDD6F4",
            muted="#9399B2",
            pinned_bg="#2B2640",
            pinned_bg_hover="#352F4F",
            pinned_border="#F5C2E7",
            pinned_border_hover="#FAD5F0",
            pin_active="#F9E2AF",
            selected_bg="#313244",
            badge_bg="#2A2A3E",
            badge_border="#585B70",
            primary_fg="#11111B",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#EFF1F5",
            chrome_bg="#E6E9EF",
            surface="#FFFFFF",
            surface_hover="#F7F8FA",
            elevated="#DCE0E8",
            border="#CCD0DA",
            border_hover="#8839EF",
            accent="#8839EF",
            accent_hover="#7224D6",
            text="#4C4F69",
            muted="#6C6F85",
            pinned_bg="#F5E8FF",
            pinned_bg_hover="#EAD5FF",
            pinned_border="#EA76CB",
            pinned_border_hover="#D652B2",
            pin_active="#DF8E1D",
            selected_bg="#DCE0E8",
            badge_bg="#F3E8FF",
            badge_border="#D8B4FE",
        ),
    },
}



def _build_scheme_variant(
    *,
    is_dark: bool,
    window_bg: str,
    chrome_bg: str,
    surface: str,
    surface_hover: str,
    elevated: str,
    border: str,
    border_hover: str,
    accent: str,
    accent_hover: str,
    text: str,
    muted: str,
    pinned_bg: str,
    pinned_bg_hover: str,
    pinned_border: str,
    pinned_border_hover: str,
    pin_active: str,
    selected_bg: str,
    badge_bg: str,
    badge_border: str,
    primary_fg: str = "#FFFFFF",
) -> dict[str, dict[str, str]]:
    """Derive matched QSS and delegate palette dicts from semantic scheme tokens."""
    if is_dark:
        copy_success_bg = "#1E4D3B"
        copy_success_fg = "#A7F3D0"
        del_border = border
        del_border_hover = "#7F1D1D"
        del_bg_hover = "#3B161E"
        del_fg = muted
        del_fg_hover = "#FB7185"
    else:
        copy_success_bg = "#DCFCE7"
        copy_success_fg = "#15803D"
        del_border = "#FECACA"
        del_border_hover = "#FCA5A5"
        del_bg_hover = "#FEE2E2"
        del_fg = "#B91C1C"
        del_fg_hover = "#DC2626"

    qss = {
        "text": text,
        "window_bg": window_bg,
        "search_bg": surface,
        "search_border": border,
        "search_sel_bg": selected_bg,
        "search_sel_fg": text,
        "search_focus_border": accent,
        "search_focus_bg": surface_hover,
        "placeholder": muted,
        "scroll_bg": chrome_bg,
        "scroll_handle": border_hover,
        "scroll_handle_hover": accent,
        "empty_fg": muted,
        "footer_bg": chrome_bg,
        "footer_fg": muted,
        "footer_border": border,
        "section_fg": muted,
        "header_bg": chrome_bg,
        "header_border": border,
        "title_fg": accent,
        "btn_border": border,
        "btn_fg": text,
        "btn_hover_bg": elevated,
        "btn_hover_border": accent,
        "btn_hover_fg": text,
        "dialog_bg": window_bg,
        "input_bg": surface,
        "input_border": border,
        "input_hover_bg": selected_bg,
        "preview_bg": surface,
        "preview_border": border,
        "muted_fg": muted,
        "primary_bg": accent,
        "primary_hover_bg": accent_hover,
        "primary_fg": primary_fg,
    }
    delegate = {
        "unpinned_bg": surface,
        "unpinned_bg_hover": surface_hover,
        "unpinned_border": border,
        "unpinned_border_hover": border_hover,
        "pinned_bg": pinned_bg,
        "pinned_bg_hover": pinned_bg_hover,
        "pinned_border": pinned_border,
        "pinned_border_hover": pinned_border_hover,
        "selected_bg": selected_bg,
        "text_primary": text,
        "text_secondary": muted,
        "badge_bg": badge_bg,
        "badge_border": badge_border,
        "badge_text": accent,
        "pin_active": pin_active,
        "pin_inactive": muted,
        "pin_hover": accent,
        "pin_hover_bg": elevated,
        "copy_bg": elevated,
        "copy_bg_hover": selected_bg,
        "copy_fg": text,
        "copy_fg_hover": accent,
        "copy_success_bg": copy_success_bg,
        "copy_success_fg": copy_success_fg,
        "del_border": del_border,
        "del_border_hover": del_border_hover,
        "del_bg_hover": del_bg_hover,
        "del_fg": del_fg,
        "del_fg_hover": del_fg_hover,
    }
    return {"qss": qss, "delegate": delegate}


COLOR_SCHEMES = {
    "Classic": {
        "dark": {"qss": _CLASSIC_QSS_COLORS["dark"], "delegate": DELEGATE_PALETTES["dark"]},
        "light": {"qss": _CLASSIC_QSS_COLORS["light"], "delegate": DELEGATE_PALETTES["light"]},
    },
    "Cyan": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#071318",
            chrome_bg="#050E12",
            surface="#0C1F26",
            surface_hover="#112933",
            elevated="#163542",
            border="#164E63",
            border_hover="#0891B2",
            accent="#22D3EE",
            accent_hover="#67E8F9",
            text="#ECFEFF",
            muted="#67A9B8",
            pinned_bg="#0E2A33",
            pinned_bg_hover="#133642",
            pinned_border="#06B6D4",
            pinned_border_hover="#22D3EE",
            pin_active="#22D3EE",
            selected_bg="#155E75",
            badge_bg="#083344",
            badge_border="#0E7490",
            primary_fg="#042F2E",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#F0FDFA",
            chrome_bg="#FFFFFF",
            surface="#FFFFFF",
            surface_hover="#ECFEFF",
            elevated="#E0F7FA",
            border="#A5F3FC",
            border_hover="#22D3EE",
            accent="#0891B2",
            accent_hover="#0E7490",
            text="#083344",
            muted="#0E7490",
            pinned_bg="#CFFAFE",
            pinned_bg_hover="#A5F3FC",
            pinned_border="#06B6D4",
            pinned_border_hover="#0891B2",
            pin_active="#0891B2",
            selected_bg="#CFFAFE",
            badge_bg="#ECFEFF",
            badge_border="#67E8F9",
        ),
    },
    "One Dark": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#21252B",
            chrome_bg="#1B1E23",
            surface="#282C34",
            surface_hover="#2C313C",
            elevated="#353B45",
            border="#3E4451",
            border_hover="#528BFF",
            accent="#61AFEF",
            accent_hover="#7EC0F5",
            text="#ABB2BF",
            muted="#7F848E",
            pinned_bg="#2F333D",
            pinned_bg_hover="#373C48",
            pinned_border="#E5C07B",
            pinned_border_hover="#F0CE8E",
            pin_active="#E5C07B",
            selected_bg="#3A4150",
            badge_bg="#2C313C",
            badge_border="#4B5263",
            primary_fg="#1B1E23",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#FAFAFA",
            chrome_bg="#F0F0F1",
            surface="#FFFFFF",
            surface_hover="#F3F4F6",
            elevated="#EAEAEB",
            border="#D4D4D8",
            border_hover="#4078F2",
            accent="#4078F2",
            accent_hover="#2563EB",
            text="#383A42",
            muted="#696C77",
            pinned_bg="#FEF3C7",
            pinned_bg_hover="#FDE68A",
            pinned_border="#C18401",
            pinned_border_hover="#986801",
            pin_active="#C18401",
            selected_bg="#E5EBF1",
            badge_bg="#EFF4FF",
            badge_border="#BFDBFE",
        ),
    },
    "Dracula": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#21222C",
            chrome_bg="#191A21",
            surface="#282A36",
            surface_hover="#2F3240",
            elevated="#383B4D",
            border="#44475A",
            border_hover="#BD93F9",
            accent="#BD93F9",
            accent_hover="#D6B8FF",
            text="#F8F8F2",
            muted="#8B96BF",
            pinned_bg="#332E47",
            pinned_bg_hover="#3C3654",
            pinned_border="#FF79C6",
            pinned_border_hover="#FF92D0",
            pin_active="#FF79C6",
            selected_bg="#44475A",
            badge_bg="#343746",
            badge_border="#6272A4",
            primary_fg="#191A21",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#F8F7FC",
            chrome_bg="#FFFFFF",
            surface="#FFFFFF",
            surface_hover="#F3EFFE",
            elevated="#EDE9FE",
            border="#DDD6FE",
            border_hover="#8B5CF6",
            accent="#7C3AED",
            accent_hover="#6D28D9",
            text="#1E1B4B",
            muted="#6D6A8A",
            pinned_bg="#FCE7F3",
            pinned_bg_hover="#FBCFE8",
            pinned_border="#EC4899",
            pinned_border_hover="#DB2777",
            pin_active="#DB2777",
            selected_bg="#EDE9FE",
            badge_bg="#F5F3FF",
            badge_border="#C4B5FD",
        ),
    },
    "Nord": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#242933",
            chrome_bg="#1F242D",
            surface="#2E3440",
            surface_hover="#353C4A",
            elevated="#3B4252",
            border="#434C5E",
            border_hover="#88C0D0",
            accent="#88C0D0",
            accent_hover="#8FBCBB",
            text="#ECEFF4",
            muted="#9AA5BA",
            pinned_bg="#333C4B",
            pinned_bg_hover="#3B4657",
            pinned_border="#EBCB8B",
            pinned_border_hover="#F3D9A4",
            pin_active="#EBCB8B",
            selected_bg="#434C5E",
            badge_bg="#3B4252",
            badge_border="#4C566A",
            primary_fg="#242933",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#ECEFF4",
            chrome_bg="#E5E9F0",
            surface="#FFFFFF",
            surface_hover="#F8FAFC",
            elevated="#E5E9F0",
            border="#D8DEE9",
            border_hover="#5E81AC",
            accent="#5E81AC",
            accent_hover="#4C6E96",
            text="#2E3440",
            muted="#4C566A",
            pinned_bg="#FEF3C7",
            pinned_bg_hover="#FDE68A",
            pinned_border="#D08770",
            pinned_border_hover="#B86B53",
            pin_active="#D08770",
            selected_bg="#D8DEE9",
            badge_bg="#E5E9F0",
            badge_border="#CBD5E1",
        ),
    },
    "Tokyo Night": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#16161E",
            chrome_bg="#13131A",
            surface="#1A1B26",
            surface_hover="#212332",
            elevated="#292E42",
            border="#2F3549",
            border_hover="#7AA2F7",
            accent="#7AA2F7",
            accent_hover="#89B4FA",
            text="#C0CAF5",
            muted="#737AA2",
            pinned_bg="#23263A",
            pinned_bg_hover="#2A2E47",
            pinned_border="#BB9AF7",
            pinned_border_hover="#CFAFFF",
            pin_active="#E0AF68",
            selected_bg="#2E3450",
            badge_bg="#24283B",
            badge_border="#3B4261",
            primary_fg="#13131A",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#E8EAF2",
            chrome_bg="#F4F5FA",
            surface="#FFFFFF",
            surface_hover="#F8F9FC",
            elevated="#DFE2EE",
            border="#C4C8DA",
            border_hover="#2467CC",
            accent="#2467CC",
            accent_hover="#1B53A8",
            text="#2B4C9B",
            muted="#52629E",
            pinned_bg="#EFE6FA",
            pinned_bg_hover="#E2D1F7",
            pinned_border="#7847BD",
            pinned_border_hover="#5F329F",
            pin_active="#8C6C3E",
            selected_bg="#D4DDF7",
            badge_bg="#E6ECFB",
            badge_border="#B4C6F5",
        ),
    },
    "Monokai": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#1E1F1C",
            chrome_bg="#171814",
            surface="#272822",
            surface_hover="#2F3029",
            elevated="#3E3D32",
            border="#49483E",
            border_hover="#A6E22E",
            accent="#A6E22E",
            accent_hover="#BEF252",
            text="#F8F8F2",
            muted="#90908A",
            pinned_bg="#333227",
            pinned_bg_hover="#3E3D30",
            pinned_border="#FD971F",
            pinned_border_hover="#FFB152",
            pin_active="#FD971F",
            selected_bg="#49483E",
            badge_bg="#33342C",
            badge_border="#57564A",
            primary_fg="#171814",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#FAF8F5",
            chrome_bg="#F1EFEA",
            surface="#FFFFFF",
            surface_hover="#F7F5F0",
            elevated="#EAE6DF",
            border="#DDD7CD",
            border_hover="#6B8E23",
            accent="#558B2F",
            accent_hover="#33691E",
            text="#2D2B28",
            muted="#757168",
            pinned_bg="#FFF3E0",
            pinned_bg_hover="#FFE0B2",
            pinned_border="#EF6C00",
            pinned_border_hover="#E65100",
            pin_active="#EF6C00",
            selected_bg="#E8E4DC",
            badge_bg="#F1F8E9",
            badge_border="#C5E1A5",
        ),
    },
    "Gruvbox": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#1D2021",
            chrome_bg="#171A1B",
            surface="#282828",
            surface_hover="#32302F",
            elevated="#3C3836",
            border="#504945",
            border_hover="#FABD2F",
            accent="#FABD2F",
            accent_hover="#FBD058",
            text="#EBDBB2",
            muted="#A89984",
            pinned_bg="#3A3127",
            pinned_bg_hover="#473C30",
            pinned_border="#FE8019",
            pinned_border_hover="#FF9B42",
            pin_active="#FE8019",
            selected_bg="#504945",
            badge_bg="#3C3836",
            badge_border="#665C54",
            primary_fg="#1D2021",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#FBF1C7",
            chrome_bg="#F2E5BC",
            surface="#FFFDF2",
            surface_hover="#F9F5D7",
            elevated="#EBDBB2",
            border="#D5C4A1",
            border_hover="#B57614",
            accent="#B57614",
            accent_hover="#945E0B",
            text="#3C3836",
            muted="#7C6F64",
            pinned_bg="#F9E2AF",
            pinned_bg_hover="#F5D08A",
            pinned_border="#AF3A03",
            pinned_border_hover="#8F2E00",
            pin_active="#AF3A03",
            selected_bg="#EBDBB2",
            badge_bg="#F2E5BC",
            badge_border="#D5C4A1",
        ),
    },
    "Solarized": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#00212B",
            chrome_bg="#001B24",
            surface="#002B36",
            surface_hover="#073642",
            elevated="#0D4554",
            border="#165363",
            border_hover="#2AA198",
            accent="#2AA198",
            accent_hover="#3BC1B7",
            text="#EEE8D5",
            muted="#839496",
            pinned_bg="#0B3B45",
            pinned_bg_hover="#104954",
            pinned_border="#B58900",
            pinned_border_hover="#D4A406",
            pin_active="#B58900",
            selected_bg="#073642",
            badge_bg="#073642",
            badge_border="#1B6477",
            primary_fg="#00212B",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#FDF6E3",
            chrome_bg="#EEE8D5",
            surface="#FFFBF0",
            surface_hover="#FDF6E3",
            elevated="#EEE8D5",
            border="#DCD3BA",
            border_hover="#268BD2",
            accent="#268BD2",
            accent_hover="#1E6FA8",
            text="#073642",
            muted="#586E75",
            pinned_bg="#F5EBC9",
            pinned_bg_hover="#EDE0B3",
            pinned_border="#CB4B16",
            pinned_border_hover="#A63A0F",
            pin_active="#CB4B16",
            selected_bg="#E4DEC8",
            badge_bg="#EEE8D5",
            badge_border="#C9C0A6",
        ),
    },
    "Catppuccin": {
        "dark": _build_scheme_variant(
            is_dark=True,
            window_bg="#181825",
            chrome_bg="#11111B",
            surface="#1E1E2E",
            surface_hover="#26263A",
            elevated="#313244",
            border="#45475A",
            border_hover="#CBA6F7",
            accent="#CBA6F7",
            accent_hover="#DEC2FF",
            text="#CDD6F4",
            muted="#9399B2",
            pinned_bg="#2B2640",
            pinned_bg_hover="#352F4F",
            pinned_border="#F5C2E7",
            pinned_border_hover="#FAD5F0",
            pin_active="#F9E2AF",
            selected_bg="#313244",
            badge_bg="#2A2A3E",
            badge_border="#585B70",
            primary_fg="#11111B",
        ),
        "light": _build_scheme_variant(
            is_dark=False,
            window_bg="#EFF1F5",
            chrome_bg="#E6E9EF",
            surface="#FFFFFF",
            surface_hover="#F7F8FA",
            elevated="#DCE0E8",
            border="#CCD0DA",
            border_hover="#8839EF",
            accent="#8839EF",
            accent_hover="#7224D6",
            text="#4C4F69",
            muted="#6C6F85",
            pinned_bg="#F5E8FF",
            pinned_bg_hover="#EAD5FF",
            pinned_border="#EA76CB",
            pinned_border_hover="#D652B2",
            pin_active="#DF8E1D",
            selected_bg="#DCE0E8",
            badge_bg="#F3E8FF",
            badge_border="#D8B4FE",
        ),
    },
}


def sanitize_font_family(font_family: str | None) -> str:
    """Normalize and sanitize a font family name for safe QSS and QFont usage."""
    if not isinstance(font_family, str):
        return DEFAULT_FONT_FAMILY

    cleaned = re.sub(r"[\x00'\"{};\r\n]", "", font_family)
    cleaned = cleaned.replace("/*", "").replace("*/", "").strip()[:128]
    if not cleaned:
        return DEFAULT_FONT_FAMILY

    for preset in FONT_FAMILY_PRESETS:
        if cleaned.lower() == preset.lower():
            return preset
    return cleaned


def normalize_font_style(font_style: str | None) -> str:
    """Validate font style label against supported style options."""
    if not isinstance(font_style, str):
        return DEFAULT_FONT_STYLE

    cleaned = font_style.strip().lower()
    for option in FONT_STYLE_OPTIONS:
        if cleaned == option.lower():
            return option
    return DEFAULT_FONT_STYLE


def clamp_font_size(font_size: int | str | None) -> int:
    """Parse and clamp font size within supported pixel bounds."""
    try:
        parsed = int(font_size)
    except (TypeError, ValueError):
        return DEFAULT_FONT_SIZE
    return max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, parsed))


def normalize_color_scheme(color_scheme: str | None) -> str:
    """Validate color scheme name, falling back to DEFAULT_COLOR_SCHEME."""
    if not isinstance(color_scheme, str):
        return DEFAULT_COLOR_SCHEME

    cleaned = color_scheme.strip().lower()
    for name in COLOR_SCHEMES:
        if cleaned == name.lower():
            return name
    return DEFAULT_COLOR_SCHEME


def get_theme_colors(theme_name: str, color_scheme: str = DEFAULT_COLOR_SCHEME) -> dict[str, str]:
    """Return QSS theme color tokens for a theme mode and color scheme."""
    theme = theme_name if theme_name in ("dark", "light") else "dark"
    scheme = normalize_color_scheme(color_scheme)
    return COLOR_SCHEMES[scheme][theme]["qss"]


def get_delegate_palette(theme_name: str, color_scheme: str = DEFAULT_COLOR_SCHEME) -> dict[str, str]:
    """Return ClipboardItemDelegate color palette for a theme mode and color scheme."""
    theme = theme_name if theme_name in ("dark", "light") else "dark"
    scheme = normalize_color_scheme(color_scheme)
    return COLOR_SCHEMES[scheme][theme]["delegate"]


def get_scheme_swatches(theme_name: str, color_scheme: str) -> list[str]:
    """Return four representative hex colors for a color scheme preview card."""
    qss = get_theme_colors(theme_name, color_scheme)
    delegate = get_delegate_palette(theme_name, color_scheme)
    return [
        qss["window_bg"],
        delegate["unpinned_bg"],
        qss["title_fg"],
        delegate["pinned_border"],
    ]


def resolve_font_qss(font_family: str) -> str:
    """Return a CSS font-family value for a preset or custom system family."""
    safe_family = sanitize_font_family(font_family)
    if safe_family in FONT_FAMILY_PRESETS:
        return FONT_FAMILY_PRESETS[safe_family][0]
    return f"'{safe_family}', sans-serif"


def resolve_qt_font_family(font_family: str) -> str:
    """Return a concrete font family name suitable for QFont construction."""
    safe_family = sanitize_font_family(font_family)
    if safe_family in FONT_FAMILY_PRESETS:
        return FONT_FAMILY_PRESETS[safe_family][1]
    return safe_family


def build_stylesheet(
    theme_name: str,
    font_family: str = DEFAULT_FONT_FAMILY,
    font_size: int = DEFAULT_FONT_SIZE,
    font_style: str = DEFAULT_FONT_STYLE,
    color_scheme: str = DEFAULT_COLOR_SCHEME,
) -> str:
    """Build the full application QSS stylesheet for theme, color scheme, and font."""
    c = get_theme_colors(theme_name, color_scheme)

    size = clamp_font_size(font_size)
    style_key = normalize_font_style(font_style)
    font_qss = resolve_font_qss(font_family)
    font_weight, font_slant, _, _ = FONT_STYLE_OPTIONS[style_key]

    small_chrome_size = max(9, min(14, size - 2))
    title_size = min(20, size + 3)
    header_btn_size = min(16, max(12, size + 1))

    return f"""
/* ── Global ─────────────────────────────────────────── */
* {{
    font-family: {font_qss};
    font-size: {size}px;
    font-weight: {font_weight};
    font-style: {font_slant};
    color: {c["text"]};
}}

QMainWindow, QWidget#centralWidget {{
    background-color: {c["window_bg"]};
}}

/* ── Search bar ──────────────────────────────────────── */
QLineEdit#searchBar {{
    background-color: {c["search_bg"]};
    border: 1px solid {c["search_border"]};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: {size}px;
    color: {c["text"]};
    selection-background-color: {c["search_sel_bg"]};
    selection-color: {c["search_sel_fg"]};
}}

QLineEdit#searchBar:focus {{
    border: 1px solid {c["search_focus_border"]};
    background-color: {c["search_focus_bg"]};
}}

QLineEdit#searchBar::placeholder {{
    color: {c["placeholder"]};
}}

/* ── Scroll area & List View ─────────────────────────── */
QScrollArea, QListView#clipListView {{
    border: none;
    background-color: transparent;
    outline: none;
}}

QListView#clipListView {{
    padding: 4px 6px;
}}

QListView#clipListView::item {{
    background: transparent;
    border: none;
    padding: 0;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

QScrollBar:vertical {{
    background: {c["scroll_bg"]};
    width: 6px;
    margin: 0;
    border-radius: 3px;
}}

QScrollBar::handle:vertical {{
    background: {c["scroll_handle"]};
    border-radius: 3px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {c["scroll_handle_hover"]};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ── Empty-state label ───────────────────────────────── */
QLabel#emptyLabel {{
    color: {c["empty_fg"]};
    font-size: {size + 1}px;
}}

/* ── Footer ──────────────────────────────────────────── */
QLabel#footerLabel {{
    background-color: {c["footer_bg"]};
    color: {c["footer_fg"]};
    font-size: {small_chrome_size}px;
    padding: 4px 12px;
    border-top: 1px solid {c["footer_border"]};
}}

/* ── Section title ───────────────────────────────────── */
QLabel#sectionTitle {{
    color: {c["section_fg"]};
    font-size: {small_chrome_size}px;
    font-weight: bold;
    letter-spacing: 1px;
}}

/* ── Top header bar ──────────────────────────────────── */
QFrame#headerBar {{
    background-color: {c["header_bg"]};
    border-bottom: 1px solid {c["header_border"]};
}}

QLabel#appTitle {{
    color: {c["title_fg"]};
    font-size: {title_size}px;
    font-weight: bold;
    letter-spacing: 1px;
}}

QPushButton#themeToggleBtn, QPushButton#fontSettingsBtn, QPushButton#colorSchemeBtn {{
    background-color: transparent;
    border: 1px solid {c["btn_border"]};
    border-radius: 6px;
    padding: 3px 8px;
    font-size: {header_btn_size}px;
    font-weight: normal;
    font-style: normal;
    color: {c["btn_fg"]};
}}

QPushButton#themeToggleBtn:hover, QPushButton#fontSettingsBtn:hover, QPushButton#colorSchemeBtn:hover {{
    background-color: {c["btn_hover_bg"]};
    border: 1px solid {c["btn_hover_border"]};
    color: {c["btn_hover_fg"]};
}}

/* ── Settings Dialogs ────────────────────────────────── */
QFrame#modalBackdrop {{
    background-color: rgba(0, 0, 0, 145);
}}

QDialog#fontOptionsDialog, QDialog#colorOptionsDialog {{
    background-color: {c["dialog_bg"]};
}}

QDialog#fontOptionsDialog[modalOverlay="true"], QDialog#colorOptionsDialog[modalOverlay="true"] {{
    border: 1px solid {c["btn_border"]};
    border-radius: 12px;
}}

QLabel#dialogHeading {{
    color: {c["title_fg"]};
    font-size: 15px;
    font-weight: bold;
    font-style: normal;
}}

QLabel#dialogSubheading {{
    color: {c["muted_fg"]};
    font-size: 12px;
    font-weight: normal;
    font-style: normal;
}}

QLabel#dialogFieldLabel {{
    color: {c["muted_fg"]};
    font-size: 12px;
    font-weight: bold;
    font-style: normal;
}}

QComboBox, QSpinBox {{
    background-color: {c["input_bg"]};
    border: 1px solid {c["input_border"]};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    font-weight: normal;
    font-style: normal;
    color: {c["text"]};
}}

QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {c["search_focus_border"]};
}}

QComboBox QAbstractItemView {{
    background-color: {c["input_bg"]};
    border: 1px solid {c["input_border"]};
    selection-background-color: {c["input_hover_bg"]};
    selection-color: {c["text"]};
    color: {c["text"]};
    outline: none;
}}

QFrame#fontPreviewCard {{
    background-color: {c["preview_bg"]};
    border: 1px solid {c["preview_border"]};
    border-radius: 8px;
}}

QLabel#fontPreviewMeta {{
    color: {c["muted_fg"]};
}}

QPushButton#colorOptionCard {{
    background-color: {c["preview_bg"]};
    border: 1px solid {c["preview_border"]};
    border-radius: 8px;
    padding: 8px 10px;
    text-align: left;
    font-size: 13px;
    font-weight: normal;
    font-style: normal;
    color: {c["text"]};
}}

QPushButton#colorOptionCard:hover {{
    background-color: {c["btn_hover_bg"]};
    border: 1px solid {c["btn_hover_border"]};
}}

QPushButton#colorOptionCard[selected="true"] {{
    background-color: {c["input_hover_bg"]};
    border: 2px solid {c["title_fg"]};
}}

QPushButton#dialogSecondaryBtn {{
    background-color: transparent;
    border: 1px solid {c["btn_border"]};
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: normal;
    font-style: normal;
    color: {c["btn_fg"]};
}}

QPushButton#dialogSecondaryBtn:hover {{
    background-color: {c["btn_hover_bg"]};
    border: 1px solid {c["btn_hover_border"]};
    color: {c["btn_hover_fg"]};
}}

QPushButton#dialogPrimaryBtn {{
    background-color: {c["primary_bg"]};
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 13px;
    font-weight: bold;
    font-style: normal;
    color: {c["primary_fg"]};
}}

QPushButton#dialogPrimaryBtn:hover {{
    background-color: {c["primary_hover_bg"]};
}}
"""


DARK_THEME = build_stylesheet("dark")
LIGHT_THEME = build_stylesheet("light")
