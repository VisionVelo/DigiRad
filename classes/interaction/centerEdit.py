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

from enum import Enum

from qgis.core import QgsMapLayer
from qgis.gui import (
    QgsMapToolIdentifyFeature,
    QgsAttributeDialog,
    QgsAttributeEditorContext,
)

class CenterEditFeatureHandler:
    """Simpler approach using the featureIdentified signal"""

    def __init__(self, iface, layer: QgsMapLayer):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.identify_tool = None
        self.layer = layer
        self.toolType = None
        self.identifyTool = QgsMapToolIdentifyFeature(self.canvas, self.layer)
        self.identifyTool.featureIdentified.connect(self.onFeatureIdentified)
        self.previousTool = self.canvas.mapTool()

    def setTool(self, toolType: 'CenterEditToolType'):
        self.toolType = toolType

        if self.toolType == CenterEditToolType.MoveGeometry:
            self.startMoveFeature()
        elif self.toolType == CenterEditToolType.AddFeature:
            self.addFeature()
        else:
            self.canvas.setMapTool(self.identifyTool)

    def restore(self):
        if self.previousTool:
            self.canvas.setMapTool(self.previousTool)
        self.toolType = None

    def onFeatureIdentified(self, feature):
        """Handle the featureIdentified signal"""
        # Get the layer from the current active layer or identify tool
        # layer = self.identify_tool.layer(self.layer.id())

        if not self.toolType:
            return

        if self.toolType == CenterEditToolType.PropertyEdit:
            self.openAttributeDialog(feature)
        elif self.toolType == CenterEditToolType.DeleteFeature:
            self.deleteFeature(feature)

    def openAttributeDialog(self, feature):
        """Open the attribute edit dialog for the feature"""
        if self.layer.isEditable() or self.layer.startEditing():
            dialog = QgsAttributeDialog(self.layer, feature, False, None, True)
            dialog.setMode(QgsAttributeEditorContext.SingleEditMode)

            if dialog.exec() == 1:
                # The dialog automatically handles the attribute updates
                # Refresh the layer to show changes
                self.layer.triggerRepaint()

    def deleteFeature(self, feature):
        """Delete the selected feature"""
        if self.layer.isEditable() or self.layer.startEditing():
            success = self.layer.deleteFeature(feature.id())
            if success:
                self.layer.triggerRepaint()

    def startMoveFeature(self):
        """Start moving the feature"""

        if self.layer.isEditable() or self.layer.startEditing():
            self.iface.actionVertexTool().trigger()

    def addFeature(self):
        if self.layer.isEditable() or self.layer.startEditing():
            self.iface.actionAddFeature().trigger()


class CenterEditToolType(Enum):
    AddFeature = 1
    PropertyEdit = 2
    MoveGeometry = 3
    DeleteFeature = 4
