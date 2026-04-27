# LDIC-G v1.0 — Langage de programmation complet

## Langage Domotique Immotique Contrôle — Global

LDIC-G est un langage de programmation universel conçu pour contrôler des bâtiments domestiques, commerciaux, agricoles et industriels.

Il est conçu pour être utilisé avec :

- ESP32 / Arduino
- Raspberry Pi
- Home Assistant
- MQTT
- Python / PyCharm
- Visual Studio Code
- pages Web locales
- LoRa
- ESP-NOW
- Modbus
- BACnet/IP via passerelle ou serveur

---

## 1. Objectif du langage

LDIC-G doit permettre de programmer simplement :

- chauffage
- ventilation
- climatisation
- pression bâtiment
- qualité d’air
- éclairage
- pompes
- vannes
- relais
- moteurs
- VFD
- capteurs
- alarmes
- sécurités
- PID
- horaires
- modes
- séquences industrielles
- équipements domestiques et industriels

Principe fondamental :

```text
Home Assistant / serveur = supervision
ESP32 = contrôle local autonome
LDIC-G = logique bâtiment
Sécurité = toujours locale et prioritaire
```

---

## 2. Règle de langue officielle

LDIC-G supporte deux langues :

```text
Français : syntaxe principale
Anglais  : syntaxe internationale
```

Un programme ne doit pas mélanger les mots-clés français et anglais.

### Français

```ldic
LANGUE fr-CA
UNITES MT
```

### Anglais

```ldic
LANGUAGE en-US
UNITS METRIC
```

---

## 3. Structure générale française

```ldic
PROJET Nom_Projet
LANGUE fr-CA
PAYS CA
FUSEAU_HORAIRE America/Montreal
UNITES MT
VERSION 1.0

BATIMENT Nom_Batiment
TYPE_BATIMENT industriel

ZONE Nom_Zone
  // Déclarations
  CAPTEUR ...
  ENTREE ...
  SORTIE ...
  CONSIGNE ...
  VARIABLE ...

  // Logique
  HORAIRE ...
  MODE ...
  PID ...
  BOUCLE ...
  SI ... ALORS
  FIN
  SECURITE ...
  ALARME ...
FIN_ZONE

MQTT
  BASE_TOPIC "ldic/batiment"
FIN_MQTT

FIN_PROJET
```

---

## 4. Structure générale anglaise

```ldic
PROJECT Project_Name
LANGUAGE en-US
COUNTRY US
TIMEZONE America/New_York
UNITS METRIC
VERSION 1.0

BUILDING Building_Name
BUILDING_TYPE industrial

ZONE Zone_Name
  SENSOR ...
  INPUT ...
  OUTPUT ...
  SETPOINT ...
  VARIABLE ...

  SCHEDULE ...
  MODE ...
  PID ...
  LOOP ...
  IF ... THEN
  END
  SAFETY ...
  ALARM ...
END_ZONE

MQTT
  BASE_TOPIC "ldic/building"
END_MQTT

END_PROJECT
```

---

## 5. Mots-clés français / anglais

| Français       | Anglais       | Description                |
| -------------- | ------------- | -------------------------- |
| PROJET         | PROJECT       | Début du projet            |
| FIN_PROJET     | END_PROJECT   | Fin du projet              |
| LANGUE         | LANGUAGE      | Langue du programme        |
| PAYS           | COUNTRY       | Pays                       |
| FUSEAU_HORAIRE | TIMEZONE      | Fuseau horaire             |
| UNITES         | UNITS         | Système d’unités           |
| BATIMENT       | BUILDING      | Bâtiment                   |
| TYPE_BATIMENT  | BUILDING_TYPE | Type de bâtiment           |
| ZONE           | ZONE          | Zone contrôlée             |
| FIN_ZONE       | END_ZONE      | Fin de zone                |
| CAPTEUR        | SENSOR        | Capteur                    |
| ENTREE         | INPUT         | Entrée                     |
| SORTIE         | OUTPUT        | Sortie                     |
| CONSIGNE       | SETPOINT      | Consigne                   |
| VARIABLE       | VARIABLE      | Variable interne           |
| SI             | IF            | Condition                  |
| ALORS          | THEN          | Début action               |
| SINON          | ELSE          | Alternative                |
| SINON_SI       | ELSE_IF       | Alternative conditionnelle |
| FIN            | END           | Fin de bloc simple         |
| HORAIRE        | SCHEDULE      | Horaire                    |
| FIN_HORAIRE    | END_SCHEDULE  | Fin horaire                |
| BOUCLE         | LOOP          | Boucle                     |
| FIN_BOUCLE     | END_LOOP      | Fin boucle                 |
| PID            | PID           | Boucle PID                 |
| FIN_PID        | END_PID       | Fin PID                    |
| ALARME         | ALARM         | Alarme                     |
| FIN_ALARME     | END_ALARM     | Fin alarme                 |
| SECURITE       | SAFETY        | Sécurité prioritaire       |
| FIN_SECURITE   | END_SAFETY    | Fin sécurité               |
| ARBITRE        | ARBITER       | Arbitrage de sortie        |
| FIN_ARBITRE    | END_ARBITER   | Fin arbitre                |
| ACTIVER        | ENABLE        | Activer                    |
| DESACTIVER     | DISABLE       | Désactiver                 |
| FORCER         | FORCE         | Forcer une sortie          |
| LIBERER        | RELEASE       | Libérer un forçage         |
| NOEUD          | NODE          | Module / contrôleur        |
| EQUIPEMENT     | EQUIPMENT     | Équipement                 |

