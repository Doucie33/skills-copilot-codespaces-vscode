# ESC_LoRa v2.0.0

Code Arduino unifié pour LilyGO **T3 S3 LR1121** et **T-Beam SoftRF SX1276 (915MHz IPEX + AXP2101)**.

## Fonctionnalités intégrées
- Choix du rôle (Master / Slave / Relais) dans la page web `/config`.
- Appairage ESP-NOW avec demande initiée par esclave (`/peers?pair=1`) et suppression des esclaves.
- Heartbeat Master -> esclaves (proof of life) toutes les 30 minutes par défaut (modifiable).
- Requête Master vers esclaves "stale" pour récupération de données absentes.
- Envoi capteurs uniquement quand la charge JSON capteurs change.
- AP initial : `ESC_LoRa+ID` (ID concaténé automatiquement).
- Variables modifiables : nom code, version, nom module, nom réseau LoRa, présence OLED.
- OTA activé (ArduinoOTA).
- Paramètres GPS via page web `/gps`.
- Gestion batterie (tension + pourcentage) + publication MQTT.
- MQTT discovery dynamique pour capteurs déclarés dans `sensors`.
- Page web capteurs (`/sensors`) + état module (`/`).
- GPIO configurables via listes déroulantes.
- Masquage mots de passe optionnel.

## Dépendances Arduino IDE
- ESP32 by Espressif
- PubSubClient
- ArduinoJson (recommandé)
- LoRa (optionnel, pour SX1276)

## Téléversement
1. Ouvrir `ESC_LoRa_v2_0_0.ino` dans Arduino IDE.
2. Sélectionner la bonne carte LilyGO.
3. Installer les dépendances.
4. Compiler et téléverser.

Un zip prêt à l'envoi est fourni à la racine du dépôt : `ESC_LoRa_v2.0.0.zip`.
