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

from typing import List, Optional
from qgis.core import (
    QgsMessageLog,
    QgsVectorLayer,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsFeatureRequest,
    QgsFeature,
    QgsGeometry,
    QgsPoint,
    QgsPointXY,
    QgsRectangle,
    QgsSymbol,
    QgsMarkerSymbol,
    Qgis,
    QgsEditFormConfig,
    QgsAttributeEditorField,
    QgsEditorWidgetSetup
)

from ...constants import CRS_STR, SURROUNDING_QUERY_DISTANCE
from ...constants import SURROUNDING_LAYER
from ..ars import ARSCodeStr
from .layer import DigiRadLayer
from ..network import LevelOfCentrality
from ..styling import Style
from .centerLayerFeatures import CenterLayerFeature, CenterLayerFeatureConfig
from ..processing.meshCalculator import MeshCalculator


class CenterLayer(DigiRadLayer):
    LayerName = "Zentren"

    def __init__(self, layer, arsCodeStr: ARSCodeStr,
                 config: CenterLayerFeatureConfig = CenterLayerFeatureConfig()):
        super().__init__(layer)
        self.arsCodeStr = arsCodeStr
        self.config = config
        renderer = self._createRenderer()
        formConfig = self._createFormConfig()
        layer.setEditFormConfig(formConfig)
        layer.setRenderer(renderer)
        layer.triggerRepaint()

        self.locFeatures = CenterLayerFeature.featuresFromLayer(layer, config)

    @staticmethod
    def createEmpty(arsCodeStr: ARSCodeStr = ARSCodeStr.empty(
    ), config: CenterLayerFeatureConfig = CenterLayerFeatureConfig()) -> 'CenterLayer':
        layer = QgsVectorLayer("Point?crs={}&field={}:string&field={}:string".format(
            config.nameName, config.locName, CRS_STR), CenterLayer.LayerName, "memory")
        return CenterLayer(layer, arsCodeStr)

    @staticmethod
    def loadFromFile(filePath: str, arsCodeStr: ARSCodeStr = ARSCodeStr.empty(
    ), filterLOCs: Optional[List[LevelOfCentrality]] = LevelOfCentrality.defaults(), config: CenterLayerFeatureConfig = CenterLayerFeatureConfig()):
        layer = QgsVectorLayer(filePath, CenterLayer.LayerName, "ogr")

        return CenterLayer.loadFromLayer(layer, arsCodeStr, filterLOCs, config)

    @staticmethod
    def loadFromLayer(layer: QgsVectorLayer, arsCodeStr: ARSCodeStr = ARSCodeStr.empty(
    ), filterLOCs: Optional[List[LevelOfCentrality]] = LevelOfCentrality.defaults(), config: CenterLayerFeatureConfig = CenterLayerFeatureConfig()):
        filter = CenterLayer._createFeatureFilter(
            config, arsCodeStr, filterLOCs)
        request = QgsFeatureRequest().setFilterExpression(filter)

        layer = layer.materialize(request)
        # If there is no ARSCodeStr, we cannot get plausible surroundings
        if not arsCodeStr.isEmpty():
            layer = CenterLayer._mergeWithSurroundings(
                arsCodeStr, layer, config)
        return CenterLayer(layer, arsCodeStr, config)

    @staticmethod
    def _mergeWithSurroundings(arsCodeStr: ARSCodeStr, layer: QgsVectorLayer,
                               config: CenterLayerFeatureConfig) -> QgsVectorLayer:
        surroundingFeats = SurroundingHelper.getSurroundingFeatures(
            arsCodeStr, layer, config)

        # Get next free feature id of the loc layer
        fidIdx = layer.fields().indexFromName("fid")
        maxFeatId = 0
        for feat in layer.getFeatures():
            fid = feat[fidIdx]
            if fid > maxFeatId:
                maxFeatId = fid

        maxFeatId += 1

        pr = layer.dataProvider()
        feats = []
        for centerFeat in surroundingFeats:
            feat = QgsFeature()
            feat.setAttributes(
                [maxFeatId, centerFeat.ars.code, centerFeat.name, centerFeat.loc.asStrShort()])
            feat.setGeometry(QgsGeometry.fromPointXY(
                QgsPointXY(centerFeat.geom.x(), centerFeat.geom.y())))
            feats.append(feat)
            maxFeatId += 1

        pr.addFeatures(feats)
        layer.updateExtents()

        return layer

    def update(self):
        self.locFeatures = CenterLayerFeature.featuresFromLayer(
            self.qgsLayer(), self.config)

    def _createRenderer(self) -> QgsCategorizedSymbolRenderer:
        renderer = QgsCategorizedSymbolRenderer(self.config.locName)

        for loc in LevelOfCentrality:
            if loc == LevelOfCentrality.Surrounding:
                symbol = QgsMarkerSymbol.createSimple({'name': 'diamond'})
            else:
                symbol = QgsSymbol.defaultSymbol(Qgis.GeometryType.Point)

            symbol.setColor(Style.getColorForLOC(loc))
            symbol.setSize(Style.getSizeForLOC(loc))
            cat = QgsRendererCategory(loc.asStrShort(), symbol, loc.asStr())

            renderer.addCategory(cat)

        return renderer

    def _createFormConfig(self):
        formConfig = QgsEditFormConfig()
        formConfig.setLayout(QgsEditFormConfig.TabLayout)
        root = formConfig.invisibleRootContainer()
        layer = self.qgsLayer()
        fields = layer.fields()

        locIdx = fields.indexFromName(self.config.locName)
        if locIdx >= 0:
            locElement = QgsAttributeEditorField(
                self.config.locName, locIdx, None)
            root.addChildElement(locElement)

            valueMap = {}
            for loc in LevelOfCentrality:
                valueMap[loc.asStr()] = loc.asStrShort()

            widgetSetup = QgsEditorWidgetSetup('ValueMap', {
                'map': valueMap,
                'AllowMulti': False,
                'AllowNull': False
            })
            layer.setEditorWidgetSetup(locIdx, widgetSetup)

        nameIdx = fields.indexFromName(self.config.nameName)
        if nameIdx >= 0:
            nameElement = QgsAttributeEditorField(
                self.config.nameName, nameIdx, None)
            root.addChildElement(nameElement)

            widgetSetup = QgsEditorWidgetSetup(
                'TextEdit', {'IsMultiline': False, 'Readonly': True})
            layer.setEditorWidgetSetup(nameIdx, widgetSetup)

        return formConfig

    @staticmethod
    def _createFeatureFilter(config: CenterLayerFeatureConfig,
                             arsCodeStr: ARSCodeStr, filterLocs: List[LevelOfCentrality]) -> str:
        locFilter = "{} in ({})".format(config.locName, ", ".join(
            map(lambda loc: "'{}'".format(loc.asStrShort()), filterLocs)))
        if arsCodeStr.isEmpty():
            return locFilter

        relevantCodePart = arsCodeStr.getRelevantPart()
        arsFilter = "substr(\"{}\", 1, {}) = '{}'".format(
            config.arsName, len(relevantCodePart), relevantCodePart)

        return f"{arsFilter} AND {locFilter}"