---

## 6. Systèmes d’unités

```ldic
UNITES MT          // métrique
UNITES IMPERIAL    // impérial
```

En anglais :

```ldic
UNITS METRIC
UNITS IMPERIAL
```

---

## 7. Unités supportées

### Température

```ldic
C
F
K
```

### Pression

```ldic
Pa
kPa
bar
psi
inHg
mmHg
```

### Débit

```ldic
L/s
m3/h
CFM
L/min
gpm
```

### Électricité

```ldic
V
A
mA
W
kW
Wh
kWh
Hz
```

### Qualité d’air

```ldic
ppm
ppb
ug/m3
Bq/m3
pCi/L
```

### Distance / niveau

```ldic
mm
cm
m
in
ft
%
L
gal
```

### Temps

```ldic
ms
s
min
h
j
```

---

## 8. Commentaires

### Commentaire ligne

```ldic
// Ceci est un commentaire
```

### Commentaire en fin de ligne

```ldic
CAPTEUR Temp TYPE temperature UNITE C // capteur température
```

### Commentaire multi-lignes

```ldic
/*
Commentaire sur plusieurs lignes
*/
```

---

## 9. Règles de nommage

Les noms internes doivent respecter :

```text
Lettres, chiffres et underscore seulement.
Pas d’espace.
Pas d’accent.
Ne pas commencer par un chiffre.
```

Correct :

```ldic
Temp_Bureau
Vanne_Chauffage
Pompe_1
PID_Pression
```

Incorrect :

```ldic
Température Bureau
1Pompe
Vanne-Chauffage
```

---

## 10. Types de bâtiments

Français :

```ldic
residentiel
commercial
industriel
hopital
ecole
agricole
entrepot
laboratoire
bureau
mixte
```

Anglais :

```ldic
residential
commercial
industrial
hospital
school
agriculture
warehouse
laboratory
office
mixed
```

---

## 11. Équipements

```ldic
EQUIPEMENT AHU_Atelier TYPE unite_ventilation ZONE Atelier
EQUIPEMENT Pompe_1 TYPE pompe ZONE Chaufferie
EQUIPEMENT VFD_Fan TYPE vfd ZONE Atelier
```

Types d’équipements :

```ldic
chaudiere
thermopompe
unite_ventilation
echangeur_air
erv
hrv
refroidisseur
ventilateur
pompe
registre
vanne
vfd
eclairage
compresseur
generatrice
reservoir
porte
convoyeur
depoussiereur
serpentin_chauffage
serpentin_refroidissement
plancher_chauffant
osmoseur
vacuum
humidificateur
deshumidificateur
```

---

## 12. Capteurs

Syntaxe française :

```ldic
CAPTEUR Nom TYPE type_capteur UNITE unite SOURCE source
```

Syntaxe anglaise :

```ldic
SENSOR Name TYPE sensor_type UNIT unit SOURCE source
```

Exemples :

```ldic
CAPTEUR Temp_Bureau TYPE temperature UNITE C SOURCE mqtt "bureau/temp"
CAPTEUR CO2_Bureau TYPE co2 UNITE ppm SOURCE i2c
CAPTEUR Vacuum_Ligne TYPE vacuum UNITE inHg SOURCE analogique GPIO34
CAPTEUR Radon_SousSol TYPE radon UNITE Bq/m3 SOURCE mqtt "maison/radon"
```

