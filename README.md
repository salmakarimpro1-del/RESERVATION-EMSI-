# 🏫 EMSI Booking - Plateforme de Réservation de Salles

![EMSI Banner](https://img.shields.io/badge/EMSI-Booking-008144?style=for-the-badge)
![Django](https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap)
![Status](https://img.shields.io/badge/Status-Production--Ready-success?style=for-the-badge)

**EMSI Booking** est une solution complète et moderne de gestion et de réservation de salles conçue spécifiquement pour les besoins de l'EMSI. Elle permet aux étudiants et professeurs de réserver des espaces de travail tout en offrant aux administrateurs un contrôle total sur les flux de validation.

---

## ✨ Points Forts & Fonctionnalités

### 👤 Expérience Utilisateur (Frontend)
- **Interface Premium** : Design moderne avec Glassmorphism, animations fluides et thèmes harmonieux.
- **Onboarding Simplifié** : Inscription rapide avec validation d'email unique.
- **Social Login** : Connexion ultra-rapide via **Google OAuth**.
- **Dashboard Intuitif** : Vue d'ensemble des réservations, calendrier interactif (FullCalendar) et notifications en temps réel.
- **Réservations Flexibles** : Choix de la salle, de l'étage et de la durée (jusqu'à **8 heures**).

### 🛡️ Administration & Contrôle
- **Admin Center Centralisé** : Gestion des demandes avec filtrage avancé et actions groupées.
- **Workflow de Modération** : Approuver, Refuser ou Mettre en attente les demandes avec messages personnalisés.
- **Détection de Conflits** : Algorithme intelligent empêchant les doubles réservations sur le même créneau.
- **Paramètres Dynamiques** : Configuration de la durée max, des horaires d'ouverture et de la fenêtre de réservation.

---

## 🚀 Installation Rapide

### 1. Prérequis
- Python 3.10+
- Un environnement virtuel (recommandé)

### 2. Clonage et Dépendances
```bash
git clone https://github.com/salmakarimpro1-del/RESERVATION-EMSI-.git
cd RESERVATION-EMSI-
pip install -r requirements.txt
```

### 3. Configuration
Créez un fichier `.env` à la racine (utilisez `.env.example` comme modèle) :
```env
DJANGO_DEBUG=True
GOOGLE_CLIENT_ID=votre_id
GOOGLE_CLIENT_SECRET=votre_secret
```

### 4. Initialisation
```bash
python manage.py migrate
python manage.py seed_demo  # Pour avoir des données de test
```

### 5. Lancement
Utilisez le lanceur rapide (Windows) :
```bash
run_emsi.bat
```
Ou manuellement :
```bash
python manage.py runserver
```

---

## 🛠️ Stack Technique

- **Backend** : Django 5.2.7, Django REST Framework
- **Frontend** : HTML5, Vanilla JS, Bootstrap 5.3, FullCalendar 6
- **Auth** : Django-allauth (Google OAuth), SimpleJWT
- **Base de données** : SQLite (Dev), PostgreSQL (Prod ready)
- **Design** : Custom CSS, Glassmorphism, Outfit Font

---

## 📂 Structure du Projet

- `core/` : Configuration centrale, paramètres et context processors.
- `bookings/` : Logique métier des réservations et validations.
- `rooms/` : Gestion des salles, équipements et étages.
- `users/` : Modèles utilisateurs personnalisés et adaptateurs sociaux.
- `templates/` : Interfaces utilisateur organisées par modules.
- `static/` : Assets, images et styles CSS.

---

## 👨‍💻 Administration

Accédez au centre d'administration via :
- **Dashboard Admin** : `/admin-center/`
- **Django Admin** : `/admin/`

**Comptes de test :**
- Admin : `admin / admin123`
- Étudiant : `youssef / password123`

---

## 📝 Licence & Auteurs
Développé pour l'**EMSI**. Tous droits réservés.
