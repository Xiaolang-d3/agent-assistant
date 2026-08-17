"""Settings page for keys, model, and search."""

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.config import current_settings, save_settings
from app.models import list_models
from desktop_app.theme import display_font, enable_stylesheet_bg, ui_font
from desktop_app.workers import FnWorker


SEARCH_CHOICES = (
    ("auto", "自动"),
    ("ddg", "DuckDuckGo"),
    ("tavily", "Tavily"),
)


class ChoiceRow(QWidget):
    changed = Signal(str)

    def __init__(self, choices: tuple[tuple[str, str], ...]) -> None:
        super().__init__()
        self._value = choices[0][0]
        self._buttons: dict[str, QPushButton] = {}
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        for value, label in choices:
            button = QPushButton(label)
            button.setObjectName("chip")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFont(ui_font(13))
            button.setCheckable(False)
            enable_stylesheet_bg(button)
            button.clicked.connect(lambda _checked=False, item=value: self.set_value(item, notify=True))
            self._buttons[value] = button
            row.addWidget(button, 0)
        row.addStretch(1)

    def value(self) -> str:
        return self._value

    def set_value(self, value: str, notify: bool = False) -> None:
        if value not in self._buttons:
            value = next(iter(self._buttons))
        self._value = value
        for key, button in self._buttons.items():
            button.setProperty("selected", "true" if key == value else "false")
            button.style().unpolish(button)
            button.style().polish(button)
        if notify:
            self.changed.emit(value)


class ModelPick(QComboBox):
    """Ignore wheel so scrolling the settings page cannot change the model."""

    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