Types de capteurs :

```ldic
temperature
humidite
pression
vacuum
co2
tvoc
aqi
radon
courant
tension
puissance
energie
niveau
debit
debit_air
debit_eau
luminosite
presence
mouvement
contact
fumee
gaz
vibration
bruit
pluie
vent_vitesse
vent_direction
batterie
rssi
etat
```

---

## 13. Entrées

```ldic
ENTREE Bouton_Mode TYPE numerique GPIO12
ENTREE Contact_Porte TYPE numerique GPIO14
ENTREE Signal_Niveau TYPE analogique GPIO34 UNITE %
```

Types :

```ldic
numerique
analogique
impulsion
compteur
frequence
i2c
spi
mqtt
virtuelle
```

---

## 14. Sorties

Chaque sortie physique doit avoir un état sécuritaire.

```ldic
SORTIE Chauffage TYPE relais GPIO25 ETAT_SECURITE OFF
SORTIE Ventilateur TYPE pwm GPIO26 UNITE % MIN 0 % MAX 100 % ETAT_SECURITE 0 %
SORTIE Vanne_Chauffage TYPE 0_10v CANAL 1 UNITE % MIN 0 % MAX 100 % ETAT_SECURITE 0 %
```

Types de sorties :

```ldic
relais
pwm
analogique
0_10v
4_20ma
vanne
moteur
ventilateur
pompe
chauffage
refroidissement
lumiere
alarme
buzzer
registre
vfd
servo
mqtt
virtuelle
```

Règle obligatoire :

```text
Aucune sortie physique n’est acceptée sans ETAT_SECURITE.
```

---

## 15. Variables

```ldic
VARIABLE Demande_Chauffage = OFF
VARIABLE Sortie_PID = 0 %
VARIABLE Mode_Communication = LOCAL
VARIABLE Temp_Moyenne = 0 C
```

Types internes :

```ldic
BOOL
ENTIER
REEL
TEXTE
TEMPS
DATE_HEURE
POURCENT
VALEUR_UNITE
```

---

## 16. Consignes

```ldic
CONSIGNE Temp_Confort = 22 C MODIFIABLE MIN 16 C MAX 26 C PAS 0.5 C
CONSIGNE CO2_Max = 1000 ppm MODIFIABLE MIN 600 ppm MAX 1500 ppm PAS 50 ppm
CONSIGNE Pression_Cible = 5 Pa MODIFIABLE MIN 0 Pa MAX 20 Pa PAS 1 Pa
```

Une consigne peut être liée à Home Assistant :

```ldic
CONSIGNE Temp_Confort = 22 C MODIFIABLE HA number MIN 16 C MAX 26 C PAS 0.5 C
```

---

## 17. Conditions

```ldic
SI Temp_Bureau < Temp_Confort ALORS
  Chauffage = ON
FIN
```

Avec SINON :

```ldic
SI Occupation = ON ALORS
  Mode_Bureau = OCCUPE
SINON
  Mode_Bureau = INOCCUPE
FIN
```

Avec SINON_SI :

```ldic
SI Temp_Bureau < 20 C ALORS
  Mode_Temp = CHAUFFAGE
SINON_SI Temp_Bureau > 24 C ALORS
  Mode_Temp = REFROIDISSEMENT
SINON
  Mode_Temp = NEUTRE
FIN
```

Opérateurs :

```ldic
=
!=
>
<
>=
<=
ET
OU
NON
ENTRE
```

---

## 18. États standards

```ldic
ON
OFF
AUTO
MANUEL
OUVERT
FERME
START
STOP
ACTIF
INACTIF
VRAI
FAUX
HAUT
BAS
NORMAL
DEFAUT
ALARME
LOCAL
DISTANT
```

---

## 19. Horaires

```ldic
HORAIRE Horaire_Jour
  LUN 06:00 A 18:00
  MAR 06:00 A 18:00
  MER 06:00 A 18:00
  JEU 06:00 A 18:00
  VEN 06:00 A 18:00
FIN_HORAIRE
```

Jours :

```ldic
LUN
MAR
MER
JEU
VEN
SAM
DIM
FERIE
```

Utilisation :

```ldic
SI Horaire_Jour = ON ALORS
  Temp_Active = Temp_Confort
SINON
  Temp_Active = Temp_Nuit
FIN
```

---

## 20. Modes

