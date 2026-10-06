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

import os
import re

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import pyqtSignal, QUrl
from qgis.core import QgsMapLayerProxyModel, QgsFieldProxyModel, QgsMessageLog, QgsVectorLayer

from .qtHelpers import QtHelper
from .dialogstate import DialogStateMachine, DialogState
from .classes.interaction.keyFilter import KeyPressFilter
from .classes.layers.centerLayer import CenterLayer
from .classes.layers.baseLayer import BaseLayerProvider
from .classes.network import LevelOfCentrality, NetworkSource
from .classes.layers.directRouteNetworkLayer import DirectRouteNetworklayer, MissingRoutesLayer
from .classes.processing.directRouteNetwork import DirectRouteNetwork, DirectRouteGenerateMethod
from .classes.layers.routeNetworkLayer import RouteNetworklayer
from .classes.layers.analysisLayers import SupplyAggregatedNetworkElementLayer
from .classes.processing.routeNetworkTaskHelpers import RouteNetworkTaskResult, RouteNetworkTaskProgress
from .classes.interaction.centerEdit import CenterEditFeatureHandler, CenterEditToolType
from .constants import AUTO_CENTER_POINTS_PATH
from .statics import ARS_INDEX
from .classes.layerManager import LayerManager
from .classes.processing.task import RouteNetworkTask

# This loads your .ui file so that PyQt can populate your plugin with the
# elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'visionvelo_digirad_dockwidget.ui'))


