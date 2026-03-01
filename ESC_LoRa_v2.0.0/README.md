# ESC_LoRa v2.0.0

Code Arduino ESP32 unifié (Master / Slave / Relay) pour LilyGO T3 S3 LR1121 et T-Beam SoftRF SX1276.

## Fonctions incluses
- AP initial: `ESC_LoRa+ID` (effectivement `ESC_LoRa<ID>`), modifiable via page Web WiFi.
- Mode sélectionnable en web: Master / Slave / Relay.
- Appairage ESP-NOW:
  - demande d'appairage envoyée par l'esclave,
  - acceptation côté maître,
  - suppression d'un esclave depuis la page web `/peers`.
- Heartbeat configurable (30 min par défaut).
- Requête maître `pull_data` si pas de données récentes.
- Envoi capteurs seulement si changement de valeur.
- OTA (`ArduinoOTA`).
- MQTT + auto-discovery Home Assistant (capteurs standards + dynamiques).
- Web pages:
  - `/` dashboard,
  - `/wifi` configuration globale,
  - `/gps` configuration GPS,
  - `/sensors` données JSON,
  - `/peers` suivi appairage.
- Variables modifiables: nom code, version, nom module, OLED oui/non.
- Base deep sleep.

## Dépendances Arduino
- ESP32 core
- ArduinoJson
- PubSubClient

## Téléversement
1. Ouvrir `ESC_LoRa_v2.0.0.ino` dans Arduino IDE.
2. Sélectionner une carte ESP32 compatible (T3 S3 LR1121 / T-Beam S3 selon variante).
3. Installer les dépendances.
4. Compiler et téléverser.

## Remarques matérielles
Le fichier contient des `readSensors()` placeholders pour intégrer:
DHT22, MS4525DO, ENS160+AHT21, MAX6675, SCT-013-000+ADS1115, LY254, etc.
Remplacer ces lectures par votre câblage réel.

## Source matérielle
- https://github.com/Xinyuan-LilyGO/LilyGo-LoRa-Series
