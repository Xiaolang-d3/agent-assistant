"""Visual tokens for the desk notepad window."""

from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication, QWidget

WALNUT = "#2a221c"
PAPER = "#ece8dc"
PAPER_DEEP = "#e3ddce"
INK = "#2c261e"
COPPER = "#c56f3a"
COPPER_DEEP = "#9a4e24"
COPPER_SOFT = "#d08a5c"
MUTE = "#8a8176"
LINE = "#d4cbb8"
LINK = "#2f6f68"
CREAM = "#f7f3ea"
OK = "#6f9a8a"
MARGINALIA = "#6a6358"


STYLESHEET = f"""
QMainWindow, QWidget#root {{
    background: {PAPER};
    color: {INK};
}}
QWidget#mast {{
    background: {WALNUT};
    border-bottom: 1px solid {COPPER};
}}
QWidget#stage, QStackedWidget, QWidget#empty, QWidget#sheet {{
    background: {PAPER};
    border: none;
}}
QScrollArea#logScroll {{
    border: none;
    background: {PAPER};
}}
QWidget#log {{
    background: transparent;
}}
QWidget#composer {{
    background: {PAPER_DEEP};
    border-top: 1px solid {LINE};
}}
QLabel#brand {{
    color: {CREAM};
}}
QLabel#status {{
    color: #c4b8a8;
}}
QLabel#status[state="ok"] {{ color: {OK}; }}
QLabel#status[state="warn"] {{ color: {COPPER_SOFT}; }}
QLabel#status[state="listen"] {{ color: {COPPER_SOFT}; }}
QLabel#status[state="busy"] {{ color: {OK}; }}
QLabel#who {{
    color: {MARGINALIA};
}}
QLabel#date {{
    color: {MUTE};
}}
QLabel#body {{
    color: {INK};
}}
QLabel#body[kind="user"] {{
    color: {COPPER_DEEP};
}}
QLabel#body[kind="pending"] {{
    color: {MUTE};
}}
QLabel#body[kind="error"] {{
    color: {COPPER_DEEP};
}}
QTextBrowser#body {{
    background: transparent;
    color: {INK};
    border: none;
    padding: 0;
    selection-background-color: {COPPER};
    selection-color: {CREAM};
}}
QTextBrowser#body[kind="user"] {{
    color: {COPPER_DEEP};
}}
QLabel#emptyTitle {{
    color: {INK};
}}
QLabel#emptyHint, QLabel#composerHint {{
    color: {MUTE};
}}
QLabel#section {{
    color: {INK};
    padding-bottom: 8px;
    border-bottom: 1px solid {LINE};
}}
QLineEdit#field {{
    background: {CREAM};
    color: {INK};
    border: 1px solid {LINE};
    border-radius: 8px;
    padding: 8px 10px;
    min-height: 22px;
    selection-background-color: {COPPER};
    selection-color: {CREAM};
}}
QLineEdit#field:hover {{
    border: 1px solid #cbbfa8;
}}
QLineEdit#field:focus {{
    border: 1px solid {COPPER};
}}
QComboBox#modelPick {{
    background: {CREAM};
    color: {INK};
    border: 1px solid {LINE};
    border-radius: 8px;
    padding: 6px 8px 6px 10px;
    min-height: 22px;
    selection-background-color: {COPPER};
    selection-color: {CREAM};
}}
QComboBox#modelPick:hover {{
    border: 1px solid #cbbfa8;
}}
QComboBox#modelPick:focus {{
    border: 1px solid {COPPER};
}}
QComboBox#modelPick::drop-down {{
    width: 22px;
    border: none;
    background: transparent;
}}
QComboBox#modelPick QLineEdit {{
    background: {CREAM};
    color: {INK};
    border: none;
    padding: 0;
    selection-background-color: {COPPER};
    selection-color: {CREAM};
}}
QComboBox#modelPick QAbstractItemView {{
    background: {CREAM};
    color: {INK};
    border: 1px solid {LINE};
    selection-background-color: {WALNUT};
    selection-color: {CREAM};
    outline: none;
    padding: 4px 0;
}}
QPushButton#mastLink, QPushButton#mastQuiet {{
    background: transparent;
    color: #c4b8a8;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 0 10px;
    min-width: 44px;
}}
QPushButton#mastLink:hover, QPushButton#mastQuiet:hover {{
    color: {CREAM};
}}
QPushButton#mastLink[active="true"] {{
    color: {CREAM};
    border-bottom: 2px solid {COPPER};
}}
QPushButton#chip {{
    background: transparent;
    color: {INK};
    border: 1px solid {LINE};
    border-radius: 8px;
    padding: 6px 12px;
}}
QPushButton#chip:hover {{
    color: {COPPER_DEEP};
    border: 1px solid {COPPER};
}}
QPushButton#chip[selected="true"] {{
    background: {WALNUT};
    color: {CREAM};
    border: 1px solid {WALNUT};
}}
QPushButton#chip[selected="true"]:hover {{
    background: {WALNUT};
    color: {CREAM};
    border: 1px solid {WALNUT};
}}
QWidget#settings, QWidget#settingsInner, QWidget#settingsHost {{
    background: {PAPER};
}}
QWidget#traces {{
    border-top: 1px solid {LINE};
}}
QLabel#trace {{
    color: {MUTE};
}}
QLabel#trace a {{
    color: {LINK};
    text-decoration: none;
}}
QPlainTextEdit#prompt {{
    background: {CREAM};
    color: {INK};
    border: 1px solid {LINE};
    border-radius: 8px;
    padding: 10px 12px;
    selection-background-color: {COPPER};
    selection-color: {CREAM};
}}
QPlainTextEdit#prompt:focus {{
    border: 1px solid {COPPER};
}}
QPushButton#talk {{
    border: none;
    background: transparent;
}}
QPushButton#send {{
    background: transparent;
    color: {INK};
    border: none;
    padding: 0 8px;
}}
QPushButton#send:hover {{
    color: {COPPER};
}}
QPushButton#send:pressed {{
    color: {COPPER_DEEP};
}}
QPushButton#send:disabled {{
    color: {MUTE};
}}
QPushButton#save {{
    background: {CREAM};
    color: {INK};
    border: 1px solid {LINE};
    border-radius: 8px;
    padding: 0 14px;
}}
QPushButton#save:hover {{
    color: {COPPER};
    border: 1px solid {COPPER};
}}
QPushButton#save:pressed {{
    color: {CREAM};
    background: {COPPER};
    border: 1px solid {COPPER};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: {LINE};
    border-radius: 4px;
    min-height: 28px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
"""


