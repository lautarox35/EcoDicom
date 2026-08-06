"""Formulario de datos del paciente veterinario."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.patient import Patient


class PatientForm(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        basic = QGroupBox("Paciente — datos básicos")
        basic_form = QFormLayout(basic)

        self.animal_name = QLineEdit()
        self.patient_id = QLineEdit()
        self.species = QLineEdit()
        self.species.setPlaceholderText("Ej. Canino, Felino, Equino")
        self.breed = QLineEdit()
        self.sex = QComboBox()
        self.sex.addItems(["", "M (Macho)", "F (Hembra)", "O (Otro)", "U (Desconocido)"])
        self.owner = QLineEdit()

        basic_form.addRow("Nombre del animal", self.animal_name)
        basic_form.addRow("ID paciente", self.patient_id)
        basic_form.addRow("Especie", self.species)
        basic_form.addRow("Raza", self.breed)
        basic_form.addRow("Sexo", self.sex)
        basic_form.addRow("Propietario", self.owner)
        layout.addWidget(basic)

        self.more_box = QGroupBox("Más datos (opcional)")
        self.more_box.setCheckable(True)
        self.more_box.setChecked(False)
        more_form = QFormLayout(self.more_box)

        self.age = QLineEdit()
        self.age.setPlaceholderText("Ej. 5 años")
        self.weight = QDoubleSpinBox()
        self.weight.setRange(0.0, 2000.0)
        self.weight.setDecimals(2)
        self.weight.setSuffix(" kg")
        self.weight.setSpecialValueText("—")
        self.veterinarian = QLineEdit()
        self.clinic = QLineEdit()
        self.birth_date = QLineEdit()
        self.birth_date.setPlaceholderText("YYYYMMDD (opcional)")

        more_form.addRow("Edad", self.age)
        more_form.addRow("Peso", self.weight)
        more_form.addRow("Veterinario", self.veterinarian)
        more_form.addRow("Clínica", self.clinic)
        more_form.addRow("Fecha nacimiento", self.birth_date)
        layout.addWidget(self.more_box)
        layout.addStretch(1)

        self.more_box.toggled.connect(self._set_more_visible)
        self._set_more_visible(False)

    def _set_more_visible(self, checked: bool) -> None:
        form = self.more_box.layout()
        if form is None:
            return
        for i in range(form.rowCount()):
            for role in (
                QFormLayout.ItemRole.LabelRole,
                QFormLayout.ItemRole.FieldRole,
            ):
                item = form.itemAt(i, role)
                if item and item.widget():
                    item.widget().setVisible(checked)

    def _sex_value(self) -> str:
        text = self.sex.currentText()
        if text.startswith("M"):
            return "M"
        if text.startswith("F"):
            return "F"
        if text.startswith("O"):
            return "O"
        if text.startswith("U"):
            return "U"
        return ""

    def get_patient(self) -> Patient:
        weight_val = self.weight.value()
        return Patient(
            animal_name=self.animal_name.text().strip(),
            patient_id=self.patient_id.text().strip(),
            species=self.species.text().strip(),
            breed=self.breed.text().strip(),
            sex=self._sex_value(),
            age=self.age.text().strip(),
            weight_kg=weight_val if weight_val > 0 else None,
            owner=self.owner.text().strip(),
            veterinarian=self.veterinarian.text().strip(),
            clinic=self.clinic.text().strip(),
            birth_date=self.birth_date.text().strip(),
        )

    def set_patient(self, patient: Patient) -> None:
        self.animal_name.setText(patient.animal_name)
        self.patient_id.setText(patient.patient_id)
        self.species.setText(patient.species)
        self.breed.setText(patient.breed)
        sex_map = {"M": 1, "F": 2, "O": 3, "U": 4}
        self.sex.setCurrentIndex(sex_map.get(patient.sex, 0))
        self.age.setText(patient.age)
        self.weight.setValue(patient.weight_kg or 0.0)
        self.owner.setText(patient.owner)
        self.veterinarian.setText(patient.veterinarian)
        self.clinic.setText(patient.clinic)
        self.birth_date.setText(patient.birth_date)
        has_extra = bool(
            patient.age
            or patient.weight_kg
            or patient.veterinarian
            or patient.clinic
            or patient.birth_date
        )
        self.more_box.setChecked(has_extra)
