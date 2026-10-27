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

from ..i18n import tr

import hashlib
import html as _html
import re
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QColor, QDesktopServices, QFont, QImage, QTextDocument
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QSizePolicy, QTextBrowser, QVBoxLayout, QWidget)

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


# --------------------------------------------------------------------------- #
# screen fitting: rows that wrap instead of forcing the window wider than the screen
# --------------------------------------------------------------------------- #
from PySide6.QtCore import QPoint, QRect, QSize      # noqa: E402
from PySide6.QtWidgets import QLayout, QSizePolicy as _SP, QWidgetItem  # noqa: E402,F401


class FlowLayout(QLayout):
    """Left-to-right row that wraps to the next line when it runs out of width."""

    def __init__(self, parent=None, spacing: int = 6):
        super().__init__(parent)
        self._items = []
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return self._do(QRect(0, 0, w, 0), True)

    def setGeometry(self, r):
        super().setGeometry(r)
        self._do(r, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        s = QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return s + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do(self, r, test):
        m = self.contentsMargins()
        eff = r.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line = eff.x(), eff.y(), 0
        sp = self.spacing()
        for it in self._items:
            if it.widget() is not None and it.widget().isHidden():
                continue
            hint = it.sizeHint()
            nx = x + hint.width() + sp
            if nx - sp > eff.right() + 1 and line > 0:
                x, y = eff.x(), y + line + sp
                nx, line = x + hint.width() + sp, 0
            if not test:
                it.setGeometry(QRect(QPoint(x, y), hint))
            x, line = nx, max(line, hint.height())
        return y + line - r.y() + m.bottom()


def flow_row(*widgets, spacing: int = 6) -> QWidget:
    """A wrapping row of widgets (buttons, labels, combos)."""
    w = QWidget()
    lay = FlowLayout(w, spacing)
    for x in widgets:
        lay.addWidget(x)
    sp = w.sizePolicy()
    sp.setHeightForWidth(True)
    w.setSizePolicy(sp)
    return w


def scroll_wrap(page: QWidget) -> QScrollArea:
    """Put a tab page in a frameless scroll area: a narrow screen scrolls the page
    instead of pushing the whole window wider than the screen."""
    sa = QScrollArea()
    sa.setFrameShape(QFrame.NoFrame)
    sa.setWidgetResizable(True)
    sa.setWidget(page)
    sa.setMinimumWidth(1)
    return sa


def short_combo(cb, chars: int = 18) -> None:
    """A combo whose width does not follow its longest entry (long mission titles)."""
    from PySide6.QtWidgets import QComboBox
    cb.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    cb.setMinimumContentsLength(chars)


# --------------------------------------------------------------------------- #
# ⤢ / ⤡ on every panel where it makes sense (Andrej, 2026-10-26)
# --------------------------------------------------------------------------- #
from PySide6.QtCore import QEvent, QObject  # noqa: E402


class _CornerKeeper(QObject):
    """Keeps a small button in the top-right corner of its panel."""

    def __init__(self, pane, btn):
        super().__init__(pane)
        self.pane, self.btn = pane, btn

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.Resize, QEvent.Show):
            self.place()
        return False

    def place(self):
        sb = 0
        vsb = getattr(self.pane, "verticalScrollBar", None)
        if vsb is not None and vsb() is not None and vsb().isVisible():
            sb = vsb().width()
        self.btn.adjustSize()
        self.btn.move(max(0, self.pane.width() - self.btn.width() - sb - 4), 4)
        self.btn.raise_()


def add_expand(pane, siblings) -> QPushButton:
    """A ⤢ in the panel's corner: the panel takes the place of its `siblings`
    (they are hidden); ⤡ brings them back."""
    b = QPushButton("⤢", pane)
    b.setObjectName("expandBtn")
    b.setToolTip(tr("raširi ovaj panel (ponovo = vrati)"))
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet("QPushButton#expandBtn { padding:0px 6px; min-width:0px; border-radius:6px;"
                    " background:rgba(34,42,55,0.85); }")
    state = {"on": False, "hidden": []}

    def toggle():
        if state["on"]:
            for w in state["hidden"]:
                w.show()
            state["on"], state["hidden"] = False, []
            b.setText("⤢")
        else:
            # isHidden(): what is shown in its own place, even inside a tab not on screen
            state["hidden"] = [w for w in siblings() if w is not pane and not w.isHidden()]
            for w in state["hidden"]:
                w.hide()
            state["on"] = True
            b.setText("⤡")
    b.clicked.connect(toggle)
    keeper = _CornerKeeper(pane, b)
    pane.installEventFilter(keeper)
    keeper.place()
    pane.setProperty("has_expand", True)
    return b


def expand_splitter(splitter, skip=()) -> list:
    """Give every panel of a splitter its own ⤢ (panels that already have one are skipped)."""
    out = []
    for i in range(splitter.count()):
        w = splitter.widget(i)
        from PySide6.QtWidgets import QSplitter as _QS
        if w in skip or w.property("has_expand") or isinstance(w, _QS):
            continue                                    # a nested splitter's panes have their own
        out.append(add_expand(w, lambda sp=splitter: [sp.widget(j) for j in range(sp.count())]))
    return out