```ldic
MODE Mode_Batiment OPTIONS AUTO, MANUEL, OCCUPE, INOCCUPE, NUIT, HORS_GEL, URGENCE DEFAULT AUTO
```

Modes recommandés :

```ldic
AUTO
MANUEL
OCCUPE
INOCCUPE
NUIT
HORS_GEL
ECONOMIE
CONFORT
MAINTENANCE
URGENCE
ARRET
```

---

## 21. PID indépendant

Un PID est un objet indépendant, réglable séparément et activable dans la logique.

```ldic
PID PID_Chauffage
  ENTREE Temp_Bureau
  CONSIGNE Temp_Confort
  SORTIE Vanne_Chauffage
  KP 2.0 MODIFIABLE MIN 0 MAX 20 PAS 0.1
  KI 0.4 MODIFIABLE MIN 0 MAX 10 PAS 0.1
  KD 0.1 MODIFIABLE MIN 0 MAX 10 PAS 0.1
  SORTIE_MIN 0 %
  SORTIE_MAX 100 %
  CYCLE 5 s
  ACTION chauffage
  ANTI_WINDUP ON
FIN_PID
```

Règle PID :

```text
ENTREE et CONSIGNE utilisent la même unité physique.
SORTIE_MIN et SORTIE_MAX utilisent l’unité de commande : %, V, Hz, etc.
```

Ne pas faire :

```ldic
SORTIE_MIN 18 C
SORTIE_MAX 22 C
```

Faire :

```ldic
SORTIE_MIN 0 %
SORTIE_MAX 100 %
```

---

## 22. Plusieurs PID

LDIC-G accepte plusieurs PID dans un même programme.

```ldic
PID PID_Chauffage
  ENTREE Temp_Atelier
  CONSIGNE Temp_Confort
  SORTIE Vanne_Chauffage
  KP 2.0
  KI 0.3
  KD 0.1
  SORTIE_MIN 0 %
  SORTIE_MAX 100 %
  CYCLE 5 s
  ACTION chauffage
FIN_PID

PID PID_Pression
  ENTREE Pression_Batiment
  CONSIGNE Pression_Cible
  SORTIE Admission_Air
  KP 1.5
  KI 0.2
  KD 0.0
  SORTIE_MIN 20 %
  SORTIE_MAX 100 %
  CYCLE 2 s
  ACTION direct
FIN_PID
```

Règle :

```text
Une même sortie physique ne doit pas être contrôlée directement par deux PID sans ARBITRE.
```

---

## 23. Boucles de contrôle supportées

```ldic
PID
PI
PD
ON_OFF
HYSTERESIS
FLOTTANT
MODULANT
RAMPE
RESET
SCALE
LIMITE
BANDE_MORTE
ANTI_WINDUP
LEAD_LAG
SEQUENCEUR
ECONOMISEUR
TEMPS_MIN_ON
TEMPS_MIN_OFF
TIMER_ON
TIMER_OFF
MOYENNE
FILTRE
```

---

## 24. Hystérésis

```ldic
BOUCLE Chauffage_ONOFF TYPE HYSTERESIS
  ENTREE Temp_Bureau
  CONSIGNE Temp_Confort
  DIFF 1 C
  SORTIE Chauffage
  ACTION chauffage
  CYCLE 5 s
FIN_BOUCLE
```

---

## 25. Fonctions intégrées

### SCALE

```ldic
VARIABLE Niveau_Eau = SCALE(Analog_Niveau, 0, 4095, 0 %, 100 %)
```

### LIMITE

```ldic
Ventilation = LIMITE(Demande_Ventilation, 30 %, 100 %)
```

### RAMPE

```ldic
VFD_Fan = RAMPE(Demande_Fan, 5 %/s)
```

### MOYENNE

```ldic
Temp_Moyenne = MOYENNE(Temp_Bureau, 10 min)
```

### FILTRE

```ldic
Pression_Filtree = FILTRE(Pression_Batiment, 0.2)
```

### ABS

```ldic
Erreur = ABS(Temp_Bureau - Temp_Confort)
```

---

## 26. Temporisateurs

```ldic
TIMER_ON Delai_Demarrage_Fan
  ENTREE Demande_Ventilation
  DELAI 30 s
FIN_TIMER

TIMER_OFF Delai_Arret_Fan
  ENTREE Demande_Ventilation
  DELAI 120 s
FIN_TIMER
```

---

## 27. Temps minimum ON/OFF

