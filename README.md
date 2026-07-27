# DigiRad – Digitales Radverkehrskonzept

[![QGIS Version](https://img.shields.io/badge/QGIS-3.16%2B-blue)](https://www.qgis.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.7.4-orange)](https://github.com/VisionVelo/DigiRad/releases)

![DigiRad Logo](res/NRVP_DigiRad_Projektlogo.jpg)

Ein QGIS-Plugin für die nutzungsdatengestützte Radnetzentwicklung mit GPS-Daten aus Crowdsourcing-Anwendungen.

## Beschreibung

DigiRad ist ein QGIS-Plugin, das die automatiserte Erstellung von Radverkehrsnetzen ermöglicht. Das Tool identifiziert wichtige Quellen und Ziele, erstellt ein Luftliniennetz und legt dieses auf das bestehende Straßen- und Wegenetz um.

## Funktionen

- **Automatische Netzentwicklung**: Automatisierte Erstellung von Zielnetzen aus Luftlinien
- **RIN-konforme Planung**: Definition von Quellen und Senken nach Richtlinien für integrierte Netzgestaltung
- **Nachfragebasierte Umlegung**: Integration genutzter Wege aus Crowdsourcing-GPS-Daten
- **Offene Daten**: Unterstützung von Daten aus der Mobilithek und OpenStreetMap
- **Standardisierte Arbeitsabläufe**: Wiederholbare und dokumentierte Planungsprozesse

## Installation

### Voraussetzungen

- QGIS 3.16 oder höher
- Python 3.x

### Installationsmethoden

#### Methode 1: QGIS Plugin Manager

1. Öffnen Sie QGIS
2. Gehen Sie zu `Erweiterungen` → `Erweiterungen verwalten und installieren`
3. Suchen Sie nach "DigiRad"
4. Klicken Sie auf `Installieren`

#### Methode 2: Manuelle Installation

1. Laden Sie das Plugin als [ZIP-Datei](https://github.com/VisionVelo/DigiRad/releases/download/v0.7.4/visionvelo_digirad.zip) herunter
2. Entpacken Sie die Datei in Ihren QGIS-Plugins-Ordner:
   - **Windows**: `C:\Users\<Benutzername>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
   - **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
3. Starten Sie QGIS neu
4. Aktivieren Sie das Plugin unter `Erweiterungen` → `Erweiterungen verwalten und installieren`

## Nutzung

### Grundlegender Arbeitsablauf

1. **Projekt starten**: Neues DigiRad-Projekt im Plugin erstellen
2. **Verkehrsnetz laden**: Straßennetz als Shapefile oder GeoPackage hochladen
3. **Zentren definieren**: Quellen und Senken nach RIN festlegen
4. **Luftliniennetz erzeugen**: Automatisiertes Luftliniennetz erstellen
5. **Netzumlegung**: Luftliniennetz auf das Wegenetz umlegen
6. **Nachfrageintegration**: GPS-Routen aus Crowdsourcing integrieren

### Weitere Informationen

Weiteführende Informationen finden Sie auf unserer [Plugin-Seite](https://vision-velo.de/digirad-digitales-radverkehrskonzept/) sowie in unserem [Anwendungsleitfaden](https://vision-velo.de/wp-content/uploads/2026/06/020626_DigiRad_Leitfaden-zum-Plugin.pdf).

Weitere Informationen zum Projekt finden Sie auch unter der [Projektseite im Mobilitätsforum Bund](https://www.mobilitaetsforum.bund.de/DE/Themen/Wissenspool/Projekte/NRVP/NRVP_23-25/NRVP_IGS-ING_DigiRad_2024-2025.html).

## Projektstruktur

```
visionvelo_digirad/
├── classes/              # Hauptlogik des Plugins
│   ├── layers/          # Layer-Verwaltung
│   ├── processing/      # Netzverarbeitung
│   └── routing/         # Routing-Algorithmen
├── dat/                  # Datendateien
│   ├── ARS_Zentren_merged.csv
│   ├── DigiRadAutoZentren.gpkg
│   └── DigiRadUmgebungsgemeinden.gpkg
├── help/                 # Dokumentation
└── res/                  # Ressourcen
```

## Projektpartner

### Projektleitung

[**Vision Velo GmbH**](https://vision-velo.de)

### Projektbeteiligte

[**IGS Ingenieurgesellschaft Stolz mbH**](https://www.igs-ingenieure.de/)

## Finanzierung

Das Projekt wird vom **Bundesministerium für Verkehr (BMV)** aus Mitteln zur Umsetzung des Nationalen Radverkehrsplans (NRVP) gefördert.

Weitere Informationen zur Projektfinanzierung finden Sie unter der [Projektseite des Fördermittelgebers](https://www.mobilitaetsforum.bund.de/DE/Themen/Wissenspool/Projekte/NRVP/NRVP_23-25/NRVP_IGS-ING_DigiRad_2024-2025.html).

<div style="display: flex; gap: 20px; align-items: center;">
  <img src="res/bmv_resize_trans.png" alt="Logo BMV" width="150"/>
  <img src="res/nicht_investiv.png" alt="Logo Nicht Investiv" width="150"/>
</div>

## Lizenz

Dieses Projekt ist unter der Apache License 2.0 lizenziert – siehe [LICENSE](LICENSE) und [NOTICE](NOTICE) für Details.

Copyright (c) 2025-2026 Vision Velo GmbH

## Kontakt

- **Probleme**: https://github.com/VisionVelo/DigiRad/issues
- **Repository**: https://github.com/VisionVelo/DigiRad