class DigiRadDialog(QtWidgets.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    # region UI-SETUP

    def __init__(self, iface, layerManager: LayerManager, parent=None):
        """Constructor."""
        super(DigiRadDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.iface = iface

        self.setupUi(self)
        self.postSetupUi()

        self.stateMachine = DialogStateMachine(DialogState.WELCOME, self)
        self.keyFilter = KeyPressFilter(self.stateMachine)

        self.layerManager = layerManager

        self.layerManager.setContextRef(self.stateMachine.context)

        self.setupConnections()

        self.stateMachine.transitionTo(DialogState.WELCOME)

    def show(self):
        super().show()
        self.layerManager.removeAll()
        self.stateMachine.transitionTo(DialogState.WELCOME)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def _resolveRichTextImages(self):
        """Point rich text images at real files.

        Qt6 dropped compiled resources, so the ``:/<prefix>/res/<file>``
        URLs baked into the .ui file are rewritten to the plugin's own
        ``res`` directory at runtime.
        """
        resDir = QUrl.fromLocalFile(
            os.path.join(os.path.dirname(__file__), 'res') + os.sep).toString()

        for label in self.findChildren(QtWidgets.QLabel):
            text = label.text()
            if ':/' not in text:
                continue
            label.setText(re.sub(r'"(:/[^/"]+/res/)', f'"{resDir}', text))

    def postSetupUi(self):
        self._resolveRichTextImages()
        self.loadProjectButton.hide()
        self.centerMapLayerComboBox.setFilters(
            QgsMapLayerProxyModel.Filter.PointLayer)
        self.reprojectSelectLayer.setFilters(
            QgsMapLayerProxyModel.Filter.LineLayer)
        self.reprojectDemandSelectLayer.setFilters(
            QgsMapLayerProxyModel.Filter.LineLayer)
        self.reprojectDemandSelectField.setFilters(
            QgsFieldProxyModel.Filter.Numeric)

        self.locationBaseMapComboBox.addItems(
            BaseLayerProvider.getLayerNames())
        self.locationBaseMapComboBox.setCurrentIndex(0)

        self.tabs = {
            DialogState.WELCOME: self.welcomeTab,
            DialogState.LOCATIONSELECT: self.locationTab,
            DialogState.CENTERPOINTS: self.centerTab,
            DialogState.CENTERPOINTSEDIT: self.centerEditTab,
            DialogState.AIRLINE: self.airlineTab,
            DialogState.REPROJECT: self.reprojectTab,
            DialogState.REPROJECTDEMAND: self.reprojectDemandTab,
        }

        self.centerEditTool = None

    def setupConnections(self):
        # Connect signals and slots

        self.iface.mainWindow().installEventFilter(self.keyFilter)
        self.keyFilter.centerEditEscape.connect(self.onCenterEditUnselectTools)

        # Welcome Page
        self.welcomeNextButton.clicked.connect(self.onWelcomeNextButton)

        # Location page
        self.locationBackButton.clicked.connect(self.onLocationBackButton)
        self.locationCreateProject.clicked.connect(
            self.onLocationCreateProject)
        self.locationLineEdit.textChanged.connect(
            self.onLocationLineEditTextChanged)
        self.locationResultsListWidget.currentItemChanged.connect(
            self.onLocationRegionItemChanged)
        self.locationSelectExpandInfoLabel.linkActivated.connect(
            self.onLocationSelectExpandInfoLabel)

        # Center page
        self.centralSaveProjectButton.clicked.connect(self.onSaveProjectButton)
        self.centralGenerateButton.clicked.connect(
            self.onCentralGenerateButton)
        self.centralNextButton.clicked.connect(self.onCentralNextButton)
        self.centralRestartButton.clicked.connect(self.onRestartButton)
        self.centerMapLayerComboBox.layerChanged.connect(
            self.onCenterMapLayerComboBox)
        self.centerLoadLayerButton.clicked.connect(
            self.onCenterLoadLayerButton)
        self.centerCreateInfoLabel.linkActivated.connect(
            self.onCenterCreateInfoLabel)

        self.centerAutoRadioButton.toggled.connect(
            self.onCenterAutoRadioButton)
        self.centerManualRadioButton.toggled.connect(
            self.onCenterManualRadioButton)
        self.centerLayerRadioButton.toggled.connect(
            self.onCenterLayerRadioButton)

        # Center edit page
        self.centerEditRestartButton.clicked.connect(self.onRestartButton)
        self.centerEditSaveProjectButton.clicked.connect(
            self.onSaveProjectButton)
        self.centerEditBackButton.clicked.connect(self.onCenterEditBackButton)
        self.centerEditContinueButton.clicked.connect(
            self.onCenterEditContinueButton)

        self.centerEditAddutton.clicked.connect(self.onCenterEditAddutton)
        self.centerEditPropertiesButton.clicked.connect(
            self.onCenterEditPropertiesButton)
        self.centerEditGeometryButton.clicked.connect(
            self.onCenterEditGeometryButton)
        self.centerEditDeleteButton.clicked.connect(
            self.onCenterEditDeleteButton)
        self.centerEditUndo.clicked.connect(self.onCenterEditUndo)
        self.centerEditRedo.clicked.connect(self.onCenterEditRedo)

        # Airline page
        self.airlineRestartButton.clicked.connect(self.onRestartButton)
        self.airlineSaveProjectButton.clicked.connect(self.onSaveProjectButton)
        self.airlineBackButton.clicked.connect(self.onAirlineBackButton)
        self.airlineContinueButton.clicked.connect(
            self.onAirlineContinueButton)
        self.airlineGenerateButton.clicked.connect(
            self.onAirlineGenerateButton)
        self.airlineExpandInfoLabel.linkActivated.connect(
            self.onAirlineExpandInfoLabel)

        # Reproject page
        self.reprojectRestartButton.clicked.connect(self.onRestartButton)
        self.reprojectSaveProjectButton.clicked.connect(
            self.onSaveProjectButton)
        self.reprojectBackButton.clicked.connect(self.onReprojectBackButton)
        self.reprojectContinueButton.clicked.connect(
            self.onReprojectContinueButton)
        self.reprojectGenerateButton.clicked.connect(
            self.onReprojectGenerateButton)
        self.reprojectCancelGenerateButton.clicked.connect(
            self.onReprojectCancelGenerateButton)
        self.reprojectCenterDistanceLabel.linkActivated.connect(
            self.onReprojectDemandCenterDistanceLabel)
        self.reprojectReduceNetworkBoundsLabel.linkActivated.connect(
            self.onReprojectReduceNetworkBoundsLabel)
        self.reprojectInfoLabel.linkActivated.connect(
            self.onReprojectInfoLabel)

        # Reproject demand page
        self.reprojectDemandRestartButton.clicked.connect(self.onRestartButton)
        self.reprojectDemandSaveProjectButton.clicked.connect(
            self.onSaveProjectButton)
        self.reprojectDemandBackButton.clicked.connect(
            self.onReprojectDemandBackButton)
        self.reprojectDemandGenerateButton.clicked.connect(
            self.onReprojectDemandGenerateButton)
        self.reprojectDemandCancelGenerateButton.clicked.connect(
            self.onReprojectDemandCancelGenerateButton)
        self.reprojectDemandSelectLayer.layerChanged.connect(
            self.onReprojectDemandSelectLayerChanged)
        self.reprojectDemandCenterDistanceLabel.linkActivated.connect(
            self.onReprojectDemandCenterDistanceLabel)
        self.reprojectDemandSelectVMLabel.linkActivated.connect(
            self.onReprojectDemandSelectVMLabel)
        self.reprojectDemandReduceNetworkBoundsLabel.linkActivated.connect(
            self.onReprojectReduceNetworkBoundsLabel)
        self.reprojectDemandInfoLabel.linkActivated.connect(
            self.onReprojectDemandInfoLabel)

    def setupMapView(self):
        # Setup map canvas
        canvas = self.iface.mapCanvas()
        canvas.freeze(True)
        canvas.setDestinationCrs(self.layerManager.crs())

        if self.layerManager.processingConfig.arsCode:
            self.layerManager.show(
                self.layerManager.processingConfig.arsCode.center)
        else:
            self.layerManager.show()

    def selectTab(self, state: DialogState):
        for (tabState, tab) in self.tabs.items():
            tab.setEnabled(tabState == state)

        if state in self.tabs:
            self.tabWidget.setCurrentWidget(self.tabs[state])

    # endregion

    # region STATE TRANSITIONS

    def showWelcomePage(self):
        self.selectTab(DialogState.WELCOME)
        self.welcomeNextButton.setFocus()

    def showLocationSelectPage(self):
        self.locationLineEdit.setText("")
        self.locationResultsListWidget.clear()
        self.locationSelectedRegionLabel.setText("")
        self.locationProjectNameEdit.setText("")
        self.locationCreateProject.setEnabled(False)
        self.locationSelectExpandInfoLabel.show()
        self.locationSelectInfoBox.hide()
        self.selectTab(DialogState.LOCATIONSELECT)
        self.locationLineEdit.setFocus()

    def showCenterPointsPage(self):
        if DialogState.CENTERPOINTS.value.getGenerateMethod() == DirectRouteGenerateMethod.AUTO:
            self.centralGenerateButton.show()
            self.centralLOCBox.show()
            self.centerMapLayerBox.hide()
        elif DialogState.CENTERPOINTS.value.getGenerateMethod() == DirectRouteGenerateMethod.MANUEL:
            self.centralGenerateButton.hide()
            self.centralLOCBox.hide()
            self.centerMapLayerBox.hide()
        elif DialogState.CENTERPOINTS.value.getGenerateMethod() == DirectRouteGenerateMethod.LAYER:
            self.centralGenerateButton.hide()
            self.centralLOCBox.hide()
            self.centerMapLayerBox.show()

        self.centerCreateInfoLabel.show()
        self.centerCreateInfoBox.hide()
        self.centralNextButton.setEnabled(self.centerManualRadioButton.isChecked(
        ) or DialogState.CENTERPOINTS.value.hasCenterLayer())
        self.selectTab(DialogState.CENTERPOINTS)
        self.centralGenerateButton.setFocus()

        self.layerManager.update(
            layerHideList=[DirectRouteNetworklayer.LayerName],
            groupHidelist=[RouteNetworklayer.GroupName, RouteNetworklayer.DemandGroupname])

    def showCenterPointsEditPage(self):
        centerLayer = DialogState.CENTERPOINTS.value.getCenterLayer()

        if not centerLayer:
            if DialogState.CENTERPOINTS.value.getGenerateMethod(
            ) == DirectRouteGenerateMethod.MANUEL:
                centerLayer = CenterLayer.createEmpty(
                    self.layerManager.processingConfig.arsCode.code)
                DialogState.CENTERPOINTS.value.setCenterLayer(centerLayer)
                self.layerManager.update()
            else:
                return

        centerLayer.qgsLayer().startEditing()
        self.iface.setActiveLayer(centerLayer.qgsLayer())

        self.centerEditTool = CenterEditFeatureHandler(
            self.iface, centerLayer.qgsLayer())

        self.selectTab(DialogState.CENTERPOINTSEDIT)
        self.centerEditContinueButton.setFocus()

        self.layerManager.update(
            layerHideList=[DirectRouteNetworklayer.LayerName],
            groupHidelist=[RouteNetworklayer.GroupName, RouteNetworklayer.DemandGroupname])

    def showAirlinePage(self):
        self.airlineContinueButton.setEnabled(
            DialogState.AIRLINE.value.hasDirectRouteLayer())
        self.selectTab(DialogState.AIRLINE)
        self.airlineGenerateButton.setFocus()
        self.airlineExpandInfoLabel.show()
        self.airlineInfoBox.hide()

        self.layerManager.update(
            layerHideList=[],
            groupHidelist=[RouteNetworklayer.GroupName, RouteNetworklayer.DemandGroupname])

    def showReprojectPage(self, fastUpdate: bool = False):
        if DialogState.REPROJECT.value.isProcessing():
            self.reprojectGenerateButton.hide()
            self.reprojectProgressBar.show()
            self.reprojectProgressLabel.show()
            self.reprojectCancelGenerateButton.show()
            self.reprojectRestartButton.setEnabled(False)
            self.reprojectSaveProjectButton.setEnabled(False)
            self.reprojectBackButton.setEnabled(False)
            self.reprojectContinueButton.setEnabled(False)
            progressInfo = DialogState.REPROJECT.value.getProgress()
            self.reprojectProgressBar.setValue(progressInfo.progress)
            self.reprojectProgressLabel.setText(progressInfo.message)
        else:
            self.reprojectGenerateButton.show()
            self.reprojectProgressBar.hide()
            self.reprojectProgressLabel.hide()
            self.reprojectCancelGenerateButton.hide()
            self.reprojectRestartButton.setEnabled(True)
            self.reprojectSaveProjectButton.setEnabled(True)
            self.reprojectBackButton.setEnabled(True)
            self.reprojectContinueButton.setEnabled(
                DialogState.REPROJECT.value.hasRouteLayer())
            self.reprojectProgressBar.setValue(0)
            self.reprojectProgressLabel.setText("")

        self.selectTab(DialogState.REPROJECT)

        if not fastUpdate:
            self.layerManager.update(
                layerHideList=[DirectRouteNetworklayer.LayerName],
                groupHidelist=[RouteNetworklayer.DemandGroupname])
        else:
            self.reprojectInfoLabel.show()
            self.reprojectInfoBox.hide()

    def showReprojectDemandPage(self, fastUpdate: bool = False):
        if DialogState.REPROJECTDEMAND.value.isProcessing():
            self.reprojectDemandGenerateButton.hide()
            self.reprojectDemandProgressBar.show()
            self.reprojectDemandProgressLabel.show()
            self.reprojectDemandRestartButton.setEnabled(False)
            self.reprojectDemandSaveProjectButton.setEnabled(False)
            self.reprojectDemandCancelGenerateButton.show()
            self.reprojectDemandBackButton.setEnabled(False)
            progressInfo = DialogState.REPROJECTDEMAND.value.getProgress()
            self.reprojectDemandProgressBar.setValue(progressInfo.progress)
            self.reprojectDemandProgressLabel.setText(progressInfo.message)
        else:
            self.reprojectDemandGenerateButton.show()
            self.reprojectDemandProgressBar.hide()
            self.reprojectDemandProgressLabel.hide()
            self.reprojectDemandCancelGenerateButton.hide()
            self.reprojectDemandRestartButton.setEnabled(True)
            self.reprojectDemandSaveProjectButton.setEnabled(
                DialogState.REPROJECTDEMAND.value.hasRouteLayer())
            self.reprojectDemandBackButton.setEnabled(True)
            self.reprojectDemandProgressBar.setValue(0)
            self.reprojectDemandProgressLabel.setText("")

            networkLayer = self.reprojectDemandSelectLayer.currentLayer()
            if networkLayer:
                self.reprojectDemandSelectField.setLayer(networkLayer)

        self.selectTab(DialogState.REPROJECTDEMAND)

        if not fastUpdate:
            self.layerManager.update(
                layerHideList=[DirectRouteNetworklayer.LayerName],
                groupHidelist=[RouteNetworklayer.GroupName])
        else:
            self.reprojectDemandInfoLabel.show()
            self.reprojectDemandInfoBox.hide()

    # endregion

    # region HELPERS

    def guardLayerRegeneration(self, state: DialogState) -> bool:
        if DialogState.getValuesAfterContext(state, "LayerKeys"):
            return not QtHelper.askForLayerDeletion()
        return False

    def guardLayerCrsMistmatch(self, layer: QgsVectorLayer) -> bool:
        layerCrs = layer.crs().authid()
        projectCrs = self.layerManager.crs().authid()
        if layerCrs != projectCrs:
            QtHelper.showInformationBox(
                self,
                "Referenzsystem",
                f"Das angegebene Referenzsystem ({layerCrs}) stimmt nicht mit dem Projektreferenzsystem ({projectCrs}) überein.\n\nBitte Transformieren Sie die Daten zuerst in das geforderte Referenzsystem. (Menüpunkt Vektor > Datenmanangement-Werkzeuge > Layer reprojizieren, Ziel-KBS: {projectCrs})")
            return True
        return False

    def getNetworkSource(self, networkLayer: QgsVectorLayer) -> NetworkSource:
        result = NetworkSource.UNKNOWN
        filterAttributeMode = NetworkSource.fromAttributeList(
            networkLayer.fields().names())
        if filterAttributeMode != NetworkSource.UNKNOWN:
            asnwer = QtHelper.showAskBox(
                self, "Datenquelle erkannt", f"Es wurde die Datenquelle {filterAttributeMode.asStr()} erkannt.\n\nSollen nicht nutzbare Straßensegmente (z.B. Autobahnen, Zugstrecken) bei der Analyse entfernt werden?\n\nFalls ja, wird dieser Filter angewendet:\n{filterAttributeMode.getFilterStr()}")
            if asnwer == QtHelper.Yes:
                result = filterAttributeMode

        return result

    def onRestartButton(self):
        reply = QtHelper.askForProjectRestart()
        if reply == QtHelper.Yes:
            self.layerManager.removeAll()
            self.centerAutoRadioButton.setChecked(True)
            self.stateMachine.transitionTo(DialogState.LOCATIONSELECT)
        elif reply == QtHelper.KeepOldProject:
            self.layerManager.unlink()
            self.centerAutoRadioButton.setChecked(True)
            self.stateMachine.transitionTo(DialogState.LOCATIONSELECT)

    def onSaveProjectButton(self):
        directory = QtHelper.askForProjectToSaveDirectory(self)
        if directory:
            result = self.layerManager.saveProjectToDisk(directory)
            (success, msg) = result
            if success:
                if msg:
                    msg = f"\nWeitere Informationen: {msg}"
                QtHelper.showInformationBox(
                    self, "Projekt speichern", f"Projekt wurde erfolgreich unter {directory} gespeichert.{msg}")
                if self.stateMachine.currentState == DialogState.REPROJECTDEMAND:
                    self.stateMachine.transitionTo(DialogState.WELCOME)
            else:
                QtHelper.showInformationBox(
                    self, "Projekt speichern", f"Fehler beim Speichern des Projekts unter {directory}:\n{msg}")

    # endregion

    # region WELCOME PAGE
    def onWelcomeNextButton(self):
        self.stateMachine.transitionTo(DialogState.LOCATIONSELECT)

    # endregion

    # region LOCATION PAGE
    def onLocationBackButton(self):
        self.stateMachine.transitionTo(DialogState.WELCOME)

    def onLocationCreateProject(self):
        if self.layerManager.processingConfig.arsCode and self.layerManager.processingConfig.arsCode.code.isZ2():
            QtHelper.showInformationBox(self, "Oberzentrum/Landkreis ausgewählt",
                                        "Die Nutzung des Plugins ist für Mittel- und Grundzentren optimiert. Bei der Anwendung auf Oberzentren oder Landkreise können unter Umständen weniger präzise Ergebnisse auftreten.")

        lineEditText = self.locationProjectNameEdit.text().strip()
        if lineEditText:
            self.layerManager.processingConfig.projectName = lineEditText
            self.layerManager.updateProjectName()
        DialogState.LOCATIONSELECT.value.setBaseLayerStr(
            self.locationBaseMapComboBox.currentText())
        self.setupMapView()
        self.stateMachine.transitionTo(DialogState.CENTERPOINTS)

    def onLocationLineEditTextChanged(self):
        self.locationResultsListWidget.clear()

        results = ARS_INDEX.findNamesBySearchName(self.locationLineEdit.text())
        if results:
            for result in results:
                self.locationResultsListWidget.addItem(result)
        else:
            self.layerManager.processingConfig.setARSCode(None)
            self.locationCreateProject.setEnabled(False)
            self.locationSelectedRegionLabel.setText("")

    def onLocationRegionItemChanged(self, item):
        if not item:
            return
        if self.layerManager.processingConfig.arsCode:
            if self.layerManager.processingConfig.arsCode.name == item.text():
                return

        self.locationSelectedRegionLabel.setText(item.text())
        code = ARS_INDEX.getARSCodeByName(item.text())
        if not code:
            return

        self.layerManager.processingConfig.setARSCode(code)
        self.layerManager.updateProjectName()

        self.locationProjectNameEdit.setText(self.layerManager.projectName)

        self.locationCreateProject.setEnabled(True)

        self.iface.mapCanvas().setCenter(code.center)
        self.iface.mapCanvas().refresh()

    def onLocationSelectExpandInfoLabel(self):
        self.locationSelectExpandInfoLabel.hide()
        self.locationSelectInfoBox.show()

    # endregion

    # region CENTER PAGE

    # HELPERS
    def centerUpdateContextLocsFromUi(self):
        locs = []
        if self.centerLOC2Check.isChecked():
            locs.append(LevelOfCentrality.II)
        if self.centerLOC3Check.isChecked():
            locs.append(LevelOfCentrality.III)
        if self.centerLOC4Check.isChecked():
            locs.append(LevelOfCentrality.IV)
        if self.centerLOCSingleCheck.isChecked():
            locs.append(LevelOfCentrality.Singular)
        if self.centerLOCSurroundingCheck.isChecked():
            locs.append(LevelOfCentrality.Surrounding)

        DialogState.CENTERPOINTS.value.setLOCs(locs)

    # SIGNALS
    def onCentralNextButton(self):
        self.centerUpdateContextLocsFromUi()
        self.stateMachine.transitionTo(DialogState.CENTERPOINTSEDIT)

    def onCentralGenerateButton(self):
        if self.guardLayerRegeneration(DialogState.CENTERPOINTS):
            return

        self.centerUpdateContextLocsFromUi()

        centerLayer = CenterLayer.loadFromFile(
            AUTO_CENTER_POINTS_PATH, self.layerManager.processingConfig.arsCode.code, DialogState.CENTERPOINTS.value.getLOCS())
        if centerLayer:
            DialogState.CENTERPOINTS.value.setCenterLayer(centerLayer)
            self.layerManager.update()
            self.showCenterPointsPage()

    def onCenterMapLayerComboBox(self):
        layer = self.centerMapLayerComboBox.currentLayer()
        if not layer:
            self.centerLoadLayerButton.setEnabled(False)
        else:
            self.centerLoadLayerButton.setEnabled(True)
            # When there was a change, we need to disable the next button so we are
            # forced to load it again
            self.centralNextButton.setEnabled(False)

    def onCenterLoadLayerButton(self):
        if self.guardLayerRegeneration(DialogState.CENTERPOINTS):
            return

        layer = self.centerMapLayerComboBox.currentLayer()
        if not layer:
            return

        if self.guardLayerCrsMistmatch(layer):
            return

        # Check if layer is a valid center layer
        try:
            # Set an empty ARSCodeStr and all LOCs because we do not want to
            # filter anything
            centerLayer = CenterLayer.loadFromLayer(layer)
            if centerLayer:
                DialogState.CENTERPOINTS.value.setCenterLayer(centerLayer)
                self.layerManager.update()
                self.showCenterPointsPage()
        except Exception as e:
            QtHelper.showInformationBox(
                self, "Zentrenlayer", f"Keine valide Zentrenlayer: {e}")

    def onCenterAutoRadioButton(self):
        DialogState.CENTERPOINTS.value.setGenerateMethod(
            DirectRouteGenerateMethod.AUTO)
        self.showCenterPointsPage()

    def onCenterManualRadioButton(self):
        DialogState.CENTERPOINTS.value.setGenerateMethod(
            DirectRouteGenerateMethod.MANUEL)
        self.showCenterPointsPage()

    def onCenterLayerRadioButton(self):
        DialogState.CENTERPOINTS.value.setGenerateMethod(
            DirectRouteGenerateMethod.LAYER)
        self.showCenterPointsPage()

    def onCenterCreateInfoLabel(self):
        self.centerCreateInfoLabel.hide()
        self.centerCreateInfoBox.show()

    # endregion

    # region CENTER EDIT PAGE

    # HELPERS
    def onCenterEditLeave(self):
        self.onCenterEditUnselectTools()

        centerLayer = DialogState.CENTERPOINTS.value.getCenterLayer()
        if not centerLayer:
            return

        editBuffer = centerLayer.qgsLayer().editBuffer()
        if not editBuffer:
            return

        if editBuffer.isModified():
            if self.guardLayerRegeneration(DialogState.CENTERPOINTS):
                centerLayer.qgsLayer().rollBack()
                return
            else:
                centerLayer.qgsLayer().commitChanges()
                centerLayer.update()
                DialogState.CENTERPOINTS.value.setCenterLayer(centerLayer)
                self.layerManager.update()
        else:
            centerLayer.qgsLayer().commitChanges()

    def onCenterEditUnselectTools(self):
        if self.centerEditTool:
            self.centerEditTool.restore()
            self.centerEditAddutton.setChecked(False)
            self.centerEditPropertiesButton.setChecked(False)
            self.centerEditGeometryButton.setChecked(False)
            self.centerEditDeleteButton.setChecked(False)

    # SIGNALS
    def onCenterEditBackButton(self):
        self.onCenterEditLeave()
        self.stateMachine.transitionTo(DialogState.CENTERPOINTS)

    def onCenterEditContinueButton(self):
        self.onCenterEditLeave()
        self.stateMachine.transitionTo(DialogState.AIRLINE)

    def onCenterEditAddutton(self):
        if self.centerEditTool:
            self.centerEditTool.setTool(CenterEditToolType.AddFeature)
            self.centerEditAddutton.setChecked(True)
            self.centerEditPropertiesButton.setChecked(False)
            self.centerEditGeometryButton.setChecked(False)
            self.centerEditDeleteButton.setChecked(False)

    def onCenterEditPropertiesButton(self):
        if self.centerEditTool:
            self.centerEditTool.setTool(CenterEditToolType.PropertyEdit)
            self.centerEditAddutton.setChecked(False)
            self.centerEditPropertiesButton.setChecked(True)
            self.centerEditGeometryButton.setChecked(False)
            self.centerEditDeleteButton.setChecked(False)

    def onCenterEditGeometryButton(self):
        if self.centerEditTool:
            self.centerEditTool.setTool(CenterEditToolType.MoveGeometry)
            self.centerEditAddutton.setChecked(False)
            self.centerEditPropertiesButton.setChecked(False)
            self.centerEditGeometryButton.setChecked(True)
            self.centerEditDeleteButton.setChecked(False)

    def onCenterEditDeleteButton(self):
        if self.centerEditTool:
            self.centerEditTool.setTool(CenterEditToolType.DeleteFeature)
            self.centerEditAddutton.setChecked(False)
            self.centerEditPropertiesButton.setChecked(False)
            self.centerEditGeometryButton.setChecked(False)
            self.centerEditDeleteButton.setChecked(True)

    def onCenterEditUndo(self):
        centerLayer = DialogState.CENTERPOINTS.value.getCenterLayer()
        if not centerLayer:
            return

        undoStack = centerLayer.qgsLayer().undoStack()
        if not undoStack:
            return

        undoStack.undo()

    def onCenterEditRedo(self):
        centerLayer = DialogState.CENTERPOINTS.value.getCenterLayer()
        if not centerLayer:
            return

        undoStack = centerLayer.qgsLayer().undoStack()
        if not undoStack:
            return

        undoStack.redo()

    # endregion

    # region AIRLINE PAGE
    def onAirlineBackButton(self):
        self.stateMachine.transitionTo(DialogState.CENTERPOINTSEDIT)

    def onAirlineContinueButton(self):
        self.stateMachine.transitionTo(DialogState.REPROJECT)

    def onAirlineGenerateButton(self):
        if self.guardLayerRegeneration(DialogState.AIRLINE):
            return

        centerLayer = DialogState.CENTERPOINTS.value.getCenterLayer()

        if not centerLayer:
            return

        drn = DirectRouteNetwork(centerLayer)
        routeEntries = drn.createNetwork()
        directRouteLayer = DirectRouteNetworklayer(
            routeEntries, DirectRouteNetworklayer.LayerName)
        if directRouteLayer:
            DialogState.AIRLINE.value.setDirectRouteLayer(directRouteLayer)
            self.layerManager.update()
            self.showAirlinePage()

    def onAirlineExpandInfoLabel(self):
        self.airlineExpandInfoLabel.hide()
        self.airlineInfoBox.show()

    # endregion

    # region REPROJECT PAGE
    def onReprojectBackButton(self):
        self.stateMachine.transitionTo(DialogState.AIRLINE)

    def onReprojectContinueButton(self):
        self.stateMachine.transitionTo(DialogState.REPROJECTDEMAND)

    def onReprojectGenerateButton(self):
        if self.guardLayerRegeneration(DialogState.REPROJECT):
            return

        directRouteLayer = DialogState.AIRLINE.value.getDirectRouteLayer()

        if not directRouteLayer:
            return
        networkLayer = self.reprojectSelectLayer.currentLayer()
        if not networkLayer:
            return

        if self.guardLayerCrsMistmatch(networkLayer):
            return

        # Check for known datasource to possible filter out invalid edges
        DialogState.REPROJECT.value.setFitlerAttributeMode(
            self.getNetworkSource(networkLayer))

        DialogState.REPROJECT.value.setNetworklayer(networkLayer)

        DialogState.REPROJECT.value.setCenterDistanceTolerance(
            self.reprojectCenterDistanceToleranzSpinbox.value())

        DialogState.REPROJECT.value.setReduceNetworkbounds(
            self.reprojectReduceNetworkBoundsCheckbox.isChecked())

        task = RouteNetworkTask.createAndRunFromContextStateHandler(DialogState.context(
        ), self.onReprojectGenerateResult, self.onReprojectGenerateProgressChanged)

        # task = RouteNetworkTask.createAndRunFromContextStateHandler(DialogState.context(), self.onReprojectGenerateResult, self.onReprojectGenerateProgressChanged)
        # Save the task into the context, so it does not get garbage collected
        DialogState.REPROJECT.value.setProcessing(task)
        DialogState.REPROJECT.value.setIsProcessing(True)

        task.start()
        self.showReprojectPage()

    def onReprojectGenerateResult(
            self, sucess: bool, taskResult: RouteNetworkTaskResult):
        if sucess:
            routeLayer = RouteNetworklayer(taskResult.routeEntries)
            DialogState.REPROJECT.value.setRouteLayer(routeLayer)

            # supplyNetworkLayer = SupplyNetworkElementLayer(taskResult.networkElements)
            # DialogState.REPROJECT.value.setSupplyNetworkLayer(supplyNetworkLayer)
            supplyAggregatedNetworkLayer = SupplyAggregatedNetworkElementLayer(
                taskResult.aggregatedElements)
            missingRouteslayer = MissingRoutesLayer(
                taskResult.getMissingRoutes(), MissingRoutesLayer.LayerNameReproject, "Umlegung")
            DialogState.REPROJECT.value.setAggregatedSupplyNetworkLayer(
                supplyAggregatedNetworkLayer)
            # breakingPointsNetworkLayer = BreakingPointsNetworkLayer(taskResult.breakingPoints)
            # DialogState.REPROJECT.value.setBreakingPointsNetworkLayer(breakingPointsNetworkLayer)
            if missingRouteslayer.routeEntries:
                DialogState.REPROJECT.value.setMissingRoutesLayer(
                    missingRouteslayer)
                QtHelper.showInformationBox(
                    self,
                    "Fehlende Umlegungen",
                    f"Es konnten nicht alle Relationen umgelegt werden. Siehe dazu die Layer '{missingRouteslayer.groupName}.{missingRouteslayer.name()}'")
            self.layerManager.update()
        else:
            QgsMessageLog.logMessage(
                f"Error while processing: {taskResult.error}")

        DialogState.REPROJECT.value.setIsProcessing(False)

        self.showReprojectPage()

    def onReprojectGenerateProgressChanged(
            self, progress: RouteNetworkTaskProgress):
        oldValue = DialogState.REPROJECT.value.setProgress(progress)
        if progress.isDifferentTo(oldValue):
            self.showReprojectPage(fastUpdate=True)

    def onReprojectCancelGenerateButton(self):
        task = DialogState.REPROJECT.value.getProcessing()
        if task:
            task.stop()

    def onReprojectInfoLabel(self):
        self.reprojectInfoLabel.hide()
        self.reprojectInfoBox.show()

    # endregion

    # region REPROJECT DEMAND PAGE
    def onReprojectDemandBackButton(self):
        self.stateMachine.transitionTo(DialogState.REPROJECT)

    def onReprojectDemandGenerateButton(self):
        if self.guardLayerRegeneration(DialogState.REPROJECTDEMAND):
            return

        directRouteLayer = DialogState.AIRLINE.value.getDirectRouteLayer()

        if not directRouteLayer:
            return
        networkLayer = self.reprojectDemandSelectLayer.currentLayer()
        if not networkLayer:
            return

        if self.guardLayerCrsMistmatch(networkLayer):
            return

        # Check for known datasource to possible filter out invalid edges
        DialogState.REPROJECTDEMAND.value.setFitlerAttributeMode(
            self.getNetworkSource(networkLayer))

        DialogState.REPROJECTDEMAND.value.setNetworklayer(networkLayer)

        demandFieldName = self.reprojectDemandSelectField.currentField()
        if not demandFieldName:
            return

        DialogState.REPROJECTDEMAND.value.setDemandFieldName(demandFieldName)

        DialogState.REPROJECTDEMAND.value.setCenterDistanceTolerance(
            self.reprojectDemandCenterDistanceToleranzSpinbox.value())

        DialogState.REPROJECTDEMAND.value.setReduceNetworkbounds(
            self.reprojectDemandReduceNetworkBoundsCheckbox.isChecked())

        task = RouteNetworkTask.createAndRunFromContextStateHandler(DialogState.context(
        ), self.onReprojectDemandGenerateResult, self.onReprojectDemandGenerateProgressChanged)
        # Save the task into the context, so it does not get garbage collected
        DialogState.REPROJECTDEMAND.value.setProcessing(task)
        DialogState.REPROJECTDEMAND.value.setIsProcessing(True)

        task.start()
        self.showReprojectPage()

    def onReprojectDemandSelectLayerChanged(self):
        networkLayer = self.reprojectDemandSelectLayer.currentLayer()
        if not networkLayer:
            return

        self.reprojectDemandSelectField.setLayer(networkLayer)

    def onReprojectDemandGenerateResult(
            self, sucess: bool, taskResult: RouteNetworkTaskResult):
        if sucess:
            routeLayer = RouteNetworklayer(
                taskResult.routeEntries, layerName="Umgelegte Nachfagerelationen", groupName=RouteNetworklayer.DemandGroupname)
            DialogState.REPROJECTDEMAND.value.setRouteLayer(routeLayer)
            supplyAggregatedNetworkLayer = SupplyAggregatedNetworkElementLayer(
                taskResult.aggregatedElements, layerName="Nachfragenetz (aggregiert)", groupName=RouteNetworklayer.DemandGroupname)
            missingRouteslayer = MissingRoutesLayer(taskResult.getMissingRoutes(
            ), layerName=MissingRoutesLayer.LayerNameReprojectDemand, groupName=RouteNetworklayer.DemandGroupname)
            DialogState.REPROJECTDEMAND.value.setAggregatedSupplyNetworkLayer(
                supplyAggregatedNetworkLayer)
            # breakingPointsNetworkLayer = BreakingPointsNetworkLayer(taskResult.breakingPoints, layerName="Netzaufteilung (Nachfrage)", groupName=RouteNetworklayer.DemandGroupname)
            # DialogState.REPROJECTDEMAND.value.setBreakingPointsNetworkLayer(breakingPointsNetworkLayer)
            if missingRouteslayer.routeEntries:
                DialogState.REPROJECTDEMAND.value.setMissingRoutesLayer(
                    missingRouteslayer)
                QtHelper.showInformationBox(
                    self,
                    "Fehlende Umlegungen",
                    f"Es konnten nicht alle Relationen umgelegt werden. Siehe dazu die Layer '{missingRouteslayer.groupName}.{missingRouteslayer.name()}'")

            self.layerManager.update()
        else:
            QgsMessageLog.logMessage(
                f"Error while processing: {taskResult.error}")

        DialogState.REPROJECTDEMAND.value.setIsProcessing(False)

        self.showReprojectDemandPage()

    def onReprojectDemandGenerateProgressChanged(
            self, progress: RouteNetworkTaskProgress):
        oldValue = DialogState.REPROJECTDEMAND.value.setProgress(progress)
        if progress.isDifferentTo(oldValue):
            self.showReprojectDemandPage(fastUpdate=True)

    def onReprojectDemandCancelGenerateButton(self):
        task = DialogState.REPROJECTDEMAND.value.getProcessing()
        if task:
            task.stop()

    def onReprojectReduceNetworkBoundsLabel(self):
        QtHelper.showInformationBox(
            self, "Ausschnitt begrenzen", "Wenn das gewählte Verkehrsnetz größer als der Untersuchungsraum ist, kann die Umlegung sehr lange dauern.\nMit dieser Option wird das Netz auf die Ausdehnung aller Zentrenpunkte und einer Pufferzone von 5 km begrenzt.")

    def onReprojectDemandCenterDistanceLabel(self):
        QtHelper.showInformationBox(self, "Maximale Zentrenverknüpfungsdistanz",
                                    "Maximal valide Distanz zwischen einem Zentrenpunkt und einer Netzkante.\n\nIst ein Zentrenpunkt weiter als die angegebene Distanz von einer Netzkante entfernt, wird der Zentrenpunkt nicht angebunden und ein entsprechender Warnhinweis erscheint.")

    def onReprojectDemandSelectVMLabel(self):
        QtHelper.showInformationBox(self, "Auswahl des Nachfrageattributes",
                                    "Für die Gewichtung des Umlegealgorithmus ist die Auswahl eines Nachfrageattributs (z.B. Verkehrsmengen, DTV etc.) für den Radverkehr Voraussetzung.")

    def onReprojectDemandInfoLabel(self):
        self.reprojectDemandInfoLabel.hide()
        self.reprojectDemandInfoBox.show()

    # endregion
