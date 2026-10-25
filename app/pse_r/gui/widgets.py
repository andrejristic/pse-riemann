"""
Shared widgets: markdown rendering with real LaTeX, on a 4 GB budget.

No QtWebEngine. A Chromium instance would cost 400+ MB before showing a single
character, on a machine with about 1.5 GB to spare after Qt and matplotlib. So
markdown is rendered to Qt's own rich text, and the mathematics is rendered by
matplotlib's mathtext into small PNGs that are cached by content hash and
embedded as resources in the document.

That trade is honest about its limits: mathtext is a large subset of LaTeX, not
all of it. Anything it cannot parse is shown as monospace source rather than
silently dropped, so you always see what you wrote.
"""
from __future__ import annotations

import hashlib
import html as _html
import re
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QColor, QDesktopServices, QFont, QImage, QTextDocument
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QTextBrowser, QVBoxLayout, QWidget)

from .. import config

# base point size the markdown renderer sizes headings and math against;
# main_window keeps it in step with the live Ctrl+/Ctrl- zoom
_BASE_PT = [19.0]


def set_base_pt(pt: float) -> None:
    _BASE_PT[0] = float(pt)
    _MATH_CACHE.clear()          # math images were rendered at the old size


_MATH_CACHE: dict[str, QImage] = {}
_FAILED: set[str] = set()

STATUS_COLOR = {
    "COMPUTED": "#2f7a4a", "CITED": "#2f5ea8", "FOLKLORE": "#a8701a",
    "SPECULATION": "#6a4fb0", "SUSPECT": "#b03a3a", "REFUTED": "#4a5568",
}


# --------------------------------------------------------------------------- #
# LaTeX -> QImage via matplotlib mathtext
# --------------------------------------------------------------------------- #
def _render_math(expr: str, display: bool, fg: str = "#e8e8e8",
                 fontsize: float = 0) -> QImage | None:
    fontsize = fontsize or _BASE_PT[0]
    key = hashlib.sha1(f"{expr}|{display}|{fg}|{fontsize}".encode()).hexdigest()
    if key in _MATH_CACHE:
        return _MATH_CACHE[key]
    if key in _FAILED:
        return None
    try:
        import io
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.patch.set_alpha(0.0)
        t = fig.text(0, 0, f"${expr}$", fontsize=fontsize * (1.25 if display else 1.0),
                     color=fg)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=110, transparent=True,
                    bbox_inches="tight", pad_inches=0.02)
        plt.close(fig)
        img = QImage()
        img.loadFromData(buf.getvalue(), "PNG")
        if img.isNull():
            _FAILED.add(key)
            return None
        _MATH_CACHE[key] = img
        if len(_MATH_CACHE) > 400:            # keep the cache bounded on 4 GB
            for k in list(_MATH_CACHE)[:120]:
                _MATH_CACHE.pop(k, None)
        return img
    except Exception:                          # noqa: BLE001 — never break the UI
        _FAILED.add(key)
        return None


_BLOCK_MATH = re.compile(r"\$\$(.+?)\$\$", re.S)
_INLINE_MATH = re.compile(r"(?<!\$)\$([^$\n]+?)\$(?!\$)")
_CODE_FENCE = re.compile(r"```(\w*)\n(.*?)```", re.S)
_WIKILINK = re.compile(r"\[\[([^\]|#]+)(\|([^\]]+))?\]\]")