```ldic
BOUCLE Compresseur_Control TYPE ON_OFF
  ENTREE Temp_Local
  CONSIGNE 24 C
  DIFF 1 C
  SORTIE Compresseur
  TEMPS_MIN_ON 180 s
  TEMPS_MIN_OFF 300 s
FIN_BOUCLE
```

---

## 28. Lead/Lag

```ldic
BOUCLE Pompes_Circulation TYPE LEAD_LAG
  SORTIES Pompe_1, Pompe_2
  ROTATION 7 j
  DEMARRER_SI Demande_Chauffage = ON
  DEUXIEME_ETAGE_SI Demande_Chauffage > 80 %
FIN_BOUCLE
```

---

## 29. Séquenceur

```ldic
BOUCLE Chauffage_Etages TYPE SEQUENCEUR
  ENTREE Demande_Chauffage
  SORTIES Stage_1, Stage_2, Stage_3
  ON_A 30 %, 60 %, 90 %
  OFF_A 20 %, 50 %, 80 %
  DELAI_ENTRE_ETAGES 60 s
FIN_BOUCLE
```

---

## 30. Économiseur HVAC

```ldic
BOUCLE Economiseur_Air TYPE ECONOMISEUR
  TEMP_EXT Temp_Exterieure
  TEMP_RET Temp_Retour
  CO2 CO2_Zone
  SORTIE Registre_Air_Neuf
  MIN_AIR_NEUF 20 %
  MAX_AIR_NEUF 100 %
  ACTIF_SI Temp_Exterieure < Temp_Retour
FIN_BOUCLE
```

---

## 31. Alarmes

```ldic
ALARME CO2_Haut
  SI CO2_Atelier > 1200 ppm ALORS
    MESSAGE "CO2 élevé dans atelier"
    PRIORITE moyenne
    NOTIFIER home_assistant
  FIN
FIN_ALARME
```

Priorités :

```ldic
info
basse
moyenne
haute
critique
```

---

## 32. Sécurités

Les sécurités passent avant tout.

```ldic
SECURITE Surchauffe
  SI Temp_Bureau > 35 C ALORS
    DESACTIVER PID_Chauffage
    Chauffage = OFF
    ALARME "Surchauffe détectée"
  FIN
FIN_SECURITE
```

Protection antigel :

```ldic
SECURITE Protection_Antigel
  SI Temp_Air_Soufflage < 5 C ALORS
    Fan = OFF
    Vanne_Chauffage = 100 %
    ALARME "Protection antigel active"
  FIN
FIN_SECURITE
```

Règle :

```text
SECURITE est toujours prioritaire sur LOGIQUE, PID, HORAIRE et MQTT.
```

---

## 33. Priorités officielles

```text
1. Arrêt d’urgence
2. Sécurité locale
3. Capteur critique en défaut
4. Forçage manuel local
5. Commande distante valide
6. Horaire
7. PID / boucles
8. Logique normale
9. État par défaut
```

---

## 34. Arbitre de sortie

```ldic
ARBITRE Vanne_Chauffage
  PRIORITE SECURITE > MANUEL > PID > LOGIQUE
  DEFAUT 0 %
FIN_ARBITRE
```

Règle :

```text
Une sortie physique doit avoir une seule valeur finale appliquée.
```

---

## 35. MQTT

```ldic
MQTT
  BROKER "192.168.1.10"
  PORT 1883
  UTILISATEUR "mqtt_user"
  MOT_DE_PASSE "mqtt_password"
  BASE_TOPIC "ldic/batiment1"
  DECOUVERTE home_assistant
  HEARTBEAT 30 s
FIN_MQTT
```

Topics recommandés :

```text
ldic/batiment1/status
ldic/batiment1/zone/atelier/capteurs/temp/etat
ldic/batiment1/zone/atelier/sorties/chauffage/etat
ldic/batiment1/zone/atelier/sorties/chauffage/set
ldic/batiment1/programme/set
ldic/batiment1/programme/etat
ldic/batiment1/alarme
ldic/batiment1/heartbeat
```

---

## 36. Home Assistant

LDIC-G peut générer :

```text
sensor
binary_sensor
switch
number
select
button
text
alarm
```

Exemple :

```ldic
CONSIGNE Temp_Confort = 22 C MODIFIABLE HA number
SORTIE Chauffage TYPE relais HA switch
CAPTEUR Temp_Bureau TYPE temperature HA sensor
MODE Mode_Bureau HA select
```

