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

from typing import Type, Optional, Tuple, List

import os

from qgis.PyQt.QtCore import QTimer

from qgis.core import (
    QgsMessageLog,
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsPointXY,
    QgsVectorFileWriter
)

from ..constants import CRS_STR
from ..dialogstate import DialogStateContext, LocationSelectHandler
from .layers.layer import DigiRadLayer
from .layers.baseLayer import BaseLayer
from .processingConfig import ProcessingConfig


class LayerManager:
    def __init__(self, processingConfig: ProcessingConfig,
                 showBaseMap: bool = True):
        self._crs = QgsCoordinateReferenceSystem(CRS_STR)
        QgsProject.instance().setCrs(self._crs)

        self.iface = None
        self.processingConfig = processingConfig
        self.projectName = processingConfig.projectName
        self.showBaseMap = showBaseMap

        self.layers = {}
        self.contextRef = None
        self.center = None

    def setContextRef(self, contextRef: DialogStateContext):
        self.contextRef = contextRef

    def unlink(self):
        self.layers = {}
        self.processingConfig = ProcessingConfig()
        self.projectName = self.processingConfig.projectName

    def removeAll(self):
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup(self.projectName)
        # NOTE: never use truthiness on QgsLayerTree* nodes. In the Qt6/PyQt6
        # bindings they implement __len__ (child count), so an empty group or a
        # leaf layer node evaluates as falsy even though it is not None.
        if group is None:
            return
        root.removeChildNode(group)
        self.layers = {}
        self.baseLayer = None

    def show(self, center: Optional[QgsPointXY] = None):
        # If no layer is on the map, QGIS updates the CRS and extent
        # based on the first added layer.
        # As we already set the crs and extent in the location view
        # these settings are overwritten when the base map is added.
        # So we have to reset the crs and extent
        self.center = center
        project = QgsProject.instance()
        canvas = self.iface.mapCanvas()

        canvas.freeze(True)
        project.setCrs(self._crs)
        canvas.setDestinationCrs(self._crs)

        if self.showBaseMap:
            if self.contextRef:
                providerName = self.contextRef.get(
                    LocationSelectHandler.KBaseLayer)
            else:
                providerName = ""

            # Remove a previously added base map so we don't end up with
            # multiple base map layers stacking up
            if getattr(self, "baseLayer", None):
                self._removeLayer(self.baseLayer)

            self.baseLayer = BaseLayer.createFromProviderName(providerName)

        self._ensureLayer(self.baseLayer)
        canvas.freeze(False)

        # See
        # https://gis.stackexchange.com/questions/303704/project-crs-not-being-respected-by-qgis/303710#303710
        QTimer.singleShot(20, self._setProjectCrsAndCenter)

        self.update()

    def _setProjectCrsAndCenter(self):
        QgsProject.instance().setCrs(self._crs)
        canvas = self.iface.mapCanvas()
        canvas.freeze(True)
        canvas.setDestinationCrs(self._crs)
        canvas.zoomScale(150000)
        if self.center:
            canvas.setCenter(self.center)

        canvas.freeze(False)
        canvas.refresh()

    def saveProjectToDisk(self, directory: str) -> Tuple[bool, str]:
        # Get all layers
        layers = []
        for value in self.contextRef.values():
            if isinstance(value, DigiRadLayer):
                layers.append(value)

        if not layers:
            return (True, "No layers")
        try:
            projectFilePath = os.path.join(
                directory, self.projectName + ".qgz")
            gpkgFilePath = os.path.join(directory, self.projectName + ".gpkg")

            # Prepare directory
            os.makedirs(directory, exist_ok=True)
            if os.path.exists(projectFilePath):
                os.remove(projectFilePath)
            if os.path.exists(gpkgFilePath):
                os.remove(gpkgFilePath)

            # Save layers to geopackage file
            for layer in layers:
                layerName = layer.name()
                if not layerName:
                    continue
                layerName = LayerManager._sanitizeLayername(layerName)

                options = QgsVectorFileWriter.SaveVectorOptions()
                options.driverName = "GPKG"
                options.layerName = layerName

                # Check if this is the first layer (create new file) or append
                # to existing
                if os.path.exists(gpkgFilePath):
                    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
                else:
                    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile

                error = QgsVectorFileWriter.writeAsVectorFormatV3(
                    layer.qgsLayer(),
                    gpkgFilePath,
                    layer.qgsLayer().transformContext(),
                    options
                )
                if error[0] == QgsVectorFileWriter.NoError:
                    pass
                else:
                    msg = f"Error writing layer {layer.name()}: {error[1]}"
                    QgsMessageLog.logMessage(msg)
                    return (False, msg)

                # Replace source in existing layer
                newSource = f"{gpkgFilePath}|layername={layerName}"
                layer.qgsLayer().setDataSource(newSource, layer.name(), "ogr")
                if layer.qgsLayer().isValid():
                    layer.qgsLayer().triggerRepaint()
                    layer.qgsLayer().reload()
                else:
                    msg = "Error while setting data source for layer {}: {}".format(
                        layer.name(),
                        layer.qgsLayer().error()
                    )
                    QgsMessageLog.logMessage(msg)
                    return (False, msg)

            # Save project
            success = QgsProject.instance().write(projectFilePath)
            if not success:
                msg = f"Error while saving project instance to {projectFilePath}"
                QgsMessageLog.logMessage(msg)
                return (False, msg)
            else:
                return (True, "")
        except Exception as e:
            return (False, f"Error while saving to disk: {e}")

    @staticmethod
    def _sanitizeLayername(layerName: str) -> str:
        layerName = layerName.replace(' ', '_').replace('-', '_')
        return ''.join(c for c in layerName if c.isalnum() or c == '_')

    def update(self, layerHideList: List[str]
               = [], groupHidelist: List[str] = []):
        if not self.contextRef:
            return

        updatedLayers = set()
        for value in self.contextRef.values():
            if isinstance(value, DigiRadLayer):
                self.updateLayer(value)
                updatedLayers.add(value.name())

        layersToRemove = []
        for (layerId, layer) in self.layers.items():
            if layer.name() not in updatedLayers:
                self._removeLayer(layer)
                layersToRemove.append(layerId)

        for layerId in layersToRemove:
            del self.layers[layerId]

        if self.layers and (layerHideList or groupHidelist):
            root = QgsProject.instance().layerTreeRoot()
            group = root.findGroup(self.projectName)
            for value in self.contextRef.values():
                if not isinstance(value, DigiRadLayer):
                    continue
                if value.groupName:
                    subgroup = group.findGroup(value.groupName)
                    if subgroup is not None:
                        if value.groupName in groupHidelist:
                            subgroup.setItemVisibilityChecked(False)
                            subgroup.setExpanded(False)
                        else:
                            subgroup.setItemVisibilityChecked(True)
                            subgroup.setExpanded(True)

                layerName = value.name()
                layerNode = root.findLayer(value.id())
                if layerNode is not None:
                    if layerName in layerHideList:
                        layerNode.setItemVisibilityCheckedRecursive(False)
                        layerNode.setExpanded(False)
                    else:
                        layerNode.setItemVisibilityCheckedRecursive(
                            value.visible)
                        layerNode.setExpanded(value.expanded)

    def _getGroup(self, layer: Optional[DigiRadLayer] = None):
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup(self.projectName)
        # NOTE: compare against None explicitly. QgsLayerTree* nodes implement
        # __len__ in the Qt6/PyQt6 bindings, so an empty group is falsy even
        # though it exists. Using `if not group` would re-create the group.
        if group is None:
            # Insert the project group directly at the top of the layer tree.
            group = root.insertGroup(0, self.projectName)

        if layer and layer.groupName:
            subgroup = group.findGroup(layer.groupName)
            if subgroup is None:
                # Insert new subgroups directly at the top of the project group.
                subgroup = group.insertGroup(0, layer.groupName)
            group = subgroup

        return (root, group)

    def _ensureLayer(self, layer: DigiRadLayer):
        if layer and layer.isQgsLayerPresent():
            qgsLayer = layer.qgsLayer()
            root = QgsProject.instance().layerTreeRoot()
            # A layer must appear at most once in the layer tree. If it is
            # already present anywhere in the tree, leave it untouched so that
            # switching between plugin views does not re-create / duplicate it.
            # Compare against None explicitly: a found leaf layer node has zero
            # children and therefore evaluates as falsy under the Qt6/PyQt6
            # bindings (QgsLayerTree* implements __len__). Using `if found:`
            # here was the cause of the duplicated layers.
            if root.findLayer(qgsLayer.id()) is not None:
                return

            (root, group) = self._getGroup(layer)
            # Register the layer without adding it to the layer tree
            # (addToLegend=False), then insert it directly into the target
            # group. This avoids cloning/re-parenting tree nodes, which is
            # unreliable and was causing duplicate groups to be created.
            QgsProject.instance().addMapLayer(qgsLayer, False)
            # The base map should always be rendered below all other
            # layers, so it is inserted at the bottom of the group
            # instead of the top.
            if isinstance(layer, BaseLayer):
                layerNode = group.insertLayer(len(group.children()), qgsLayer)
            else:
                layerNode = group.insertLayer(0, qgsLayer)
            if layerNode is None:
                QgsMessageLog.logMessage(
                    f"No layer node found for QGIS layer {qgsLayer.id()}")
                return
            layerNode.setItemVisibilityChecked(layer.visible)
            layerNode.setExpanded(layer.expanded)

    def _removeLayer(self, layer: DigiRadLayer):
        if layer and layer.isQgsLayerPresent():
            root = QgsProject.instance().layerTreeRoot()
            # Locate the node tree-wide by layer id and remove it from wherever
            # it is attached. This is reliable even if the layer is not in the
            # group _getGroup would currently resolve to.
            layerNode = root.findLayer(layer.id())
            if layerNode is not None and layerNode.parent() is not None:
                layerNode.parent().removeChildNode(layerNode)

    def updateLayer(self, layer: DigiRadLayer):
        layerName = layer.name()

        if layerName in self.layers:
            originalLayer = self.layers[layerName]
            if originalLayer.isQgsLayerPresent():
                if originalLayer.id() != layer.id():
                    self._removeLayer(originalLayer)
                    self.layers[layerName] = layer
            else:
                self.layers[layerName] = layer
        else:
            self.layers[layerName] = layer

        self._ensureLayer(layer)
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())

    def getLayer(self, layerType: Type) -> Optional[DigiRadLayer]:
        for layer in self.layers:
            if isinstance(layer, layerType):
                return layer

        return None

    def updateProjectName(self):
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup(self.projectName)
        if group is not None:
            group.setName(self.processingConfig.projectName)

        self.projectName = self.processingConfig.projectName

    def crs(self):
        return self._crs
