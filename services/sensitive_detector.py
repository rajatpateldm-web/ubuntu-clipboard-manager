"""
services/sensitive_detector.py
------------------------------
Detection of sensitive clipboard content from password managers (such as KeePassXC,
Bitwarden, 1Password, KWallet) using standard MIME types and clipboard hints.

Common standard format:
    x-kde-passwordManagerHint: "secret"
"""

import logging

log = logging.getLogger("ClipVault.sensitive")

# Standard formats and MIME types used across Linux/KDE/GNOME/Wayland/macOS
SENSITIVE_MIME_FORMATS = {
    "x-kde-passwordManagerHint",
    "application/x-kde-passwordManagerHint",
    "application/x-password-manager-hint",
    "x-password-manager-hint",
    "application/x-nspasteboard-concealed-type",
    "application/x-copyq-secret",
    "text/x-moz-secret",
    "x-secret",
}

# Pre-computed lowercase lookup set for fast O(1) case-insensitive matching
_SENSITIVE_LOWERCASE = {fmt.lower() for fmt in SENSITIVE_MIME_FORMATS}

# Values that explicitly declare content is NOT sensitive
_NEGATIVE_VALUES = {b"0", b"false", b"no"}


def is_sensitive_format(format_name: str | None) -> bool:
    """
    Check if a single MIME type or target format name matches known password manager hints.
    Case-insensitive.
    """
    if not format_name:
        return False
    return format_name.strip().lower() in _SENSITIVE_LOWERCASE


def is_sensitive_targets(targets: list[str] | str | None) -> bool:
    """
    Check if any target format in a list or raw newline-delimited output
    matches a sensitive password manager hint.
    """
    if not targets:
        return False

    if isinstance(targets, str):
        target_list = [line.strip() for line in targets.splitlines() if line.strip()]
    else:
        target_list = targets

    for target in target_list:
        if is_sensitive_format(target):
            log.info(f"Sensitive clipboard format detected in targets: {target}")
            return True

    return False


def is_sensitive_mime_data(mime_data) -> bool:
    """
    Check if a QMimeData object carries a sensitive password manager hint.
    Examines formats and validates that hints are not explicitly deactivated (e.g. '0' or 'false').
    """
    if mime_data is None:
        return False

    try:
        formats = mime_data.formats()
    except (RuntimeError, AttributeError) as exc:
        log.warning("Failed to query MIME formats: %s", exc)
        return False

    for fmt in formats:
        if is_sensitive_format(fmt):
            # Check if payload contains an explicit negative override
            try:
                raw = mime_data.data(fmt)
                if raw is not None:
                    # In PyQt, QByteArray can be converted to bytes
                    val = bytes(raw).strip().lower()
                    if val in _NEGATIVE_VALUES:
                        continue
            except (RuntimeError, TypeError, ValueError) as exc:
                log.debug("Could not read MIME hint payload for %s: %s", fmt, exc)

            log.info("Sensitive clipboard format detected in QMimeData: %s", fmt)
            return True

    return False
