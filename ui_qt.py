"""Small Qt widget adapters for English/Persian UI text.

Text translation occurs at construction and on subsequent setters. The original
Qt widget behaviors, signals and object names are retained.
"""
from __future__ import annotations
from PySide6 import QtWidgets as W
from ui_language import tr


def localized_args(args):
    return tuple(tr(v) if isinstance(v, str) else v for v in args)


class QLabel(W.QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*localized_args(args), **kwargs)
    def setText(self, text):
        return super().setText(tr(text))
    def setToolTip(self, text):
        return super().setToolTip(tr(text))


class QPushButton(W.QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*localized_args(args), **kwargs)
    def setText(self, text):
        return super().setText(tr(text))
    def setToolTip(self, text):
        return super().setToolTip(tr(text))


class QCheckBox(W.QCheckBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*localized_args(args), **kwargs)
    def setText(self, text):
        return super().setText(tr(text))


class QComboBox(W.QComboBox):
    def addItem(self, *args, **kwargs):
        return super().addItem(*localized_args(args), **kwargs)
    def setItemText(self, index, text):
        return super().setItemText(index, tr(text))


class QSpinBox(W.QSpinBox):
    def setSpecialValueText(self, text):
        return super().setSpecialValueText(tr(text))
    def setToolTip(self, text):
        return super().setToolTip(tr(text))


class QPlainTextEdit(W.QPlainTextEdit):
    def setPlaceholderText(self, text):
        return super().setPlaceholderText(tr(text))


class QLineEdit(W.QLineEdit):
    def setPlaceholderText(self, text):
        return super().setPlaceholderText(tr(text))


class QTableWidget(W.QTableWidget):
    def setHorizontalHeaderLabels(self, labels):
        return super().setHorizontalHeaderLabels([tr(label) for label in labels])
    def setToolTip(self, text):
        return super().setToolTip(tr(text))


class QTableWidgetItem(W.QTableWidgetItem):
    def setText(self, text):
        return super().setText(tr(text))


class QTabWidget(W.QTabWidget):
    def addTab(self, *args):
        return super().addTab(*localized_args(args))


class QMessageBox(W.QMessageBox):
    @staticmethod
    def information(parent, title, text, *args):
        return W.QMessageBox.information(parent, tr(title), tr(text), *args)
    @staticmethod
    def warning(parent, title, text, *args):
        return W.QMessageBox.warning(parent, tr(title), tr(text), *args)
    @staticmethod
    def question(parent, title, text, *args):
        return W.QMessageBox.question(parent, tr(title), tr(text), *args)
    @staticmethod
    def critical(parent, title, text, *args):
        return W.QMessageBox.critical(parent, tr(title), tr(text), *args)
