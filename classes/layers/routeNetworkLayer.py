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
    QgsMessageLog,
    QgsVectorLayer,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsField,
    QgsFeature,
    QgsFeatureRequest
)

from ...constants import CRS_STR
from .layer import DigiRadLayer
from ..network import ConnectivityFunction
from ..processing.routeNetwork import RouteEntry
from ..styling import Style


class RouteNetworkFeatureConfig:
    def __init__(self, cfName: str = "Verbindungsfunktionsstufe",
                 relationName: str = "relation", airDistPathRel: str = "LuftlinienWegRelation"):
        self.cfName = cfName
        self.relationName = relationName
        self.airDistPathRel = airDistPathRel


class RouteNetworklayer(DigiRadLayer):
    LayerName = "Umgelegte Relationen"
    GroupName = "Umlegung"
    DemandGroupname = "Nachfrageumlegung"

    def __init__(self, routeEntries: List[RouteEntry], layerName: str = "Umgelegte Relationen", groupName: str = "Umlegung",
                 config: RouteNetworkFeatureConfig = RouteNetworkFeatureConfig()) -> 'RouteNetworklayer':
        super().__init__(
            RouteNetworklayer._createLayerFromRouteEntries(
                routeEntries, layerName, config),
            groupName,
            expanded=False,
            visible=False)

        self.routeEntries = routeEntries
        self.config = config

        renderer = self._createRenderer(groupName == self.DemandGroupname)
        self._qgsLayer.setRenderer(renderer)
        self._qgsLayer.triggerRepaint()

    def _createLayerFromRouteEntries(
            routeEntries: List[RouteEntry], layerName: str, config: RouteNetworkFeatureConfig) -> QgsVectorLayer:
        routeLayer = QgsVectorLayer("LineString?crs={}".format(CRS_STR),
                                    layerName, "memory")
        pr = routeLayer.dataProvider()
        pr.addAttributes([
            QgsField(config.relationName, QMetaType.Type.LongLong),
            QgsField(config.cfName, QMetaType.Type.QString),
            QgsField(config.airDistPathRel, QMetaType.Type.Double),
        ])
        routeLayer.updateFields()

        feats = []
        for route in routeEntries:
            if route.notFound():
                QgsMessageLog.logMessage(
                    f"Route not found {route.directRouteEntry.relationId}")
                continue
            feat = QgsFeature()
            feat.setAttributes([route.directRouteEntry.relationId, route.directRouteEntry.cf.asStr(
            ), route.validation.airDistPathRel])
            feat.setGeometry(route.geometry())
            feats.append(feat)

        pr.addFeatures(feats)

        routeLayer.updateExtents()

        return routeLayer

    def _createRenderer(
            self, isDemand: bool = False) -> QgsCategorizedSymbolRenderer:
        renderer = QgsCategorizedSymbolRenderer(self.config.cfName)

        for cf in [ConnectivityFunction.VFS_2,
                   ConnectivityFunction.VFS_3, ConnectivityFunction.VFS_4]:
            symbol = Style.getStyleForRouteLine(cf, isDemand)
            cat = QgsRendererCategory(cf.asStr(), symbol, cf.asStr())

            renderer.addCategory(cat)

        orderBy = QgsFeatureRequest.OrderBy(
            [QgsFeatureRequest.OrderByClause(self.config.cfName, False)])
        renderer.setOrderByEnabled(True)
        renderer.setOrderBy(orderBy)

        return renderer
