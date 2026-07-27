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
    QgsRendererCategory,
    QgsField,
    QgsSymbol,
    QgsMarkerSymbol,
    Qgis,
    QgsFeatureRequest
)

from ...constants import CRS_STR
from .layer import DigiRadLayer
from ..network import ConnectivityFunction
from ..processing.routeNetworkAnalyser import NetworkElement, AggregatedNetworkElement, BreakingElement
from ..styling import Style


class SupplyNetworkElementFeatureConfig:
    def __init__(self, edgeIdName: str = "KantenId", cfName: str = "Verbindungsfunktionsstufe",
                 occupancyName: str = "Belegung") -> 'SupplyNetworkElementFeatureConfig':
        self.edgeIdName = edgeIdName
        self.cfName = cfName
        self.occupancyName = occupancyName
        self.occupancyNameCF2 = "{} {}".format(
            occupancyName, ConnectivityFunction.VFS_2.asStrShort())
        self.occupancyNameCF3 = "{} {}".format(
            occupancyName, ConnectivityFunction.VFS_3.asStrShort())
        self.occupancyNameCF4 = "{} {}".format(
            occupancyName, ConnectivityFunction.VFS_4.asStrShort())


class SupplyNetworkElementLayer(DigiRadLayer):
    def __init__(self, networkElements: List[NetworkElement], layerName: str = "Angebotsnetz", groupName: str = "Umlegung",
                 config: SupplyNetworkElementFeatureConfig = SupplyNetworkElementFeatureConfig()) -> 'SupplyNetworkElementLayer':
        super().__init__(
            SupplyNetworkElementLayer._createLayerFromNetworkElements(
                networkElements, layerName, config),
            groupName,
            expanded=False,
            visible=False
        )

        self.networkElements = networkElements
        self.config = config

        renderer = self._createRenderer()
        self._qgsLayer.setRenderer(renderer)
        self._qgsLayer.triggerRepaint()

    @staticmethod
    def _createLayerFromNetworkElements(
            networkElements: List[NetworkElement], layerName: str, config: SupplyNetworkElementFeatureConfig) -> QgsVectorLayer:
        routeLayer = QgsVectorLayer("LineString?crs={}".format(CRS_STR),
                                    layerName, "memory")
        pr = routeLayer.dataProvider()
        pr.addAttributes([
            QgsField(config.edgeIdName, QMetaType.Type.LongLong),
            QgsField(config.cfName, QMetaType.Type.QString),
            QgsField(config.occupancyName, QMetaType.Type.Int),
            QgsField(config.occupancyNameCF2, QMetaType.Type.Int),
            QgsField(config.occupancyNameCF3, QMetaType.Type.Int),
            QgsField(config.occupancyNameCF4, QMetaType.Type.Int),
        ])
        routeLayer.updateFields()
        features = []
        for element in networkElements:
            features.append(element.toQgsFeature())
        pr.addFeatures(features)

        routeLayer.updateExtents()

        return routeLayer

    def _createRenderer(self) -> QgsCategorizedSymbolRenderer:
        renderer = QgsCategorizedSymbolRenderer(self.config.cfName)

        for cf in [ConnectivityFunction.VFS_2,
                   ConnectivityFunction.VFS_3, ConnectivityFunction.VFS_4]:
            symbol = QgsSymbol.defaultSymbol(Qgis.GeometryType.Line)
            symbol.setColor(Style.getColorForCF(cf))
            symbol.setWidth(Style.getSizeForCF(cf))
            cat = QgsRendererCategory(cf.asStrShort(), symbol, cf.asStr())

            renderer.addCategory(cat)

        orderBy = QgsFeatureRequest.OrderBy(
            [QgsFeatureRequest.OrderByClause(self.config.cfName, False)])
        renderer.setOrderByEnabled(True)
        renderer.setOrderBy(orderBy)

        return renderer