def markdown_to_html(md: str, doc: QTextDocument | None = None,
                     fg: str = "#e8e8e8") -> str:
    """
    Small, predictable markdown subset: headings, bold/italic, code, lists,
    tables, links, images, wiki-links and math. Deliberately not a full CommonMark
    implementation — the vault's markdown is written by this app and by you, and
    a predictable renderer beats a complete one you cannot debug at 23:00.
    """
    text = md or ""
    placeholders: dict[str, str] = {}

    def _stash(hkey: str, hval: str) -> str:
        placeholders[hkey] = hval
        return hkey

    # code fences first — nothing inside them is markdown
    def _fence(m):
        lang, body = m.group(1), _html.escape(m.group(2))
        key = f"\x00F{len(placeholders)}\x00"
        return _stash(key, f'<pre style="background:#12151b;padding:8px;'
                           f'border-radius:5px;font-size:{_BASE_PT[0]*0.9:.1f}pt;'
                           f'"><code>{body}</code></pre>')
    text = _CODE_FENCE.sub(_fence, text)

    # math -> embedded images
    def _math(m, display):
        expr = m.group(1).strip()
        img = _render_math(expr, display, fg)
        key = f"\x00M{len(placeholders)}\x00"
        if img is None or doc is None:
            return _stash(key, f'<code style="color:#ffcf7a">'
                               f'{_html.escape(expr)}</code>')
        name = f"math{abs(hash(expr)) % 10**9}{int(display)}"
        doc.addResource(QTextDocument.ImageResource, QUrl(name), img)
        style = ("display:block;margin:6px 0;" if display else
                 "vertical-align:middle;")
        return _stash(key, f'<img src="{name}" style="{style}">')

    text = _BLOCK_MATH.sub(lambda m: _math(m, True), text)
    text = _INLINE_MATH.sub(lambda m: _math(m, False), text)

    text = _html.escape(text)

    # images ![alt](path)  — resolved relative to the vault
    def _img(m):
        alt, src = m.group(1), m.group(2)
        p = (config.VAULT / src.lstrip("./")).resolve() if not src.startswith(
            ("http", "file:")) else None
        if p is not None and p.exists():
            return f'<img src="file://{p}" width="640">'
        return f'<i>[{_html.escape(alt)}]</i>'
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _img, text)

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                  r'<a href="\2" style="color:#86b3ff">\1</a>', text)
    text = _WIKILINK.sub(
        lambda m: f'<a href="card:{m.group(1).strip()}" '
                  f'style="color:#74d79a">{m.group(3) or m.group(1)}</a>', text)

    out_lines, in_table, in_list = [], False, False
    for raw in text.split("\n"):
        line = raw.rstrip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            if not in_table:
                out_lines.append('<table cellspacing="0" cellpadding="4" '
                                 'style="border-collapse:collapse">')
                in_table = True
            tag = "td"
            out_lines.append("<tr>" + "".join(
                f'<{tag} style="border:1px solid #262d3a">{c}</{tag}>'
                for c in cells) + "</tr>")
            continue
        if in_table:
            out_lines.append("</table>")
            in_table = False

        h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if h:
            n = len(h.group(1))
            base = _BASE_PT[0]
            size = {1: base * 1.5, 2: base * 1.25, 3: base * 1.1}.get(n, base)
            size = f"{size:.1f}pt"
            out_lines.append(f'<div style="font-size:{size};font-weight:600;'
                             f'margin:10px 0 4px 0">{h.group(2)}</div>')
            continue
        if re.match(r"^\s*[-*]\s+", line):
            if not in_list:
                out_lines.append("<ul style='margin:2px 0 2px 16px'>")
                in_list = True
            out_lines.append("<li>" + re.sub(r"^\s*[-*]\s+", "", line) + "</li>")
            continue
        if in_list:
            out_lines.append("</ul>")
            in_list = False
        if line.startswith("&gt;"):
            out_lines.append(f'<div style="border-left:3px solid #666;'
                             f'padding-left:8px;color:#9aa4b5">{line[4:]}</div>')
            continue
        if re.match(r"^\s*---+\s*$", line):
            out_lines.append("<hr style='border:0;border-top:1px solid #444'>")
            continue
        out_lines.append(line if line else "<br>")
    if in_list:
        out_lines.append("</ul>")
    if in_table:
        out_lines.append("</table>")

    html = "<br>\n".join(out_lines)
    # no line breaks around block elements (lists, headings, tables, rules):
    # a <br> there renders as an empty line and blows lists apart
    _blk = r"(?:ul|/ul|li|div|/div|table|/table|tr|hr)"
    html = re.sub(r"<br>\n(?=<" + _blk + r"\b)", "\n", html)
    html = re.sub(r"(</?" + _blk + r"\b[^>]*>)<br>\n", r"\1\n", html)
    html = re.sub(r"(</li>)<br>\n", r"\1\n", html)
    html = re.sub(r"(?:<br>\s*){2,}", "<br>\n", html)
    html = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", html)
    html = re.sub(r"(?<!\w)\*([^*\n]+)\*(?!\w)", r"<i>\1</i>", html)
    html = re.sub(r"(?<![\w/])_([^_\n]+)_(?![\w/])", r"<i>\1</i>", html)
    html = re.sub(r"`([^`\n]+)`",
                  r'<code style="background:#12151b;padding:1px 3px;'
                  r'border-radius:3px">\1</code>', html)
    for k, v in placeholders.items():
        html = html.replace(k, v)
    base = _BASE_PT[0]
    return (f'<div style="font-family:sans-serif;font-size:{base:.1f}pt;'
            f'line-height:1.5;color:{fg}">{html}</div>')


