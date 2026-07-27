# -*- coding: utf-8 -*-
"""
Copyright (c) 2026 Vision Velo GmbH

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
"""

from typing import Optional
from qgis.PyQt.QtWidgets import QFileDialog
from qgis.PyQt.QtWidgets import QMessageBox


class QtHelper:
    @staticmethod
    def askForLayerDeletion(parent=None) -> bool:
        reply = QMessageBox.question(
            parent,
            "Generierte Layer entfernen",  # Dialog title
            "Wenn Sie diesen Bearbeitungsschritt erneut ausführen, werden nachgelagerte Bearbeitungsschritte gelöscht. Möchten Sie fortfahren?",  # Dialog message
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,  # Buttons
            QMessageBox.StandardButton.No  # Default button
        )

        return reply == QMessageBox.StandardButton.Yes

    Yes = 1
    No = 2
    KeepOldProject = 3

    @staticmethod
    def askForProjectRestart(parent=None) -> int:
        msgBox = QMessageBox(parent=parent, icon=QMessageBox.Icon.Question)
        msgBox.setWindowTitle("Projekt neustarten")
        msgBox.setText(
            "Wenn Sie das Projekt neustarten, werden alle schon erzeugten Daten gelöscht. Möchten Sie fortfahren?")
        msgBox.setIcon
        yesButton = msgBox.addButton("Ja", QMessageBox.ButtonRole.YesRole)
        noButton = msgBox.addButton("Nein", QMessageBox.ButtonRole.NoRole)
        keepOldProjectButton = msgBox.addButton(
            "Projektdaten behalten", QMessageBox.ButtonRole.ActionRole)

        msgBox.exec()
        if msgBox.clickedButton() == yesButton:
            return QtHelper.Yes
        if msgBox.clickedButton() == noButton:
            return QtHelper.No
        if msgBox.clickedButton() == keepOldProjectButton:
            return QtHelper.KeepOldProject

        # reply = QMessageBox.question(
        #     parent,
        #     "Projekt neustarten",  # Dialog title
        #     "Wenn Sie das Projekt neustarten, werden alle schon erzeugten Daten gelöscht. Möchten Sie fortfahren?",  # Dialog message
        #     QMessageBox.Yes | QMessageBox.No |  # Buttons
        #     QMessageBox.No  # Default button
        # )

        # return reply == QMessageBox.Yes

    @staticmethod
    def showInformationBox(parent=None, title: str = "", message: str = ""):
        QMessageBox.information(
            parent,
            title,
            message,
            QMessageBox.StandardButton.Ok,  # Button
            QMessageBox.StandardButton.Ok  # Default button
        )

    @staticmethod
    def showAskBox(parent=None, title: str = "", message: str = "") -> int:
        msgBox = QMessageBox(parent=parent, icon=QMessageBox.Icon.Question)
        msgBox.setWindowTitle(title)
        msgBox.setText(message)
        msgBox.setIcon
        yesButton = msgBox.addButton("Ja", QMessageBox.ButtonRole.YesRole)
        noButton = msgBox.addButton("Nein", QMessageBox.ButtonRole.NoRole)

        msgBox.exec()
        if msgBox.clickedButton() == yesButton:
            return QtHelper.Yes
        if msgBox.clickedButton() == noButton:
            return QtHelper.No

    @staticmethod
    def askForProjectToSaveDirectory(parent=None) -> Optional[str]:
        """Open folder dialog and get selected folder"""
        directoryPath = QFileDialog.getExistingDirectory(
            parent,
            "Ordner auswählen",
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )

        return directoryPath
