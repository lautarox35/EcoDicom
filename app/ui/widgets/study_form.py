"""Formulario de datos del estudio."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.study import STUDY_TYPE_CHOICES, Study


class StudyForm(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._study_uid = ""
        self._series_uid = ""
        self._build()

    def _build(self) -> None:
        group = QGroupBox("Estudio")
        form = QFormLayout(group)

        self.datetime_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")

        self.study_type = QComboBox()
        self.study_type.addItems(STUDY_TYPE_CHOICES)

        self.organ = QLineEdit()
        self.organ.setPlaceholderText("Ej. Hígado, Útero, Corazón")

        self.observations = QTextEdit()
        self.observations.setPlaceholderText("Observaciones clínicas...")
        self.observations.setMaximumHeight(140)

        form.addRow("Fecha y hora", self.datetime_edit)
        form.addRow("Tipo de estudio", self.study_type)
        form.addRow("Órgano evaluado", self.organ)
        form.addRow("Observaciones", self.observations)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(group)
        layout.addStretch(1)

    def get_study(self) -> Study:
        qd = self.datetime_edit.dateTime()
        qt_dt = datetime(
            qd.date().year(),
            qd.date().month(),
            qd.date().day(),
            qd.time().hour(),
            qd.time().minute(),
            qd.time().second(),
        )
        return Study(
            study_datetime=qt_dt,
            study_type=self.study_type.currentText(),
            organ=self.organ.text().strip(),
            observations=self.observations.toPlainText().strip(),
            study_instance_uid=self._study_uid,
            series_instance_uid=self._series_uid,
        )

    def set_uids(self, study_uid: str, series_uid: str) -> None:
        self._study_uid = study_uid
        self._series_uid = series_uid