class SettingsPage(QWidget):
    saved = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("settings")
        enable_stylesheet_bg(self)

        scroll = QScrollArea()
        scroll.setObjectName("logScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        enable_stylesheet_bg(scroll)

        inner = QWidget()
        inner.setObjectName("settingsInner")
        enable_stylesheet_bg(inner)
        inner.setMaximumWidth(560)
        inner.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        form = QVBoxLayout(inner)
        form.setContentsMargins(8, 28, 8, 24)
        form.setSpacing(0)
        form.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("设置")
        title.setObjectName("emptyTitle")
        title.setFont(display_font(28))
        form.addWidget(title)
        form.addSpacing(6)
        intro = QLabel("密钥只保存在本机的 .env，不会上传。")
        intro.setObjectName("emptyHint")
        intro.setFont(ui_font(13))
        intro.setWordWrap(True)
        form.addWidget(intro)
        form.addSpacing(28)

        form.addWidget(self._heading("接口"))
        form.addSpacing(12)
        self.api_key = self._add_field(form, "密钥", secret=True, placeholder="OPENAI_API_KEY")
        form.addSpacing(16)
        self.base_url = self._add_field(
            form,
            "网关",
            hint="兼容 OpenAI 的接口，建议带 /v1。例如 https://www.packyapi.ai/v1",
            placeholder="https://api.openai.com/v1",
        )
        form.addSpacing(16)
        self._add_model_row(form)
        form.addSpacing(28)

        form.addWidget(self._heading("搜索"))
        form.addSpacing(12)
        search_label = QLabel("来源")
        search_label.setObjectName("who")
        search_label.setFont(display_font(14))
        form.addWidget(search_label)
        form.addSpacing(8)
        self.search = ChoiceRow(SEARCH_CHOICES)
        form.addWidget(self.search)
        form.addSpacing(16)
        self.tavily_key = self._add_field(
            form,
            "Tavily 密钥",
            secret=True,
            hint="选 Tavily 或自动且填了密钥时使用。",
            placeholder="可选",
        )
        form.addStretch(1)

        host = QWidget()
        host.setObjectName("settingsHost")
        enable_stylesheet_bg(host)
        host_col = QVBoxLayout(host)
        host_col.setContentsMargins(36, 0, 36, 0)
        host_col.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        host_col.addWidget(inner)
        scroll.setWidget(host)

        footer = QWidget()
        footer.setObjectName("composer")
        enable_stylesheet_bg(footer)
        actions = QHBoxLayout(footer)
        actions.setContentsMargins(36, 12, 20, 16)
        self.note = QLabel("")
        self.note.setObjectName("emptyHint")
        self.note.setFont(ui_font(13))
        self.save = QPushButton("保存")
        self.save.setObjectName("save")
        self.save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save.setFont(display_font(16))
        self.save.setFixedSize(88, 44)
        enable_stylesheet_bg(self.save)
        self.save.clicked.connect(self._save)
        actions.addWidget(self.note, 1)
        actions.addWidget(self.save, 0)

        page = QVBoxLayout(self)
        page.setContentsMargins(0, 0, 0, 0)
        page.setSpacing(0)
        page.addWidget(scroll, 1)
        page.addWidget(footer)

        self._thread: QThread | None = None
        self._worker: FnWorker | None = None
        self.reload_from_config()

    def _heading(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("section")
        label.setFont(display_font(18))
        enable_stylesheet_bg(label)
        return label

    def _add_model_row(self, form: QVBoxLayout) -> None:
        caption = QLabel("模型")
        caption.setObjectName("who")
        caption.setFont(display_font(14))
        form.addWidget(caption)
        form.addSpacing(6)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.model = ModelPick()
        self.model.setObjectName("modelPick")
        self.model.setEditable(True)
        self.model.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.model.setFont(ui_font(14))
        self.model.setMaxVisibleItems(16)
        self.model.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.model.setMinimumContentsLength(12)
        self.fetch = QPushButton("获取列表")
        self.fetch.setObjectName("chip")
        self.fetch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fetch.setFont(ui_font(13))
        self.fetch.setFixedHeight(38)
        enable_stylesheet_bg(self.fetch)
        self.fetch.clicked.connect(self._fetch_models)
        row.addWidget(self.model, 1)
        row.addWidget(self.fetch, 0)
        form.addLayout(row)
        hint = QLabel("从当前密钥和网关拉取可用模型。没写 /v1 时会自动补上。")
        hint.setObjectName("emptyHint")
        hint.setFont(ui_font(12))
        hint.setWordWrap(True)
        form.addSpacing(6)
        form.addWidget(hint)

    def _add_field(
        self,
        form: QVBoxLayout,
        label: str,
        *,
        secret: bool = False,
        hint: str = "",
        placeholder: str = "",
    ) -> QLineEdit:
        caption = QLabel(label)
        caption.setObjectName("who")
        caption.setFont(display_font(14))
        edit = QLineEdit()
        edit.setObjectName("field")
        edit.setFont(ui_font(14))
        edit.setClearButtonEnabled(True)
        if secret:
            edit.setEchoMode(QLineEdit.EchoMode.Password)
        if placeholder:
            edit.setPlaceholderText(placeholder)
        form.addWidget(caption)
        form.addSpacing(6)
        form.addWidget(edit)
        if hint:
            note = QLabel(hint)
            note.setObjectName("emptyHint")
            note.setFont(ui_font(12))
            note.setWordWrap(True)
            form.addSpacing(6)
            form.addWidget(note)
        return edit

    def reload_from_config(self) -> None:
        values = current_settings()
        self.api_key.setText(values["OPENAI_API_KEY"])
        self.base_url.setText(values["OPENAI_BASE_URL"])
        self._set_model_items(values["OPENAI_MODEL"] or "gpt-4o-mini")
        self.search.set_value(values["SEARCH_PROVIDER"] or "auto")
        self.tavily_key.setText(values["TAVILY_API_KEY"])
        self.note.setText("")

    def _set_model_items(self, current: str, names: list[str] | None = None) -> None:
        current = (current or "").strip()
        items = list(names or [])
        if current and current not in items:
            items.insert(0, current)
        if not items:
            items = ["gpt-4o-mini"]
        self.model.blockSignals(True)
        self.model.clear()
        self.model.addItems(items)
        self.model.setCurrentText(current or items[0])
        self.model.blockSignals(False)

    def _model_name(self) -> str:
        return self.model.currentText().strip() or "gpt-4o-mini"

    def _fetch_models(self) -> None:
        if self._thread is not None:
            return
        self.fetch.setEnabled(False)
        self.fetch.setText("获取中…")
        self.note.setText("正在获取模型列表…")
        self._thread = QThread()
        self._worker = FnWorker(list_models, self.api_key.text(), self.base_url.text())
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_models, Qt.ConnectionType.QueuedConnection)
        self._worker.failed.connect(self._on_models_failed, Qt.ConnectionType.QueuedConnection)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._on_fetch_thread_finished)
        self._thread.start()

    @Slot(object)
    def _on_models(self, result: object) -> None:
        names: list[str] = []
        resolved = ""
        if isinstance(result, dict):
            names = [str(item) for item in (result.get("models") or []) if str(item).strip()]
            resolved = str(result.get("base_url") or "").strip()
        elif isinstance(result, list):
            names = [str(item) for item in result if str(item).strip()]
        self._set_model_items(self._model_name(), names)
        if resolved and resolved != self.base_url.text().strip():
            self.base_url.setText(resolved)
        self.note.setText(f"已获取 {len(names)} 个模型")
        self.fetch.setEnabled(True)
        self.fetch.setText("获取列表")

    @Slot(str)
    def _on_models_failed(self, message: str) -> None:
        text = (message or "获取失败").split("\n", 1)[0][:180]
        self.note.setText(text)
        self.fetch.setEnabled(True)
        self.fetch.setText("获取列表")

    @Slot()
    def _on_fetch_thread_finished(self) -> None:
        worker, thread = self._worker, self._thread
        self._worker = None
        self._thread = None
        if worker is not None:
            worker.deleteLater()
        if thread is not None:
            thread.deleteLater()

    def stop_fetch(self) -> None:
        thread = self._thread
        if thread is None or not thread.isRunning():
            return
        thread.quit()
        if QThread.currentThread() is not thread:
            thread.wait(2000)
        self.fetch.setEnabled(True)
        self.fetch.setText("获取列表")

    def _save(self) -> None:
        save_settings(
            {
                "OPENAI_API_KEY": self.api_key.text(),
                "OPENAI_MODEL": self._model_name(),
                "OPENAI_BASE_URL": self.base_url.text(),
                "SEARCH_PROVIDER": self.search.value(),
                "TAVILY_API_KEY": self.tavily_key.text(),
            }
        )
        self.note.setText("已保存到本机 .env")
        self.saved.emit()