def ui_font(px: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont()
    font.setFamilies(["PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Sans Serif"])
    font.setPixelSize(px)
    font.setWeight(weight)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def display_font(px: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont()
    font.setFamilies(["Songti SC", "STSong", "Noto Serif CJK SC", "Serif"])
    font.setPixelSize(px)
    font.setWeight(weight)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def mono_font(px: int) -> QFont:
    font = QFont()
    font.setFamilies(["Menlo", "Monaco"])
    font.setPixelSize(px)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def enable_stylesheet_bg(widget: QWidget) -> None:
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def draw_paper_margin(painter: QPainter, height: int, x: int = 26) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(COPPER))
    pen.setWidthF(1.2)
    painter.setPen(pen)
    painter.drawLine(x, 0, x, height)
    painter.restore()


def draw_talk_disc(
    painter: QPainter,
    center: QPoint,
    radius: int,
    *,
    hot: bool = False,
    phase: float = 0.0,
    enabled: bool = True,
) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if not enabled:
        painter.setOpacity(0.4)

    if hot:
        halo = QColor(COPPER)
        halo.setAlphaF(0.22)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(halo)
        painter.drawEllipse(center, radius + 5, radius + 5)

    fill = QColor(COPPER_SOFT if hot else COPPER)
    ring = QColor(COPPER_DEEP)
    painter.setPen(QPen(ring, 1.5))
    painter.setBrush(fill)
    painter.drawEllipse(center, radius, radius)

    cream = QColor(CREAM)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(cream)
    bases = (0.42, 0.82, 0.55)
    bar_w = max(2.4, radius * 0.16)
    gap = bar_w * 0.9
    total = bar_w * 3 + gap * 2
    left = center.x() - total / 2
    max_h = radius * 1.05
    for i, base in enumerate(bases):
        wave = 0.18 * math.sin(phase * 2 * math.pi + i * 1.3) if hot else 0.0
        height = max_h * min(1.0, max(0.22, base + wave))
        x = left + i * (bar_w + gap)
        y = center.y() - height / 2
        painter.drawRoundedRect(QRectF(x, y, bar_w, height), 1.6, 1.6)
    painter.restore()


def copper_icon(size: int = 64) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    draw_talk_disc(painter, QPoint(size // 2, size // 2), size // 2 - 3)
    painter.end()
    return QIcon(pixmap)


def apply(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setApplicationName("Agent Assistant")
    app.setOrganizationName("agent-assistant")
    app.setWindowIcon(copper_icon())
    app.setFont(ui_font(14))

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(PAPER))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(INK))
    palette.setColor(QPalette.ColorRole.Base, QColor(CREAM))
    palette.setColor(QPalette.ColorRole.Text, QColor(INK))
    palette.setColor(QPalette.ColorRole.Button, QColor(PAPER_DEEP))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(INK))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COPPER))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(CREAM))
    palette.setColor(QPalette.ColorRole.Link, QColor(LINK))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(MUTE))
    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET)