---

## 37. ESP32 autonome

Chaque ESP32 doit pouvoir garder :

```text
/program.ldic
/program.json
/program_backup.ldic
/config.json
/safety.json
/pid.json
/last_state.json
/log.txt
```

Comportement obligatoire :

```text
Si MQTT est perdu, l’ESP32 continue localement.
Si Home Assistant tombe, l’ESP32 continue localement.
Si le Raspberry Pi tombe, l’ESP32 continue localement.
Si un capteur critique tombe, l’ESP32 applique la sécurité.
```

---

## 38. Page Web locale ESP32

Fonctions minimales :

```text
- éditer le programme LDIC-G
- valider la syntaxe
- sauvegarder dans LittleFS
- tester le programme
- voir les capteurs
- voir les sorties
- voir les PID
- voir les alarmes
- revenir à l’ancienne version
```

Flux :

```text
Page Web ESP32
↓
Programme LDIC-G
↓
Validation locale
↓
Sauvegarde LittleFS
↓
Exécution autonome
```

---

## 39. Watchdog

```ldic
WATCHDOG MQTT_Watchdog
  ENTREE MQTT_Status
  TIMEOUT 60 s
  SI_TIMEOUT Mode_Communication = LOCAL
FIN_WATCHDOG
```

```ldic
SI Mode_Communication = LOCAL ALORS
  ALARME "Mode local actif : MQTT perdu"
FIN
```

---

## 40. Nœuds maître / esclave

```ldic
NOEUD ESP32_Master ROLE maitre PROTOCOLE mqtt, espnow, lora
NOEUD ESP32_Slave_01 ROLE esclave PROTOCOLE espnow
NOEUD ESP32_Slave_02 ROLE esclave PROTOCOLE lora
```

Capteur distant :

```ldic
CAPTEUR Temp_Remote TYPE temperature UNITE C NOEUD ESP32_Slave_01
SORTIE Relais_Remote TYPE relais NOEUD ESP32_Slave_01 GPIO25 ETAT_SECURITE OFF
```

---

## 41. Protocoles supportés

```ldic
mqtt
http
websocket
espnow
lora
modbus_rtu
modbus_tcp
bacnet_ip
gpio
i2c
spi
uart
onewire
```

---

## 42. Compatibilité IEC 61131-3

LDIC-G peut être converti vers une logique proche du Structured Text.

LDIC-G :

```ldic
SI Temp_Bureau < Consigne_Temp ALORS
  Chauffage = ON
SINON
  Chauffage = OFF
FIN
```

Structured Text :

```pascal
IF Temp_Bureau < Consigne_Temp THEN
  Chauffage := TRUE;
ELSE
  Chauffage := FALSE;
END_IF;
```

---

## 43. Compatibilité BACnet

| LDIC-G              | BACnet                     |
| ------------------- | -------------------------- |
| CAPTEUR temperature | Analog Input               |
| CAPTEUR humidite    | Analog Input               |
| CAPTEUR pression    | Analog Input               |
| CAPTEUR contact     | Binary Input               |
| SORTIE relais       | Binary Output              |
| SORTIE analogique   | Analog Output              |
| CONSIGNE numérique  | Analog Value               |
| VARIABLE booléenne  | Binary Value               |
| MODE                | Multi-state Value          |
| HORAIRE             | Schedule                   |
| ALARME              | Notification Class / Event |
| HISTORIQUE          | Trend Log                  |
| CONTROLEUR          | Device                     |

Exemple :

```ldic
CAPTEUR Temp_Bureau TYPE temperature UNITE C BACNET AI 1
SORTIE Vanne_Chauffage TYPE analogique UNITE % BACNET AO 1
MODE Mode_Bureau OPTIONS AUTO, MANUEL, NUIT BACNET MSV 1
```

---

## 44. Tags sémantiques

```ldic
CAPTEUR Temp_Bureau TYPE temperature UNITE C TAGS zone,bureau,temp,air,sensor
SORTIE Vanne_Chauffage TYPE analogique UNITE % TAGS heating,valve,cmd
```

---

## 45. Validation et erreurs

Un programme invalide ne doit jamais être exécuté.

En cas d’erreur :

```text
1. Le nouveau programme est refusé.
2. L’ancien programme valide reste actif.
3. Le fichier refusé peut être sauvegardé comme brouillon.
4. Les erreurs sont affichées.
5. Les sorties ne changent pas.
6. Les sécurités locales restent actives.
```

