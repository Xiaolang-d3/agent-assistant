from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.agent import run_agent
from app.config import readiness
from app.transcribe import transcribe_audio
from desktop_app.audio import Recorder
from desktop_app.workers import FnWorker

STYLES = """
QMainWindow, QWidget#root {
    background: #1a2229;
    color: #e8dfd0;
}
QLabel#eyebrow {
    color: #7eb8c9;
    font-size: 11px;
    letter-spacing: 2px;
}
QLabel#title {
    color: #e8dfd0;
    font-size: 22px;
    font-weight: 700;
}
QLabel#status {
    color: #8a9199;
    font-size: 12px;
}
QLabel#status[state="ok"] { color: #7eb8c9; }
QLabel#status[state="warn"] { color: #c4845a; }
QScrollArea {
    border: none;
    background: #243039;
}
QWidget#log {
    background: #243039;
}
QFrame#bubble {
    background: #1f2a31;
    border: 1px solid #334049;
    padding: 10px 12px;
}
QFrame#bubble[kind="user"] {
    background: #2d3942;
}
QLabel#who {
    color: #8a9199;
    font-size: 11px;
}
QLabel#body, QLabel#trace {
    color: #e8dfd0;
}
QLabel#trace { color: #7eb8c9; font-size: 12px; }
QPlainTextEdit {
    background: #1a2229;
    color: #e8dfd0;
    border: 1px solid #334049;
    padding: 8px;
    font-size: 14px;
}
QPushButton#send {
    background: #c4845a;
    color: #1a120c;
    border: none;
    padding: 10px 16px;
    font-weight: 700;
}
QPushButton#talk {
    background: #2a1f18;
    color: #e8dfd0;
    border: none;
    padding: 10px 16px;
}
QPushButton#talk[hot="true"] {
    background: #3a261b;
}
QPushButton:disabled { opacity: 0.5; }
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Agent Assistant")
        self.resize(880, 640)
        self.setStyleSheet(STYLES)

        self.history: list[dict] = []
        self.recorder = Recorder()
        self._thread: QThread | None = None
        self._worker: FnWorker | None = None
        self._busy = False

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(20, 16, 20, 16)
        titles = QVBoxLayout()
        eyebrow = QLabel("DESK INTERCOM")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Agent Assistant")
        title.setObjectName("title")
        title.setFont(QFont("PingFang SC", 22, QFont.Weight.Bold))
        titles.addWidget(eyebrow)
        titles.addWidget(title)
        self.status = QLabel()
        self.status.setObjectName("status")
        self.status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_row.addLayout(titles, 1)
        header_row.addWidget(self.status, 0)
        layout.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.log = QWidget()
        self.log.setObjectName("log")
        self.log_layout = QVBoxLayout(self.log)
        self.log_layout.setContentsMargins(20, 12, 20, 12)
        self.log_layout.setSpacing(10)
        self.log_layout.addStretch(1)
        self.scroll.setWidget(self.log)
        layout.addWidget(self.scroll, 1)

        composer = QWidget()
        composer_row = QHBoxLayout(composer)
        composer_row.setContentsMargins(20, 12, 20, 16)
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("问一件需要查的事，或按住说话")
        self.input.setFixedHeight(72)
        buttons = QVBoxLayout()
        self.talk = QPushButton("按住说话")
        self.talk.setObjectName("talk")
        self.send = QPushButton("发送")
        self.send.setObjectName("send")
        buttons.addWidget(self.talk)
        buttons.addWidget(self.send)
        composer_row.addWidget(self.input, 1)
        composer_row.addLayout(buttons)
        layout.addWidget(composer)

        self.send.clicked.connect(self._send)
        self.talk.pressed.connect(self._talk_start)
        self.talk.released.connect(self._talk_stop)

        self._add_bubble(
            "system",
            "这是原生桌面窗口。按住说话或打字；需要查证时会先上网再回答。",
        )
        self._refresh_status()
        self.input.setFocus()

    def _refresh_status(self) -> None:
        info = readiness()
        if not info["llm"]:
            self.status.setText("未配置 OPENAI_API_KEY")
            self.status.setProperty("state", "warn")
        else:
            self.status.setText(f"{info['model']} · 搜索 {info['search']}")
            self.status.setProperty("state", "ok")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def _add_bubble(self, kind: str, text: str, traces: list[dict] | None = None) -> None:
        frame = QFrame()
        frame.setObjectName("bubble")
        frame.setProperty("kind", kind)
        box = QVBoxLayout(frame)
        who = QLabel("You" if kind == "user" else "Assistant")
        who.setObjectName("who")
        body = QLabel(text)
        body.setObjectName("body")
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        box.addWidget(who)
        box.addWidget(body)
        for step in traces or []:
            if step.get("type") != "search":
                continue
            line = QLabel(f"搜索：{step.get('query', '')}")
            line.setObjectName("trace")
            line.setWordWrap(True)
            box.addWidget(line)
            for item in (step.get("results") or [])[:3]:
                url = item.get("url") or ""
                title = item.get("title") or url
                link = QLabel(f'<a href="{url}">{title}</a>')
                link.setObjectName("trace")
                link.setOpenExternalLinks(True)
                link.setWordWrap(True)
                box.addWidget(link)

        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        # insert before the stretch
        self.log_layout.insertWidget(self.log_layout.count() - 1, frame)
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.send.setEnabled(not busy)
        self.talk.setEnabled(not busy)
        self.input.setReadOnly(busy)

    def _run_async(self, fn, *args, on_done) -> None:
        if self._thread is not None:
            return
        self._thread = QThread()
        self._worker = FnWorker(fn, *args)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)

        def _ok(result: object) -> None:
            on_done(result)
            self._cleanup_thread()

        def _err(message: str) -> None:
            self._add_bubble("assistant", message)
            self._set_busy(False)
            self._cleanup_thread()

        self._worker.finished.connect(_ok)
        self._worker.failed.connect(_err)
        self._thread.start()

    def _cleanup_thread(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        self._thread = None
        self._worker = None

    def _send(self) -> None:
        text = self.input.toPlainText().strip()
        if not text or self._busy:
            return
        self.input.clear()
        self._add_bubble("user", text)
        self._set_busy(True)
        self._run_async(run_agent, list(self.history), text, on_done=lambda result: self._on_chat(text, result))

    def _on_chat(self, user_text: str, result: object) -> None:
        data = result if isinstance(result, dict) else {"reply": str(result), "steps": []}
        reply = data.get("reply") or ""
        steps = data.get("steps") or []
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": reply})
        self._add_bubble("assistant", reply, steps)
        self._set_busy(False)
        self.input.setFocus()

    def _talk_start(self) -> None:
        if self._busy:
            return
        try:
            self.recorder.start()
        except Exception as exc:  # noqa: BLE001
            self._add_bubble("assistant", str(exc))
            return
        self.talk.setText("松手结束")
        self.talk.setProperty("hot", "true")
        self.talk.style().unpolish(self.talk)
        self.talk.style().polish(self.talk)

    def _talk_stop(self) -> None:
        self.talk.setText("按住说话")
        self.talk.setProperty("hot", "false")
        self.talk.style().unpolish(self.talk)
        self.talk.style().polish(self.talk)
        path = self.recorder.stop()
        if path is None:
            return
        self._set_busy(True)
        self.talk.setText("转写中…")
        self._run_async(self._transcribe, path, on_done=self._on_transcript)

    def _transcribe(self, path: Path) -> str:
        try:
            return transcribe_audio(path)
        finally:
            path.unlink(missing_ok=True)

    def _on_transcript(self, result: object) -> None:
        self.talk.setText("按住说话")
        self._set_busy(False)
        text = str(result or "").strip()
        if text:
            self.input.setPlainText(text)
            self.input.setFocus()
        else:
            self._add_bubble("assistant", "没有听清，请再说一次。")

    def closeEvent(self, event) -> None:  # noqa: N802
        self._cleanup_thread()
        super().closeEvent(event)
