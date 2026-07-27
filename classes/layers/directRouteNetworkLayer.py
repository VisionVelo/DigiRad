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

from typing import List

from qgis.PyQt.QtCore import QMetaType
from qgis.core import (
    QgsVectorLayer,
    QgsCategorizedSymbolRenderer,
    QgsSingleSymbolRenderer,
    QgsRendererCategory,
    QgsField,
    QgsFeature,
    QgsLineSymbol,
    QgsFeatureRequest
)

from ...constants import CRS_STR
from .layer import DigiRadLayer
from ..network import ConnectivityFunction
from ..processing.directRouteEntry import DirectRouteEntry
from ..styling import Style, Colors


class DirectRouteNetworkFeatureConfig:
    def __init__(self, cfName: str = "Verbindungsfunktionsstufe",
                 relationName: str = "relation"):
        self.cfName = cfName
        self.relationName = relationName


class DirectRouteNetworklayer(DigiRadLayer):
    LayerName = "Luftliniennetz"

    def __init__(self, routeEntries: List[DirectRouteEntry], layerName: str, groupName: str = "",
                 config: DirectRouteNetworkFeatureConfig = DirectRouteNetworkFeatureConfig()) -> 'DirectRouteNetworklayer':
        super().__init__(DirectRouteNetworklayer.createLayerFromRouteEntries(
            routeEntries, config, layerName), groupName)

        self.routeEntries = routeEntries
        self.config = config

        renderer = self._createRenderer(config.cfName)
        self._qgsLayer.setRenderer(renderer)
        self._qgsLayer.triggerRepaint()

    @staticmethod
    def createLayerFromRouteEntries(
            routeEntries: DirectRouteEntry, config: DirectRouteNetworkFeatureConfig, layerName: str) -> 'DirectRouteNetworklayer':
        meshlayer = QgsVectorLayer(
            "LineString?crs={}".format(CRS_STR), layerName, "memory")
        pr = meshlayer.dataProvider()
        pr.addAttributes([QgsField(config.relationName, QMetaType.Type.LongLong),
                          QgsField(config.cfName, QMetaType.Type.QString)])
        meshlayer.updateFields()

        feats = []
        for route in routeEntries:
            feat = QgsFeature()
            feat.setAttributes([route.relationId, route.cf.asStr()])
            feat.setGeometry(route.geometry())
            feats.append(feat)

        pr.addFeatures(feats)
        meshlayer.updateExtents()

        return meshlayer

    def _createRenderer(
            self, categoryField: str) -> QgsCategorizedSymbolRenderer:
        renderer = QgsCategorizedSymbolRenderer(categoryField)

        for cf in [ConnectivityFunction.VFS_2,
                   ConnectivityFunction.VFS_3, ConnectivityFunction.VFS_4]:
            symbol = QgsLineSymbol.createSimple({'line_style': 'dash'})
            symbol.setColor(Style.getColorForCF(cf))
            symbol.setWidth(Style.getSizeForCF(cf))
            cat = QgsRendererCategory(cf.asStr(), symbol, cf.asStr())

            renderer.addCategory(cat)

        orderBy = QgsFeatureRequest.OrderBy(
            [QgsFeatureRequest.OrderByClause(self.config.cfName, False)])
        renderer.setOrderByEnabled(True)
        renderer.setOrderBy(orderBy)

        return renderer


class MissingRoutesLayer(DigiRadLayer):
    LayerNameReproject = "Nicht gefundene Umlegungen"
    LayerNameReprojectDemand = "Nicht gefundene Nachfrageumlegungen"

    def __init__(self, routeEntries: List[DirectRouteEntry], layerName: str, groupName: str,
                 config: DirectRouteNetworkFeatureConfig = DirectRouteNetworkFeatureConfig()) -> 'MissingRoutesLayer':
        super().__init__(DirectRouteNetworklayer.createLayerFromRouteEntries(
            routeEntries, config, layerName), groupName)

        self.routeEntries = routeEntries
        self.config = config

        renderer = self._createRenderer()
        self._qgsLayer.setRenderer(renderer)
        self._qgsLayer.triggerRepaint()

    def _createRenderer(self) -> QgsCategorizedSymbolRenderer:
        symbol = QgsLineSymbol.createSimple({'line_style': 'dash'})
        symbol.setColor(Colors.Error)
        symbol.setWidth(0.4)
        renderer = QgsSingleSymbolRenderer(symbol)

        return renderer