Format d’erreur :

```text
ERREUR LDIC-001
Ligne : 12
Colonne : 24
Message : Mot-clé inconnu ALOR
Suggestion : remplacer ALOR par ALORS
```

Codes principaux :

```text
LDIC-001 Mot-clé inconnu
LDIC-002 Mot-clé obligatoire manquant
LDIC-003 Bloc non fermé
LDIC-004 Bloc fermé sans ouverture
LDIC-005 Langue incohérente
LDIC-010 Variable non déclarée
LDIC-011 Capteur non déclaré
LDIC-012 Sortie non déclarée
LDIC-016 Sortie sans état sécuritaire
LDIC-100 Unité inconnue
LDIC-105 Mauvaise unité pour sortie PID
LDIC-150 SI sans ALORS
LDIC-153 FIN manquant
LDIC-200 PID sans ENTREE
LDIC-201 PID sans CONSIGNE
LDIC-202 PID sans SORTIE
LDIC-203 PID sans limites de sortie
LDIC-204 Deux PID sur même sortie sans arbitre
LDIC-300 SECURITE mal formée
LDIC-400 Topic MQTT invalide
```

---

## 46. Compilateur LDIC-G

Entrée :

```text
programme.ldic
```

Sorties :

```text
programme.json              Runtime ESP32
programme.yaml              Home Assistant
programme_mqtt.json         Topics MQTT
programme_bacnet.json       Objets BACnet
programme_modbus.json       Table Modbus
programme_st.txt            Structured Text IEC
rapport_validation.txt      Erreurs et avertissements
```

Commandes proposées :

```bash
ldic compile usine.ldic --target esp32 --output programme.json
ldic compile usine.ldic --target homeassistant --output programme.yaml
ldic compile usine.ldic --target bacnet --output bacnet.json
ldic compile usine.ldic --target st --output programme_st.txt
```

---

## 47. Format JSON interne

```json
{
  "projet": "Maison",
  "langue": "fr-CA",
  "pays": "CA",
  "fuseau_horaire": "America/Montreal",
  "unites": "MT",
  "batiment": {
    "nom": "Maison_Principale",
    "type": "residentiel"
  },
  "zones": [
    {
      "nom": "Salon",
      "capteurs": [
        {
          "nom": "Temp_Salon",
          "type": "temperature",
          "unite": "C"
        }
      ],
      "sorties": [
        {
          "nom": "Chauffage_Salon",
          "type": "relais",
          "etat_securite": "OFF"
        }
      ]
    }
  ]
}
```

---

## 48. Exemple complet résidentiel

```ldic
PROJET Maison
LANGUE fr-CA
PAYS CA
FUSEAU_HORAIRE America/Montreal
UNITES MT
VERSION 1.0

BATIMENT Maison_Principale
TYPE_BATIMENT residentiel

ZONE Salon
  CAPTEUR Temp_Salon TYPE temperature UNITE C SOURCE mqtt "maison/salon/temp"
  CAPTEUR Hum_Salon TYPE humidite UNITE % SOURCE mqtt "maison/salon/hum"
  SORTIE Chauffage_Salon TYPE relais GPIO25 ETAT_SECURITE OFF

  CONSIGNE Temp_Confort = 22 C MODIFIABLE MIN 16 C MAX 26 C PAS 0.5 C
  CONSIGNE Temp_Nuit = 18 C MODIFIABLE MIN 14 C MAX 22 C PAS 0.5 C
  VARIABLE Temp_Active = 22 C

  HORAIRE Horaire_Jour
    LUN 06:00 A 22:00
    MAR 06:00 A 22:00
    MER 06:00 A 22:00
    JEU 06:00 A 22:00
    VEN 06:00 A 22:00
    SAM 07:00 A 23:00
    DIM 07:00 A 22:00
  FIN_HORAIRE

  SI Horaire_Jour = ON ALORS
    Temp_Active = Temp_Confort
  SINON
    Temp_Active = Temp_Nuit
  FIN

  BOUCLE Chauffage_Salon_ONOFF TYPE HYSTERESIS
    ENTREE Temp_Salon
    CONSIGNE Temp_Active
    DIFF 0.5 C
    SORTIE Chauffage_Salon
    ACTION chauffage
    CYCLE 5 s
  FIN_BOUCLE

  SECURITE Surchauffe_Salon
    SI Temp_Salon > 30 C ALORS
      Chauffage_Salon = OFF
      ALARME "Surchauffe salon"
    FIN
  FIN_SECURITE
FIN_ZONE

FIN_PROJET
```

