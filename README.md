# 🍁 Érablière — Logiciel de gestion

Logiciel complet de gestion pour érablière : clients, factures, stock, production, comptabilité.  
Portable — fonctionne directement depuis une clé USB, **sans installation**.

---

## Installation sur clé USB — 3 étapes

### Étape 1 — Télécharger le logiciel

👉 Cliquez sur le bouton vert **`< > Code`** en haut de cette page, puis **`Download ZIP`**

### Étape 2 — Extraire sur la clé USB

1. Branchez votre clé USB
2. Clic droit sur le fichier ZIP → **Extraire ici** (ou **Extract Here**)
3. Déplacez ou extrayez directement dans votre clé USB

Vous devriez voir ces fichiers dans le dossier :

```
📁 votre-clé-USB/
├── 🖥️  LANCER.bat          ← Windows
├── 🐧  LANCER.sh           ← Linux
├── 🖼️  LANCER.desktop      ← Linux (icône cliquable)
├── 📁  erabliere-app/
└── 📁  data/
```

### Étape 3 — Lancer le logiciel

| Système | Action |
|---------|--------|
| **Windows** | Double-cliquer sur `LANCER.bat` |
| **Linux** | Double-cliquer sur `LANCER.sh` → *Exécuter dans un terminal* |
| **Linux** (alternative) | Double-cliquer sur `LANCER.desktop` → *Autoriser le lancement* |

> **Première fois uniquement :** le logiciel installe automatiquement ses composants (~30 secondes, connexion Internet requise). Les fois suivantes, il démarre immédiatement.

---

## Utilisation

Le logiciel ouvre automatiquement votre navigateur à l'adresse **http://localhost:5000**

Pour arrêter : fermez la fenêtre noire / terminal.

---

## Fonctionnalités

| Module | Description |
|--------|-------------|
| 📊 **Tableau de bord** | Ventes du jour, du mois, de l'année, alertes stock |
| 🛍️ **Produits** | Gestion du catalogue avec suivi du stock en temps réel |
| 👥 **Clients** | Base de données clients, historique d'achats |
| ⭐ **Abonnements** | Plans d'abonnement avec rabais automatiques |
| 🚚 **Fournisseurs** | Répertoire des fournisseurs |
| 🧾 **Factures** | Création, édition, PDF, export CSV, suivi des paiements |
| 💧 **Production** | Suivi des coulées, saisons, ratio eau/sirop |
| 📒 **Comptabilité** | Saisie des dépenses, export CSV |
| 📈 **Historique des ventes** | Analyses par période |
| 🏦 **Rapport de taxes** | TPS/TVQ par mois, trimestre ou année |
| ⚙️ **Paramètres** | Informations de l'entreprise, logo |

---

## Configuration requise

| | Minimum |
|-|---------|
| **Python** | Version 3.8 ou plus récente |
| **Navigateur** | Chrome, Firefox, Edge, Safari |
| **Espace disque** | ~100 Mo sur la clé USB |
| **Connexion** | Requise uniquement lors de la première installation |

Python est gratuit : [python.org/downloads](https://www.python.org/downloads/)

---

## Données

Vos données sont stockées dans le dossier **`data/`** sur votre clé USB.  
Pour faire une sauvegarde, copiez simplement ce dossier.

---

*Développé pour la gestion d'une érablière québécoise.*
