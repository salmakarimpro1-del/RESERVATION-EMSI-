@echo off
TITLE EMSI Reservation Platform Launcher
echo ==========================================
echo    LANCEMENT DE EMSI RESERVATION...
echo ==========================================

:: 1. Activation de l'environnement virtuel
if exist venv\Scripts\activate (
    echo [OK] Activation de l'environnement virtuel...
    call venv\Scripts\activate
) else (
    echo [ERREUR] Dossier venv introuvable. Assurez-vous d'avoir cree un venv.
    pause
    exit /b
)

:: 2. Verification des migrations
echo [OK] Verification de la base de donnees...
python manage.py migrate

:: 3. Ouverture du navigateur (optionnel)
echo [OK] Ouverture du navigateur...
start http://127.0.0.1:8000

:: 4. Lancement du serveur
echo [OK] Lancement du serveur Django sur le port 8000...
echo Appuyez sur Ctrl+C pour arreter le serveur.
python manage.py runserver 0.0.0.0:8000

pause
