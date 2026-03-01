# ESC_LoRa v2.0.0

Projet Arduino/ESP32 prêt à téléverser pour une base **Master / Slave / Relay** avec:

- ESP-NOW mesh (appairage, désappairage, heartbeat, ping/pong, demande de report).
- Web UI: WiFi, rôle, GPS, GPIO, mesh, capteurs.
- MQTT + Home Assistant discovery (statique + dynamique via JSON déclaré par l'esclave).
- OTA, deep sleep, batterie, envoi conditionnel des données capteurs.

## Cartes ciblées
- LilyGO T3 S3 LR1121
- LilyGO T-Beam SoftRF SX1276 915MHz IPEX AXP2101

## Dépendances Arduino (Library Manager)
- ArduinoJson
- PubSubClient
- DHT sensor library

## Notes capteurs
Le squelette est prêt pour les capteurs demandés (DHT22, MS4525DO, ENS160+AHT21, MAX6675, LY254, YWBL-WH, SCT-013-000 + ADS1115),
avec l'architecture dynamique MQTT Discovery.
Ajoutez/activez les drivers spécifiques dans la fonction `pollSensors()` selon votre câblage final.

## ZIP
Le dossier contient le code principal:
- `ESC_LoRa.ino`

Vous pouvez zipper ce dossier directement pour téléversement.
