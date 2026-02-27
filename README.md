# 🚀 PolyTask Pro

**PolyTask** est un gestionnaire de tâches personnel (To-Do List) avancé, conçu pour l'auto-hébergement (Homelab).
Il combine une interface moderne (**Streamlit**), une base de données robuste (**PostgreSQL**), et un système de notifications proactif (**Telegram**).

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-orange)
![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-red)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Fonctionnalités

- **Interface Réactive** : Ajout et suppression de tâches instantanés (Callbacks optimisés).
- **Organisation** : 
  - Gestion par **Groupes** dynamiques (Pro, Perso, DevOps...).
  - Gestion par **Priorités** (Haute 🔴, Moyenne 🟠, Basse 🟢).
- **Planification Avancée** : 
  - Définition d'échéances avec un sélecteur d'heure ergonomique (Heures/Minutes).
- **Vues Intelligentes** : 
  - **Tri automatique** : En retard 🔥 / À venir 📅 / Sans date ♾️.
  - **Mode Liste** ou **Mode Arborescence** par groupe.
- **Notifications & Alertes** :
  - **Telegram** : Rappel préventif (5 min avant) + Alerte immédiate à l'heure pile.
  - **Navigateur** : Notifications Desktop natives pour les tâches urgentes.
  - **Rapport Hebdo** : Résumé automatique envoyé chaque lundi matin.
- **Filtres Puissants** : Recherche textuelle, filtrage par Tags multiples et par Priorité.

---

## 🏗️ Architecture

Le projet est conçu pour tourner sous **Docker** derrière un reverse-proxy (Traefik) avec une isolation réseau.

```text
polytask/
├── config/             # Configuration métier (YAML : Groupes, Priorités, Planning)
├── database/           # Gestion PostgreSQL (SQLAlchemy + Psycopg2)
├── modules/            # Logique Backend (Scheduler, Notifications Telegram)
├── app.py              # Frontend (Streamlit)
├── .env                # Secrets (Non versionné)
└── docker-compose.yml  # Orchestration
```

## 🚀 Installation & Démarrage

### 1. Pré-requis
* Docker & Docker Compose
* Un bot Telegram (Token + Chat ID)

### 2. Cloner le dépôt

```bash
git clone [https://github.com/KpihX/PolyTask.git](https://github.com/KpihX/PolyTask.git)
cd PolyTask
```

### 3. Configuration

Copiez le fichier d'exemple et remplissez vos secrets :

```bash
cp .env.example .env
nano .env
```

Remplissez les informations de base de données et les tokens Telegram.
Vous pouvez aussi ajuster les préférences métier (groupes par défaut, jour du rapport hebdo) dans `config/config.yaml`.

### 4. Lancement

```bash
docker compose up -d --build
```

### 5. Accès
L'application est accessible via deux URLs (grâce à Traefik) :
- **Privé (Local) :** `https://task.homelab`
- **Souverain (Certifié) :** `https://task.kpihx-labs.com` (Cadenas vert via Let's Encrypt / DNS-01)

---

## 🛠️ Stack Technique

* **Langage** : Python 3.11
* **Frontend** : Streamlit (avec injection JS pour notifications)
* **Database** : PostgreSQL (Driver: psycopg2-binary, ORM: SQLAlchemy pour Pandas)
* **Scheduling** : Library schedule (Thread daemon en arrière-plan)
* **Infrastructure** : Docker Compose, Réseau Bridge, Support Proxy HTTP/HTTPS.

## 🤝 Contribution

Les contributions sont les bienvenues !

1.  Forkez le projet.
2.  Créez votre branche de fonctionnalité (`git checkout -b feature/AmazingFeature`).
3.  Commitez vos changements (`git commit -m 'Add some AmazingFeature'`).
4.  Pushez sur la branche (`git push origin feature/AmazingFeature`).
5.  Ouvrez une Pull Request.

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.