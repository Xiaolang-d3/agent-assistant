"""Controls for the desk notepad window."""

from __future__ import annotations

from datetime import date
from html import escape

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPalette, QPen, QTextOption
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from desktop_app.theme import (
    COPPER,
    COPPER_SOFT,
    CREAM,
    INK,
    MUTE,
    OK,
    PAPER,
    display_font,
    draw_paper_margin,
    draw_talk_disc,
    enable_stylesheet_bg,
    mono_font,
    repolish,
    ui_font,
)

SEARCH_NAMES = {"ddg": "DuckDuckGo", "tavily": "Tavily"}
WEEKDAYS = "一二三四五六日"


class PaperSheet(QWidget):
    """Pad of paper with a copper margin rule."""

    def __init__(self, name: str = "sheet") -> None:
        super().__init__()
        self.setObjectName(name)
        enable_stylesheet_bg(self)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(PAPER))
        draw_paper_margin(painter, self.height())
        del event


class StatusLamp(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(9, 9)
        self._color = QColor(MUTE)
        self._pulse = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)

    def set_state(self, state: str) -> None:
        colors = {
            "ok": QColor(OK),
            "warn": QColor(COPPER_SOFT),
            "listen": QColor(COPPER_SOFT),
            "busy": QColor(OK),
        }
        self._color = colors.get(state, QColor(MUTE))
        if state in {"listen", "busy"}:
            self._timer.start()
        else:
            self._timer.stop()
            self._pulse = 0.0
        self.update()

    def _tick(self) -> None:
        self._pulse = (self._pulse + 0.08) % 1.0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self._color)
        if self._timer.isActive():
            color.setAlphaF(0.45 + 0.55 * abs(0.5 - self._pulse) * 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(0, 0, 9, 9)


class TalkButton(QPushButton):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("talk")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(52, 52)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setToolTip("按住说话")
        self.setAccessibleName("按住说话")
        self._hot = False
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(32)
        self._timer.timeout.connect(self._tick)

    def enterEvent(self, event) -> None:  # noqa: N802
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        super().leaveEvent(event)
        self.update()

    def set_hot(self, hot: bool) -> None:
        self._hot = hot
        if hot:
            self._timer.start()
        else:
            self._timer.stop()
            self._phase = 0.0
        self.update()

    def set_caption(self, text: str) -> None:
        transcribing = text == "转写"
        if transcribing and not self._hot:
            self._timer.start()
        elif not self._hot:
            self._timer.stop()
            self._phase = 0.0
        self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + 0.07) % 1.0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPoint(self.width() // 2, self.height() // 2)
        draw_talk_disc(
            painter,
            center,
            20,
            hot=self._hot or (self.underMouse() and self.isEnabled()),
            phase=self._phase,
            enabled=self.isEnabled(),
        )
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(COPPER), 1, Qt.PenStyle.DotLine))
            painter.drawEllipse(center, 23, 23)


