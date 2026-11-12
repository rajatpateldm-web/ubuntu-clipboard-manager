# ClipVault Software Distribution Checklist

A step-by-step release checklist for distributing ClipVault across Linux package formats, application stores, and software discovery directories.

## 1. Canonical Snap Store

Current Status: Revision 1 uploaded to candidate channel.

### Tasks
- [ ] Verify candidate channel installation on clean Ubuntu environment:
  ```bash
  sudo snap install clipvault-teckscaler --channel=candidate
  clipvault-teckscaler
  clipvault-teckscaler.toggle
  ```
- [ ] Promote revision to stable channel:
  ```bash
  snapcraft promote clipvault-teckscaler --from-channel candidate --to-channel stable
  ```
- [ ] Complete store listing at [Snapcraft Publisher Dashboard](https://snapcraft.io/clipvault-teckscaler/listing):
  - [ ] Set primary category to `Utilities` and secondary category to `Productivity`
  - [ ] Upload 2 to 4 desktop screenshots (1920x1080 or 1280x720 PNG)
  - [ ] Verify website link points to [teckscaler.com](https://www.teckscaler.com)
- [ ] Request automatic alias for `clipvault` on the [Snapcraft Store Forum](https://forum.snapcraft.io/c/store/10):
  - Post an alias request topic titled `Alias request: clipvault for clipvault-teckscaler`
  - Once approved by reviewers, users installing `clipvault-teckscaler` can run `clipvault` directly without typing the full package name

Primary Documentation: [Snapcraft Publishing Documentation](https://documentation.ubuntu.com/snapcraft/stable/how-to/publishing/publish-a-snap/)

## 2. Flathub (Flatpak)

Flathub is the standard application repository for Fedora, Linux Mint, Pop!_OS, Arch Linux, and the Steam Deck.

### Prerequisites
- GitHub account to submit pull requests to [flathub/flathub](https://github.com/flathub/flathub)
- `flatpak` and `flatpak-builder` installed locally

### Tasks
- [ ] Create AppStream metadata specification file `com.teckscaler.ClipVault.metainfo.xml`:
  - Define application ID: `com.teckscaler.ClipVault`
  - Include summary, description, OARS content rating, license, and developer name
  - Add screenshot URLs hosted on GitHub or website
- [ ] Create Flatpak manifest `com.teckscaler.ClipVault.yaml`:
  - Base runtime: `org.kde.Platform` (runtime version 6.6 or later for Qt6 support)
  - Sandbox permissions:
    ```yaml
    finish-args:
      - --share=ipc
      - --socket=fallback-x11
      - --socket=wayland
      - --device=dri
      - --filesystem=xdg-data/clipvault:create
    ```
  - Module source: Point to git repository tag with commit hash
  - Dependencies: Include PyPI dependencies using `flatpak-pip-generator`
- [ ] Verify local Flatpak build:
  ```bash
  flatpak-builder --user --install --force-clean build-dir com.teckscaler.ClipVault.yaml
  flatpak run com.teckscaler.ClipVault
  ```
- [ ] Submit application to Flathub:
  - Fork [flathub/flathub](https://github.com/flathub/flathub)
  - Create new branch `add-com.teckscaler.ClipVault`
  - Open pull request following [Flathub submission guidelines](https://docs.flathub.org/docs/for-app-authors/submission/)
- [ ] Transfer repository ownership to Flathub team upon review approval
- [ ] Configure automatic builds triggered by GitHub release tags

Primary Documentation: [Flathub Developer Documentation](https://docs.flathub.org/)

## 3. Standalone AppImage

AppImage packages run across any modern Linux distribution without installation or system package manager dependencies.

### Prerequisites
- Build machine with Docker or Ubuntu 22.04 LTS (building on older LTS ensures glibc backward compatibility)
- Tool: [appimage-builder](https://appimage-builder.readthedocs.io/) or [linuxdeploy](https://github.com/linuxdeploy/linuxdeploy) with Qt plugin

### Tasks
- [ ] Create AppImage recipe configuration `AppImageBuilder.yml`:
  - Define AppDir layout with Python 3, PyQt6, and system libraries
  - Specify entrypoint script launching `main.py`
  - Include desktop file `clipvault.desktop` and icon `icon.png`
- [ ] Build AppImage:
  ```bash
  appimage-builder --recipe AppImageBuilder.yml
  ```
- [ ] Test portable binary on multiple distributions:
  - [ ] Ubuntu 22.04 / 24.04
  - [ ] Fedora 40 / 41
  - [ ] Arch Linux
- [ ] Create GitHub Release:
  - Tag git repository (e.g., `git tag v1.0.0 && git push origin v1.0.0`)
  - Upload `ClipVault-1.0.0-x86_64.AppImage` with sha256 checksum
- [ ] Submit to [AppImageHub](https://www.appimagehub.com/):
  - Add AppImage metadata file to [AppImage/appimage.github.io](https://github.com/AppImage/appimage.github.io) for automatic inclusion

Primary Documentation: [AppImage Official Documentation](https://docs.appimage.org/)

## 4. Native Debian / Ubuntu Package (.deb) and Launchpad PPA

Provides native Debian/Ubuntu integration for users who install software via `apt`.

### Prerequisites
- Canonical Launchpad account connected with OpenPGP (GPG) signing key
- Packaging tools: `devscripts`, `debhelper`, `dpkg-dev`

### Tasks
- [ ] Prepare Debian package metadata in `debian/`:
  - `debian/control`: Package name `clipvault-teckscaler`, dependencies (`python3`, `python3-pyqt6`, `python3-pyperclip`, `wl-clipboard`, `xclip`)
  - `debian/rules`: Standard dh sequencer for Python applications
  - `debian/changelog`: Version history and distribution target
- [ ] Build standalone `.deb`:
  ```bash
  dpkg-buildpackage -us -uc -b
  ```
- [ ] Test installation:
  ```bash
  sudo apt install ./clipvault-teckscaler_1.0.0_amd64.deb
  ```
- [ ] Attach `.deb` binary to GitHub Releases
- [ ] Configure Launchpad PPA:
  - Create PPA `ppa:teckscaler/clipvault` at [Launchpad.net](https://launchpad.net/)
  - Build source package: `debuild -S -sa -kYOUR_GPG_KEY_ID`
  - Upload source package to PPA:
    ```bash
    dput ppa:teckscaler/clipvault ../clipvault-teckscaler_1.0.0_source.changes
    ```
  - Verify Launchpad build farm builds binaries for Ubuntu noble (24.04), jammy (22.04)

Primary Documentation: [Debian Packaging Guide](https://www.debian.org/doc/manuals/maint-guide/) and [Launchpad PPA Documentation](https://help.launchpad.net/Packaging/PPA)

## 5. Arch User Repository (AUR)

Reaches the Arch Linux, Manjaro, and EndeavourOS community.

### Prerequisites
- Arch User Repository account at [aur.archlinux.org](https://aur.archlinux.org/)
- SSH key uploaded to AUR profile

### Tasks
- [ ] Create AUR package recipe `PKGBUILD`:
  - Package name: `clipvault-teckscaler` (or `clipvault-bin` if distributing pre-built assets)
  - Dependencies: `python`, `python-pyqt6`, `python-pyperclip`, `wl-clipboard`, `xclip`
  - Source: Points to GitHub release tarball with sha256 checksum
  - Package function: Installs code into `/usr/lib/clipvault-teckscaler/`, symlinks launcher to `/usr/bin/clipvault`, installs desktop entry and icon
- [ ] Generate `.SRCINFO`:
  ```bash
  makepkg --printsrcinfo > .SRCINFO
  ```
- [ ] Test build locally:
  ```bash
  makepkg -si
  ```
- [ ] Publish to AUR:
  ```bash
  git clone ssh://aur@aur.archlinux.org/clipvault-teckscaler.git
  cp PKGBUILD .SRCINFO clipvault-teckscaler/
  cd clipvault-teckscaler
  git add PKGBUILD .SRCINFO
  git commit -m "Release v1.0.0"
  git push origin master
  ```
- [ ] Verify installation via AUR helper:
  ```bash
  yay -S clipvault-teckscaler
  ```

Primary Documentation: [ArchWiki AUR Submission Guidelines](https://wiki.archlinux.org/title/Arch_User_Repository)

## 6. Python Package Index (PyPI / pipx)

Allows Python developers and power users on any distribution to install and execute ClipVault via `pipx`.

### Prerequisites
- PyPI account at [pypi.org](https://pypi.org/) with API token
- Build tools: `python3 -m pip install --upgrade build twine`

### Tasks
- [ ] Verify `pyproject.toml` configuration:
  - Project name: `clipvault-teckscaler`
  - Entry points:
    ```toml
    [project.gui-scripts]
    clipvault = "main:main"
    clipvault-toggle = "main:main"
    ```
- [ ] Build distribution artifacts:
  ```bash
  python3 -m build
  ```
- [ ] Validate distribution packages:
  ```bash
  twine check dist/*
  ```
- [ ] Test on TestPyPI:
  ```bash
  twine upload --repository testpypi dist/*
  pipx run --index-url https://test.pypi.org/simple/ clipvault-teckscaler
  ```
- [ ] Publish to production PyPI:
  ```bash
  twine upload dist/*
  ```
- [ ] Verify public installation:
  ```bash
  pipx run clipvault-teckscaler
  ```

Primary Documentation: [Python Packaging User Guide](https://packaging.python.org/)

## 7. Product Discovery Directories and Communities

Maximizes visibility, search rankings, and initial user feedback.

### Directories
- [ ] [AlternativeTo](https://alternativeto.net/):
  - Submit ClipVault under Clipboard Managers
  - Select alternatives: CopyQ, GPaste, Diodon, Clipman
  - Add tags: Open Source, Linux, Wayland, Privacy, PyQt6
  - Provide website link: `https://www.teckscaler.com`
- [ ] [OpenDesktop / Pling](https://www.opendesktop.org/):
  - Create product listing under Software -> Utilities
  - Upload screenshots, icon, and link to GitHub / Snap / AppImage
- [ ] [GitHub Topics & Badges](https://github.com/rajatpateldm-web/ubuntu-clipboard-manager):
  - Add topics: `clipboard-manager`, `linux`, `wayland`, `x11`, `pyqt6`, `privacy`
  - Add Snap Store badge: `[![Get it from the Snap Store](https://snapcraft.io/static/images/badges/en/snap-store-black.svg)](https://snapcraft.io/clipvault-teckscaler)`

### Community Announcements
- [ ] Product Hunt:
  - Submit product with maker comment describing the privacy problem with standard clipboard tools (password manager credential leaking)
- [ ] Reddit:
  - Share project demo on [r/linux](https://www.reddit.com/r/linux), [r/ubuntu](https://www.reddit.com/r/ubuntu), [r/opensource](https://www.reddit.com/r/opensource)
  - Emphasize the three-tier Wayland/X11 architecture and sensitive content detection
- [ ] Hacker News:
  - Submit Show HN: `Show HN: ClipVault: Privacy-aware Linux clipboard manager with password manager filtering`