class SupplyAggregatedNetworkElementLayer(DigiRadLayer):
    LayerName = "Angebotsnetz (aggregiert)"

    def __init__(self, networkElements: List[AggregatedNetworkElement], layerName: str = "Angebotsnetz (aggregiert)", groupName: str = "Umlegung",
                 config: SupplyNetworkElementFeatureConfig = SupplyNetworkElementFeatureConfig()) -> 'SupplyAggregatedNetworkElementLayer':
        super().__init__(SupplyAggregatedNetworkElementLayer._createLayerFromNetworkElements(
            networkElements, layerName, config), groupName)

        self.networkElements = networkElements
        self.config = config

        renderer = self._createRenderer(groupName != "Umlegung")
        self._qgsLayer.setRenderer(renderer)
        self._qgsLayer.triggerRepaint()

    @staticmethod
    def _createLayerFromNetworkElements(
            networkElements: List[AggregatedNetworkElement], layerName: str, config: SupplyNetworkElementFeatureConfig) -> QgsVectorLayer:
        routeLayer = QgsVectorLayer("LineString?crs={}".format(CRS_STR),
                                    layerName, "memory")
        pr = routeLayer.dataProvider()
        pr.addAttributes([
            QgsField(config.cfName, QMetaType.Type.QString),
            QgsField(config.occupancyName, QMetaType.Type.Int),
            QgsField(config.occupancyNameCF2, QMetaType.Type.Int),
            QgsField(config.occupancyNameCF3, QMetaType.Type.Int),
            QgsField(config.occupancyNameCF4, QMetaType.Type.Int),
        ])
        routeLayer.updateFields()
        features = []
        for element in networkElements:
            features.append(element.toQgsFeature())
        pr.addFeatures(features)

        routeLayer.updateExtents()

        return routeLayer

    def _createRenderer(
            self, isDemand: bool = False) -> QgsCategorizedSymbolRenderer:
        renderer = QgsCategorizedSymbolRenderer(self.config.cfName)

        for cf in [ConnectivityFunction.VFS_2,
                   ConnectivityFunction.VFS_3, ConnectivityFunction.VFS_4]:
            symbol = Style.getStyleForRouteLine(cf, isDemand)
            cat = QgsRendererCategory(cf.asStrShort(), symbol, cf.asStr())
            renderer.addCategory(cat)

        orderBy = QgsFeatureRequest.OrderBy(
            [QgsFeatureRequest.OrderByClause(self.config.cfName, False)])
        renderer.setOrderByEnabled(True)
        renderer.setOrderBy(orderBy)

        return renderer


class BreakingPointsNetworkFeatureeConfig:
    def __init__(self, cfName: str = "Verbindungsfunktionsstufe",
                 occupancyName: str = "Belegung") -> 'BreakingPointsNetworkFeatureeConfig':
        self.cfName = cfName
        self.occupancyName = occupancyName
        self.occupancyNameCF2 = "{} {}".format(
            occupancyName, ConnectivityFunction.VFS_2.asStrShort())
        self.occupancyNameCF3 = "{} {}".format(
            occupancyName, ConnectivityFunction.VFS_3.asStrShort())
        self.occupancyNameCF4 = "{} {}".format(
            occupancyName, ConnectivityFunction.VFS_4.asStrShort())


class BreakingPointsNetworkLayer(DigiRadLayer):
    def __init__(self, breakingElements: List[BreakingElement], layerName: str = "Netzaufteilung", groupName: str = "Umlegung",
                 config: BreakingPointsNetworkFeatureeConfig = BreakingPointsNetworkFeatureeConfig()) -> 'BreakingPointsNetworkLayer':
        super().__init__(
            BreakingPointsNetworkLayer._createLayer(
                breakingElements, layerName, config),
            groupName,
            expanded=False)

        self.breakingElements = breakingElements
        self.config = config

        renderer = self._createRenderer()
        self._qgsLayer.setRenderer(renderer)
        self._qgsLayer.triggerRepaint()

    @staticmethod
    def _createLayer(breakingElements: List[BreakingElement], layerName: str,
                     config: BreakingPointsNetworkFeatureeConfig) -> QgsVectorLayer:
        layer = QgsVectorLayer("Point?crs={}".format(CRS_STR),
                               layerName, "memory")
        pr = layer.dataProvider()
        pr.addAttributes([
            QgsField(config.cfName, QMetaType.Type.QString),
            QgsField(config.occupancyName, QMetaType.Type.Int),
            QgsField(config.occupancyNameCF2, QMetaType.Type.Int),
            QgsField(config.occupancyNameCF3, QMetaType.Type.Int),
            QgsField(config.occupancyNameCF4, QMetaType.Type.Int),
        ])
        layer.updateFields()
        features = []
        for breakingElement in breakingElements:
            features.append(breakingElement.toQgsFeature())
        pr.addFeatures(features)

        layer.updateExtents()

        return layer

    def _createRenderer(self) -> QgsCategorizedSymbolRenderer:
        renderer = QgsCategorizedSymbolRenderer(self.config.cfName)

        for cf in [ConnectivityFunction.VFS_2,
                   ConnectivityFunction.VFS_3, ConnectivityFunction.VFS_4]:
            symbol = QgsMarkerSymbol.createSimple({'name': 'triangle'})
            symbol.setColor(Style.getColorForCF(cf))
            symbol.setSize(3.6)
            cat = QgsRendererCategory(cf.asStrShort(), symbol, cf.asStr())

            renderer.addCategory(cat)

        orderBy = QgsFeatureRequest.OrderBy(
            [QgsFeatureRequest.OrderByClause(self.config.cfName, False)])
        renderer.setOrderByEnabled(True)
        renderer.setOrderBy(orderBy)

        return renderer
