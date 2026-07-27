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

from qgis.PyQt.QtCore import QObject, QEvent, Qt, pyqtSignal

from ...dialogstate import DialogStateMachine, DialogState


class KeyPressFilter(QObject):
    centerEditEscape = pyqtSignal()

    def __init__(self, state: DialogStateMachine):
        super().__init__()
        self.state = state

    def eventFilter(self, obj, event):
        # Check if escape was pressed while in state CENTERPOINTSEDIT
        # If so, emit centerEditEscape signal
        if self.state.currentState == DialogState.CENTERPOINTSEDIT:
            if not event or not event.type():
                return False  # let event continue
            if event.type() == QEvent.Type.KeyRelease and event.key():
                if event.key() == Qt.Key.Key_Escape:
                    self.centerEditEscape.emit()
                    return True  # stop propagation (optional)

        return False  # let event continue
