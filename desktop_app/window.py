from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.agent import run_agent
from app.config import readiness
from app.transcribe import transcribe_audio
from desktop_app.audio import Recorder
from desktop_app.settings import SettingsPage
from desktop_app.theme import copper_icon, display_font, enable_stylesheet_bg, ui_font
from desktop_app.widgets import (
    DateHead,
    EmptyState,
    Mast,
    MessageRow,
    MessageSlip,
    PaperSheet,
    PromptInput,
    TalkButton,
    search_label,
)
from desktop_app.workers import FnWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("桌边助理")
        self.setWindowIcon(copper_icon())
        self.resize(840, 700)
        self.setMinimumSize(720, 520)

        self.history: list[dict] = []
        self.recorder = Recorder()
        self._thread: QThread | None = None
        self._worker: FnWorker | None = None
        self._on_done = None
        self._busy = False
        self._pending: MessageRow | None = None
        self._rows: list[MessageRow] = []
        self._date_head: DateHead | None = None

        root = QWidget()
        root.setObjectName("root")
        enable_stylesheet_bg(root)
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.mast = Mast()
        self.mast.chat_clicked.connect(self._show_chat)
        self.mast.settings_clicked.connect(self._show_settings)
        self.mast.new_chat_clicked.connect(self._new_chat)
        outer.addWidget(self.mast)

        self.pages = QStackedWidget()
        enable_stylesheet_bg(self.pages)

        stage = QWidget()
        stage.setObjectName("stage")
        enable_stylesheet_bg(stage)
        stage_col = QVBoxLayout(stage)
        stage_col.setContentsMargins(0, 0, 0, 0)
        stage_col.setSpacing(0)

        self.empty = EmptyState()
        self.scroll = QScrollArea()
        self.scroll.setObjectName("logScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.log = PaperSheet("log")
        self.log_layout = QVBoxLayout(self.log)
        self.log_layout.setContentsMargins(44, 22, 28, 18)
        self.log_layout.setSpacing(22)
        self.log_layout.addStretch(1)
        self.scroll.setWidget(self.log)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.empty)
        self.stack.addWidget(self.scroll)

        composer = QWidget()
        composer.setObjectName("composer")
        enable_stylesheet_bg(composer)
        composer_col = QVBoxLayout(composer)
        composer_col.setContentsMargins(20, 12, 16, 12)
        composer_col.setSpacing(6)
        composer_row = QHBoxLayout()
        composer_row.setContentsMargins(0, 0, 0, 0)
        composer_row.setSpacing(8)
        self.input = PromptInput()
        self.talk = TalkButton()
        self.send = QPushButton("发送")
        self.send.setObjectName("send")
        self.send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send.setFont(display_font(17))
        self.send.setAutoDefault(False)
        self.send.setDefault(False)
        self.send.setFixedSize(52, 52)
        self.send.setAccessibleName("发送")
        composer_row.addWidget(self.input, 1)
        composer_row.addWidget(self.talk, 0, Qt.AlignmentFlag.AlignBottom)
        composer_row.addWidget(self.send, 0, Qt.AlignmentFlag.AlignBottom)
        hint = QLabel("回车发送 · Shift+回车换行 · 按住铜色键说话")
        hint.setObjectName("composerHint")
        hint.setFont(ui_font(11))
        composer_col.addLayout(composer_row)
        composer_col.addWidget(hint)

        stage_col.addWidget(self.stack, 1)
        stage_col.addWidget(composer)

        self.settings_page = SettingsPage()
        self.settings_page.saved.connect(self._on_settings_saved)
        self.pages.addWidget(stage)
        self.pages.addWidget(self.settings_page)
        outer.addWidget(self.pages, 1)

        self.send.clicked.connect(self._send)
        self.input.submitted.connect(self._send)
        self.talk.pressed.connect(self._talk_start)
        self.talk.released.connect(self._talk_stop)

        QShortcut(QKeySequence.StandardKey.New, self, self._new_chat)
        QShortcut(QKeySequence("Ctrl+,"), self, self._show_settings)

        self._refresh_status()
        self.input.setFocus()

    def _show_chat(self) -> None:
        self.pages.setCurrentWidget(self.pages.widget(0))
        self.mast.set_page("chat")
        self.input.setFocus()

    def _show_settings(self) -> None:
        self.settings_page.reload_from_config()
        self.pages.setCurrentWidget(self.settings_page)
        self.mast.set_page("settings")

    def _new_chat(self) -> None:
        if self._busy:
            return
        self.history.clear()
        self._clear_pending()
        for row in self._rows:
            self.log_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()
        if self._date_head is not None:
            self.log_layout.removeWidget(self._date_head)
            self._date_head.deleteLater()
            self._date_head = None
        self.stack.setCurrentWidget(self.empty)
        self._show_chat()
        self.input.clear()
        self.input.setFocus()

    def _on_settings_saved(self) -> None:
        self._refresh_status()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._sync_slip_widths()

    def _sync_slip_widths(self) -> None:
        width = max(280, self.scroll.viewport().width() - 48)
        for row in self._rows:
            row.set_column_width(width)

    def _refresh_status(self, state: str | None = None) -> None:
        info = readiness()
        self.empty.set_need_key(not info["llm"])
        if not info["llm"]:
            self.mast.set_status("未配置密钥", "warn")
            return
        if state == "listen":
            self.mast.set_status("正在听…", "listen")
            return
        if state == "transcribe":
            self.mast.set_status("正在转写…", "busy")
            return
        if state == "busy":
            self.mast.set_status("正在查证…", "busy")
            return
        model = info["model"]
        search = search_label(str(info["search"]))
        self.mast.set_status(f"{model}  ·  {search}", "ok")

    def _ensure_date(self) -> None:
        if self._date_head is not None:
            return
        self._date_head = DateHead()
        self.log_layout.insertWidget(0, self._date_head)

    def _add_slip(self, kind: str, text: str, traces: list[dict] | None = None) -> MessageRow:
        self.stack.setCurrentWidget(self.scroll)
        self._ensure_date()
        slip = MessageSlip(kind, text, traces)
        row = MessageRow(slip)
        self._rows.append(row)
        self.log_layout.insertWidget(self.log_layout.count() - 1, row)
        self._sync_slip_widths()
        QTimer.singleShot(0, self._scroll_to_end)
        return row

    def _scroll_to_end(self) -> None:
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _show_pending(self, text: str = "正在查证") -> None:
        self._clear_pending()
        self._pending = self._add_slip("pending", text)

    def _clear_pending(self) -> None:
        if self._pending is None:
            return
        self._rows = [row for row in self._rows if row is not self._pending]
        self.log_layout.removeWidget(self._pending)
        self._pending.deleteLater()
        self._pending = None

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.send.setEnabled(not busy)
        self.talk.setEnabled(not busy)
        self.input.setReadOnly(busy)
        self.mast.new_chat_btn.setEnabled(not busy)

    def _run_async(self, fn, *args, on_done) -> None:
        if self._thread is not None:
            return
        self._on_done = on_done
        self._thread = QThread()
        self._worker = FnWorker(fn, *args)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_worker_ok, Qt.ConnectionType.QueuedConnection)
        self._worker.failed.connect(self._on_worker_err, Qt.ConnectionType.QueuedConnection)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

    @Slot(object)
    def _on_worker_ok(self, result: object) -> None:
        on_done = self._on_done
        self._on_done = None
        if on_done is not None:
            on_done(result)

    @Slot(str)
    def _on_worker_err(self, message: str) -> None:
        self._on_done = None
        self._clear_pending()
        self._add_slip("error", message)
        self._set_busy(False)
        self._refresh_status()

    @Slot()
    def _on_thread_finished(self) -> None:
        worker, thread = self._worker, self._thread
        self._worker = None
        self._thread = None
        if worker is not None:
            worker.deleteLater()
        if thread is not None:
            thread.deleteLater()

    def _stop_worker_thread(self) -> None:
        thread = self._thread
        if thread is None or not thread.isRunning():
            return
        thread.quit()
        if QThread.currentThread() is not thread:
            thread.wait(2000)

    def _send(self) -> None:
        text = self.input.toPlainText().strip()
        if not text or self._busy:
            return
        self.input.clear()
        self._add_slip("user", text)
        self._show_pending()
        self._set_busy(True)
        self._refresh_status("busy")
        self._run_async(run_agent, list(self.history), text, on_done=lambda result: self._on_chat(text, result))

    def _on_chat(self, user_text: str, result: object) -> None:
        data = result if isinstance(result, dict) else {"reply": str(result), "steps": []}
        reply = data.get("reply") or ""
        steps = data.get("steps") or []
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": reply})
        self._clear_pending()
        self._add_slip("assistant", reply, steps)
        self._set_busy(False)
        self._refresh_status()
        self.input.setFocus()

    def _talk_start(self) -> None:
        if self._busy:
            return
        try:
            self.recorder.start()
        except Exception as exc:  # noqa: BLE001
            self._add_slip("error", str(exc))
            return
        self.talk.set_hot(True)
        self._refresh_status("listen")

    def _talk_stop(self) -> None:
        self.talk.set_hot(False)
        path = self.recorder.stop()
        if path is None:
            self._refresh_status()
            return
        self._set_busy(True)
        self.talk.set_caption("转写")
        self._refresh_status("transcribe")
        self._run_async(self._transcribe, path, on_done=self._on_transcript)

    def _transcribe(self, path: Path) -> str:
        try:
            return transcribe_audio(path)
        finally:
            path.unlink(missing_ok=True)

    def _on_transcript(self, result: object) -> None:
        self.talk.set_caption("说话")
        self._set_busy(False)
        self._refresh_status()
        text = str(result or "").strip()
        if text:
            self.input.setPlainText(text)
            self.input.setFocus()
        else:
            self._add_slip("error", "没有听清，请再说一次。")

    def closeEvent(self, event) -> None:  # noqa: N802
        self._stop_worker_thread()
        self.settings_page.stop_fetch()
        super().closeEvent(event)