class MarkdownView(QTextBrowser):
    """Read-only markdown + math. Emits card links via `on_card`."""

    def __init__(self, on_card=None, parent=None):
        super().__init__(parent)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.on_card = on_card
        self.anchorClicked.connect(self._clicked)
        self.setStyleSheet("QTextBrowser{background:#1a1f2b;border:none;}")
        self._md = ""

    def set_markdown(self, md: str) -> None:
        self._md = md or ""
        doc = self.document()
        doc.clear()
        self.setHtml(markdown_to_html(self._md, doc))
        self.verticalScrollBar().setValue(0)     # open at the top, not the bottom

    def rerender(self) -> None:
        """Re-lay-out at the current base size — used by the live zoom."""
        if self._md:
            pos = self.verticalScrollBar().value()
            self.set_markdown(self._md)
            self.verticalScrollBar().setValue(pos)

    def _clicked(self, url: QUrl) -> None:
        s = url.toString()
        if s.startswith("card:") and self.on_card:
            self.on_card(s[5:])
        elif s.startswith(("http://", "https://")):
            QDesktopServices.openUrl(url)


# --------------------------------------------------------------------------- #
def status_chip(status: str) -> QLabel:
    lb = QLabel(status)
    c = STATUS_COLOR.get(status, "#666")
    lb.setStyleSheet(f"background:{c};color:white;border-radius:3px;"
                     f"padding:2px 8px;font-size:{_BASE_PT[0]*0.72:.1f}pt;"
                     f"font-weight:600;")
    lb.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    return lb


def hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet("color:#262d3a;")
    return f


def small(text: str, color: str = "#9aa4b5") -> QLabel:
    """Secondary text. Still scales with the base size — "small" is relative,
    and a fixed 11px is unreadable on a 207-DPI panel."""
    lb = QLabel(text)
    lb.setStyleSheet(f"color:{color};font-size:{_BASE_PT[0]*0.85:.1f}pt;")
    lb.setWordWrap(True)
    return lb


def button(text: str, slot=None, primary: bool = False, kind: str = "") -> QPushButton:
    """Styled by the theme: kind = primary | go | no | '' (Svarog button classes)."""
    b = QPushButton(text)
    k = kind or ("primary" if primary else "")
    if k:
        b.setProperty("kind", k)
    if slot:
        b.clicked.connect(slot)
    return b


DARK_QSS_TMPL = """
QWidget { background:#141414; color:#dcdcdc; font-size:%(fs).1fpt; }
QTabWidget::pane { border:1px solid #2a2a2a; }
QTabBar::tab { background:#1c1c1c; color:#bbb; padding:6px 12px; border:none; }
QTabBar::tab:selected { background:#242424; color:#fff; border-bottom:2px solid #1565c0; }
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background:#1b1b1b; border:1px solid #333; border-radius:4px; padding:4px;
    selection-background-color:#1565c0; }
QListWidget, QTreeWidget, QTableWidget { background:#171717; border:1px solid #2a2a2a; }
QListWidget::item:selected, QTreeWidget::item:selected { background:#1565c0; }
QScrollBar:vertical { background:#141414; width:10px; }
QScrollBar::handle:vertical { background:#333; border-radius:5px; min-height:24px; }
QScrollBar::add-line, QScrollBar::sub-line { height:0; }
/* fat, visible splitter handles: every panel is draggable, and grabbable
   without hunting for a 2px line */
QSplitter::handle { background:#2b2b2b; }
QSplitter::handle:horizontal { width:7px; }
QSplitter::handle:vertical { height:7px; }
QSplitter::handle:hover { background:#1565c0; }
QStatusBar { background:#101010; color:#999; }
QGroupBox { border:1px solid #2a2a2a; border-radius:5px; margin-top:8px; padding-top:8px; }
QGroupBox::title { subcontrol-origin:margin; left:8px; color:#8ab; }
"""


def dark_qss(font_pt: float = 19.0) -> str:
    """The app theme (Svarog look, gui/theme.py). Name kept for old callers."""
    from .theme import qss
    return qss(font_pt)


# kept for callers that don't care about size
DARK_QSS = dark_qss()
