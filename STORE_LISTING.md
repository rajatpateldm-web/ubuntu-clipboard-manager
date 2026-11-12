# Snap Store Listing Details: clipvault-teckscaler

This document provides ready-to-use copy and metadata for the Canonical Snap Store (Snapcraft) listing submission.

## Listing Metadata

*   **Snap Name:** `clipvault-teckscaler` (or `clipvault`)
*   **Application Title:** `ClipVault`
*   **Primary Category:** `Utilities`
*   **Secondary Category:** `Productivity`
*   **License:** `MIT`
*   **Website:** `https://teckscaler.com/`
*   **Video URL:** `https://teckscaler.com/`
*   **Issue Tracker:** `https://github.com/rajatpateldm-web/ubuntu-clipboard-manager/issues`

## Summary (Max 79 characters)

```text
Privacy-aware clipboard manager with Wayland support and password protection
```
*(76 characters: strictly within the 79-character Snap Store boundary)*

## Detailed Description (Markdown for Store Listing)

```markdown
ClipVault is a lightweight, privacy-focused clipboard manager for Linux desktop environments, engineered specifically for modern Wayland compositors (GNOME, Ubuntu) and X11 sessions.

### Key Capabilities

* **Hardware-Level Privacy Protection:** Automatically intercepts and filters sensitive clipboard metadata from password managers such as KeePassXC, 1Password, Bitwarden, and KWallet. Secrets are dropped immediately without ever touching memory or disk history.
* **Wayland & X11 Native Monitoring:** Employs an asynchronous three-tier polling engine that completely eliminates GNOME dock flickering and GUI stuttering by delegating subprocesses off the main thread.
* **Dark and Light Modes:** Toggle seamlessly between dark and light themes with one click. Theme preferences are persisted automatically across sessions.
* **Virtualized Performance:** Built on Qt's Model-View-Delegate architecture. Renders hundreds of clipboard history items with constant O(1) memory overhead and smooth 60fps scrolling.
* **Instant Substring Search:** Filter through code snippets, URLs, and multi-line notes in real time.
* **Card Pinning:** Pin important snippets, API keys, or templates so they stay permanently anchored at the top of your list.
* **Keyboard Ergonomics:** Complete keyboard flow. Use Down Arrow to jump from search into items, Enter to copy, Delete to remove, and Escape for instant window dismissal.
* **Strict Snap Confinement:** Runs within Ubuntu's secure AppArmor sandbox with restricted UNIX file permissions (0600) on local SQLite databases.

### Recommended Desktop Shortcut

To toggle ClipVault using a global keyboard shortcut (such as Super+V):
1. Open Ubuntu Settings -> Keyboard -> Keyboard Shortcuts -> Custom Shortcuts.
2. Add a new shortcut named "Toggle ClipVault".
3. Set the command to: `clipvault-teckscaler.toggle` (or `clipvault.toggle`).
4. Assign your preferred key combination.
```

## Keywords / Tags

```text
clipboard, clipboard-manager, wayland, x11, privacy, keepassxc, bitwarden, 1password, productivity, utilities, ubuntu
```

## Permission Justifications (For Reviewers)

*   `wayland` / `x11`: Required to listen for system clipboard events and paste text across active Wayland and XWayland windows.
*   `desktop` / `desktop-legacy`: Required to display application windows, system tray integration, and desktop icons.
*   `network-bind`: Required exclusively for local UNIX domain socket binding (`QLocalServer`), enabling single-instance detection and shortcut toggle triggers. Does not access external networks.