class SurroundingHelper:

    @staticmethod
    def getSurroundingFeatures(arsCodeStr: ARSCodeStr, centerLayer: QgsVectorLayer,
                               config: CenterLayerFeatureConfig) -> List[CenterLayerFeature]:
        featureBounds = centerLayer.extent()
        queryBounds = QgsRectangle(
            featureBounds.xMinimum() - SURROUNDING_QUERY_DISTANCE,
            featureBounds.yMinimum() - SURROUNDING_QUERY_DISTANCE,
            featureBounds.xMaximum() + SURROUNDING_QUERY_DISTANCE,
            featureBounds.yMaximum() + SURROUNDING_QUERY_DISTANCE
        )
        request = QgsFeatureRequest().setFilterRect(
            queryBounds).setFlags(QgsFeatureRequest.ExactIntersect)
        locFeatures = CenterLayerFeature.featuresFromLayer(centerLayer, config)

        surroundingFeats = []
        arsIdx = SURROUNDING_LAYER.fields().indexFromName("ARS_2")
        nameIdx = SURROUNDING_LAYER.fields().indexFromName("GEN")
        for feat in SURROUNDING_LAYER.getFeatures(request):
            arsStr = str(feat[arsIdx])
            # Skip ars of self
            if arsCodeStr.code == arsStr:
                continue
            ars = ARSCodeStr.fromStr(arsStr)
            if not ars:
                QgsMessageLog.logMessage(
                    f"Unable to create ars code from {arsStr} (surrounding)")
                ars = ARSCodeStr.empty()

            name = feat[nameIdx]
            geom = feat.geometry().asPoint()
            geom = QgsPoint(geom.x(), geom.y())

            surroundingFeats.append(
                CenterLayerFeature(feat.id(), name, ars, LevelOfCentrality.Surrounding, geom))

        allFeats = surroundingFeats
        for locFeats in locFeatures.values():
            allFeats += locFeats

        meshCalc = MeshCalculator()
        directRoutes = meshCalc.extractDirectRoutes(allFeats)
        nearbySurroundingFeats = []
        nearbyAddedIds = set()
        for route in directRoutes.values():
            if route.feat1.loc == LevelOfCentrality.Surrounding:
                if route.feat2.loc != LevelOfCentrality.Surrounding and route.feat1.featureId not in nearbyAddedIds:
                    nearbySurroundingFeats.append(route.feat1)
                    nearbyAddedIds.add(route.feat1.featureId)
            elif route.feat2.loc == LevelOfCentrality.Surrounding:
                if route.feat1.loc != LevelOfCentrality.Surrounding and route.feat2.featureId not in nearbyAddedIds:
                    nearbySurroundingFeats.append(route.feat2)
                    nearbyAddedIds.add(route.feat2.featureId)

        return nearbySurroundingFeats