---

## 49. Exemple complet industriel

```ldic
PROJET Usine_Lislet
LANGUE fr-CA
PAYS CA
FUSEAU_HORAIRE America/Montreal
UNITES MT
VERSION 1.0

BATIMENT Usine_Principale
TYPE_BATIMENT industriel

ZONE Atelier_Production
  CAPTEUR Temp_Atelier TYPE temperature UNITE C SOURCE mqtt "atelier/temp"
  CAPTEUR Hum_Atelier TYPE humidite UNITE % SOURCE mqtt "atelier/hum"
  CAPTEUR CO2_Atelier TYPE co2 UNITE ppm SOURCE mqtt "atelier/co2"
  CAPTEUR Pression_Batiment TYPE pression UNITE Pa SOURCE mqtt "atelier/pression"

  SORTIE Vanne_Chauffage TYPE analogique UNITE % MIN 0 % MAX 100 % ETAT_SECURITE 0 %
  SORTIE Ventilation TYPE analogique UNITE % MIN 20 % MAX 100 % ETAT_SECURITE 20 %
  SORTIE Admission_Air TYPE analogique UNITE % MIN 0 % MAX 100 % ETAT_SECURITE 20 %
  SORTIE Alarme_Atelier TYPE relais ETAT_SECURITE OFF

  CONSIGNE Temp_Confort = 21 C MODIFIABLE MIN 16 C MAX 26 C PAS 0.5 C
  CONSIGNE CO2_Max = 1000 ppm MODIFIABLE MIN 600 ppm MAX 1500 ppm PAS 50 ppm
  CONSIGNE Pression_Cible = 5 Pa MODIFIABLE MIN 0 Pa MAX 20 Pa PAS 1 Pa

  PID PID_Chauffage
    ENTREE Temp_Atelier
    CONSIGNE Temp_Confort
    SORTIE Vanne_Chauffage
    KP 2.0 MODIFIABLE MIN 0 MAX 20 PAS 0.1
    KI 0.3 MODIFIABLE MIN 0 MAX 10 PAS 0.1
    KD 0.1 MODIFIABLE MIN 0 MAX 10 PAS 0.1
    SORTIE_MIN 0 %
    SORTIE_MAX 100 %
    CYCLE 5 s
    ACTION chauffage
    ANTI_WINDUP ON
  FIN_PID

  PID PID_Pression
    ENTREE Pression_Batiment
    CONSIGNE Pression_Cible
    SORTIE Admission_Air
    KP 1.5
    KI 0.2
    KD 0.0
    SORTIE_MIN 20 %
    SORTIE_MAX 100 %
    CYCLE 2 s
    ACTION direct
  FIN_PID

  SI CO2_Atelier > CO2_Max ALORS
    Ventilation = 100 %
  SINON
    Ventilation = 40 %
  FIN

  SECURITE Temperature_Critique
    SI Temp_Atelier > 35 C ALORS
      DESACTIVER PID_Chauffage
      Vanne_Chauffage = 0 %
      Alarme_Atelier = ON
      ALARME "Température critique atelier"
    FIN
  FIN_SECURITE
FIN_ZONE

MQTT
  BROKER "192.168.1.10"
  PORT 1883
  BASE_TOPIC "ldic/usine_lislet"
  DECOUVERTE home_assistant
  HEARTBEAT 30 s
FIN_MQTT

FIN_PROJET
```

---

## 50. Fichiers officiels du projet

```text
ldic_validator.py          Validation syntaxique FR/EN
ldic_parser.py             Analyse du langage
ldic_compiler.py           Conversion JSON/YAML/MQTT/BACnet
ldic_runtime_esp32.ino     Runtime Arduino ESP32
ldic_web_editor.html       Éditeur Web local
examples/maison.ldic
examples/usine.ldic
examples/erabliere.ldic
```

---

## 51. Conclusion

LDIC-G v1.0 définit :

- la syntaxe française
- la syntaxe anglaise
- les objets bâtiment
- les capteurs
- les sorties
- les variables
- les consignes
- les PID
- les boucles
- les alarmes
- les sécurités
- les priorités
- MQTT
- Home Assistant
- ESP32 autonome
- validation d’erreurs
- compatibilité IEC, BACnet et JSON

LDIC-G est maintenant défini comme un vrai langage de contrôle bâtiment universel.