class Mast(QWidget):
    chat_clicked = Signal()
    settings_clicked = Signal()
    new_chat_clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("mast")
        enable_stylesheet_bg(self)
        self.setFixedHeight(58)
        row = QHBoxLayout(self)
        row.setContentsMargins(22, 0, 16, 0)
        row.setSpacing(4)

        brand = QLabel("桌边助理")
        brand.setObjectName("brand")
        brand.setFont(display_font(22))

        self.new_chat_btn = self._link("新对话", "mastQuiet")
        self.new_chat_btn.clicked.connect(self.new_chat_clicked.emit)
        self.chat_btn = self._link("对话", "mastLink")
        self.chat_btn.clicked.connect(self.chat_clicked.emit)
        self.settings_btn = self._link("设置", "mastLink")
        self.settings_btn.clicked.connect(self.settings_clicked.emit)

        status_box = QHBoxLayout()
        status_box.setContentsMargins(8, 0, 0, 0)
        status_box.setSpacing(8)
        self.lamp = StatusLamp()
        self.status = QLabel()
        self.status.setObjectName("status")
        self.status.setFont(mono_font(11))
        self.status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.status.setMaximumWidth(280)
        status_box.addWidget(self.lamp, 0, Qt.AlignmentFlag.AlignVCenter)
        status_box.addWidget(self.status, 0, Qt.AlignmentFlag.AlignVCenter)

        row.addWidget(brand, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)
        row.addWidget(self.new_chat_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.chat_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.settings_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addLayout(status_box, 0)
        self.set_page("chat")

    def _link(self, text: str, name: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName(name)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFont(ui_font(13))
        button.setFlat(True)
        button.setFixedHeight(58)
        enable_stylesheet_bg(button)
        return button

    def set_page(self, page: str) -> None:
        chat = page == "chat"
        self.new_chat_btn.setVisible(chat)
        self.chat_btn.setProperty("active", "true" if chat else "false")
        self.settings_btn.setProperty("active", "true" if page == "settings" else "false")
        repolish(self.chat_btn)
        repolish(self.settings_btn)

    def set_status(self, text: str, state: str) -> None:
        metrics = self.status.fontMetrics()
        self.status.setToolTip(text)
        self.status.setText(metrics.elidedText(text, Qt.TextElideMode.ElideMiddle, 260))
        self.status.setProperty("state", state)
        self.lamp.set_state(state)
        repolish(self.status)


class EmptyMark(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(44, 44)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        draw_talk_disc(painter, QPoint(22, 22), 16)


class EmptyState(PaperSheet):
    def __init__(self) -> None:
        super().__init__("empty")
        col = QVBoxLayout(self)
        col.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        col.setContentsMargins(56, 88, 48, 24)
        col.setSpacing(0)

        self.title = QLabel("说一件要查的事")
        self.title.setObjectName("emptyTitle")
        self.title.setFont(display_font(28))
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.hint = QLabel("按住铜色按钮说话，或直接打字。回车发送。")
        self.hint.setObjectName("emptyHint")
        self.hint.setFont(ui_font(13))
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint.setWordWrap(True)
        self.hint.setMaximumWidth(320)

        col.addWidget(EmptyMark(), 0, Qt.AlignmentFlag.AlignHCenter)
        col.addSpacing(16)
        col.addWidget(self.title)
        col.addSpacing(10)
        col.addWidget(self.hint, 0, Qt.AlignmentFlag.AlignHCenter)

    def set_need_key(self, need_key: bool) -> None:
        if need_key:
            self.title.setText("先填接口密钥")
            self.hint.setText("打开右上角设置，把密钥贴进去。只保存在这台电脑上。")
        else:
            self.title.setText("说一件要查的事")
            self.hint.setText("按住铜色按钮说话，或直接打字。回车发送。")


class DateHead(QWidget):
    def __init__(self) -> None:
        super().__init__()
        today = date.today()
        label = QLabel(f"{today.month}月{today.day}日 星期{WEEKDAYS[today.weekday()]}")
        label.setObjectName("date")
        label.setFont(display_font(13))
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 4)
        box.addWidget(label)


class PromptInput(QPlainTextEdit):
    submitted = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("prompt")
        self.setFont(ui_font(14))
        self.setPlaceholderText("写在这里")
        self.setTabChangesFocus(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._min_h = 54
        self._max_h = 132
        self.setFixedHeight(self._min_h)
        self.textChanged.connect(self._fit_height)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.submitted.emit()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._fit_height()

    def _fit_height(self) -> None:
        doc_h = int(self.document().size().height())
        height = max(self._min_h, min(self._max_h, doc_h + 24))
        bar = Qt.ScrollBarPolicy.ScrollBarAsNeeded if height >= self._max_h else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        self.setVerticalScrollBarPolicy(bar)
        if height != self.height():
            self.setFixedHeight(height)


class BodyCopy(QTextBrowser):
    def __init__(self, text: str, *, kind: str, markdown: bool) -> None:
        super().__init__()
        self.setObjectName("body")
        self.setProperty("kind", kind)
        self.setReadOnly(True)
        self.setOpenExternalLinks(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.viewport().setAutoFillBackground(False)
        self.setFont(ui_font(15))
        self.document().setDocumentMargin(0)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        pal.setColor(QPalette.ColorRole.Text, QColor(INK))
        pal.setColor(QPalette.ColorRole.Highlight, QColor(COPPER))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor(CREAM))
        self.setPalette(pal)
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.document().setDefaultTextOption(option)
        if markdown:
            self.setMarkdown(text)
        else:
            self.setPlainText(text)
        self.document().contentsChanged.connect(self._fit_height)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._fit_height()

    def _fit_height(self) -> None:
        width = max(40, self.viewport().width())
        self.document().setTextWidth(width)
        height = max(22, int(self.document().size().height()) + 2)
        if self.height() != height:
            self.setFixedHeight(height)


class MessageSlip(QWidget):
    def __init__(self, kind: str, text: str, traces: list[dict] | None = None) -> None:
        super().__init__()
        self.kind = kind
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(4)
        align = Qt.AlignmentFlag.AlignRight if kind == "user" else Qt.AlignmentFlag.AlignLeft

        if kind in {"user", "assistant", "error"}:
            who = QLabel({"user": "你", "assistant": "助理", "error": "出错"}[kind])
            who.setObjectName("who")
            who.setFont(display_font(13))
            who.setAlignment(align)
            box.addWidget(who)

        if kind == "assistant":
            self.body = BodyCopy(text, kind=kind, markdown=True)
            box.addWidget(self.body)
        else:
            self.body = QLabel(text)
            self.body.setObjectName("body")
            self.body.setProperty("kind", kind)
            self.body.setFont(display_font(15) if kind == "pending" else ui_font(15))
            self.body.setWordWrap(True)
            self.body.setTextFormat(Qt.TextFormat.PlainText)
            self.body.setAlignment(align)
            self.body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            box.addWidget(self.body)

        if kind == "pending":
            self._pending_base = text.rstrip(".…")
            self._dots = 0
            self._timer = QTimer(self)
            self._timer.setInterval(420)
            self._timer.timeout.connect(self._tick_pending)
            self._timer.start()

        search_steps = [step for step in (traces or []) if step.get("type") == "search"]
        if search_steps:
            traces_box = QWidget()
            traces_box.setObjectName("traces")
            traces_col = QVBoxLayout(traces_box)
            traces_col.setContentsMargins(0, 10, 0, 0)
            traces_col.setSpacing(3)
            heading = QLabel("检索")
            heading.setObjectName("who")
            heading.setFont(display_font(12))
            traces_col.addWidget(heading)
            for step in search_steps:
                query = QLabel(str(step.get("query", "")))
                query.setObjectName("trace")
                query.setFont(mono_font(11))
                query.setWordWrap(True)
                traces_col.addWidget(query)
                for item in (step.get("results") or [])[:3]:
                    url = str(item.get("url") or "")
                    title = escape(str(item.get("title") or url))
                    href = escape(url, quote=True)
                    link = QLabel(f'<a href="{href}">{title}</a>')
                    link.setObjectName("trace")
                    link.setFont(ui_font(13))
                    link.setOpenExternalLinks(True)
                    link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
                    link.setWordWrap(True)
                    traces_col.addWidget(link)
            box.addWidget(traces_box)

    def _tick_pending(self) -> None:
        self._dots = (self._dots + 1) % 4
        self.body.setText(self._pending_base + "." * self._dots)


class MessageRow(QWidget):
    def __init__(self, slip: MessageSlip) -> None:
        super().__init__()
        self.slip = slip
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        if slip.kind == "user":
            row.addStretch(1)
            row.addWidget(slip, 0)
        else:
            row.addWidget(slip, 0)
            row.addStretch(1)

    def set_column_width(self, width: int) -> None:
        cap = max(260, int(width * 0.74))
        if self.slip.kind == "assistant":
            self.slip.setFixedWidth(cap)
        else:
            self.slip.setMaximumWidth(cap)
        body = getattr(self.slip, "body", None)
        if isinstance(body, BodyCopy):
            body._fit_height()


def search_label(backend: str) -> str:
    return SEARCH_NAMES.get(backend, backend)
