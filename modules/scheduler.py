import time
import schedule
import yaml
import os
import pandas as pd
from datetime import datetime, timedelta
from database.db import get_tasks
from modules.notifications import send_telegram

# ==============================================================================
# 1. CHARGEMENT CONFIGURATION
# ==============================================================================
# On récupère le chemin absolu pour éviter les erreurs de "File not found"
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'config.yaml')

try:
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
except Exception as e:
    print(f"⚠️ Warning: Impossible de charger config.yaml ({e}). Valeurs par défaut utilisées.")
    config = {}

# ==============================================================================
# 2. SYSTÈME ANTI-DOUBLON (CACHE)
# ==============================================================================
# Dictionnaire pour se souvenir des alertes déjà envoyées.
# Format : { "ID_TACHE_TYPE": TIMESTAMP_ENVOI }
# Ex: { "14_prevent": 1703254020, "14_now": 1703254320 }
sent_cache = {}

def clean_cache():
    """Nettoie le cache toutes les heures pour éviter qu'il ne grossisse indéfiniment."""
    now = time.time()
    # On supprime les entrées vieilles de plus de 1 heure (3600s)
    keys_to_delete = [k for k, v in sent_cache.items() if now - v > 3600]
    for k in keys_to_delete:
        del sent_cache[k]
    # print(f"🧹 Cache nettoyé. {len(sent_cache)} entrées actives.")

# ==============================================================================
# 3. VÉRIFICATION DES ÉCHÉANCES
# ==============================================================================
def check_deadlines():
    """Vérifie les tâches et envoie des notifs (Prévenance + Instant T)."""
    try:
        df = get_tasks(status='pending')
        if df.empty: return

        now = datetime.now()
        # Récupère le délai de prévenance (défaut 5 min), converti en secondes
        reminder_minutes = config.get('reminder_minutes', 5)
        reminder_sec = reminder_minutes * 60
        
        for _, row in df.iterrows():
            # Ignorer si pas de date ou date invalide
            if pd.isna(row['due_date']): continue
            try:
                due = row['due_date'].to_pydatetime()
            except: continue

            # Différence en secondes (Positif = Futur, Négatif = Passé)
            diff = (due - now).total_seconds()
            tid = row['id']

            # --- ALERTE 1 : PRÉVENANCE (ex: 5 min avant) ---
            # On cherche si on est dans la fenêtre [4min30s ... 6min30s]
            # On prend une fenêtre large (120s) pour être sûr de ne pas rater le coche,
            # car le cache empêchera les doublons de toute façon.
            if (reminder_sec - 60) < diff < (reminder_sec + 60):
                cache_key = f"{tid}_prevent"
                
                # Si on n'a pas déjà envoyé cette alerte :
                if cache_key not in sent_cache:
                    send_telegram(
                        f"⏰ **RAPPEL -{reminder_minutes} min**\n\n"
                        f"📌 *{row['title']}*\n"
                        f"🕒 Prévu à : {due.strftime('%H:%M')}"
                    )
                    # On marque comme envoyé
                    sent_cache[cache_key] = time.time()

            # --- ALERTE 2 : C'EST L'HEURE (T=0) ---
            # Fenêtre de tir : entre -60s et +60s autour de l'heure pile
            elif -60 < diff < 60:
                cache_key = f"{tid}_now"
                
                if cache_key not in sent_cache:
                    prio_icon = "🔴" if row['priority'] == 3 else "🟠"
                    send_telegram(
                        f"🚨 **C'EST L'HEURE !**\n\n"
                        f"{prio_icon} *{row['title']}*\n"
                        f"📂 Groupe : {row['group_name']}"
                    )
                    sent_cache[cache_key] = time.time()

    except Exception as e:
        print(f"❌ Erreur check_deadlines: {e}")

# ==============================================================================
# 4. RAPPORT HEBDOMADAIRE
# ==============================================================================
def weekly_report():
    """Génère et envoie le bilan de la semaine."""
    try:
        df = get_tasks(status='pending')
        if df.empty:
            send_telegram("📅 **Bilan Hebdo**\n\nBravo ! Aucune tâche en attente. 🎉")
            return

        total = len(df)
        high_prio = len(df[df['priority'] == 3])
        
        msg = f"📅 **BILAN HEBDOMADAIRE**\nTotal : **{total}** tâches (Dont {high_prio} urgentes)\n"
        
        # On liste les 5 plus urgentes/vieilles
        top_tasks = df.sort_values(by=['priority', 'due_date'], ascending=[False, True]).head(5)
        
        msg += "\n🔥 **Top Priorités :**\n"
        for _, row in top_tasks.iterrows():
            date_str = ""
            if not pd.isna(row['due_date']):
                date_str = f" ({row['due_date'].strftime('%d/%m')})"
            
            prio = "🔴" if row['priority'] == 3 else "🔵"
            msg += f"{prio} {row['title']}{date_str}\n"
            
        send_telegram(msg)

    except Exception as e:
        print(f"❌ Erreur weekly_report: {e}")

# ==============================================================================
# 5. BOUCLE PRINCIPALE
# ==============================================================================
def run_scheduler():
    print("🕒 Scheduler V3 (Anti-Doublon) démarré...")
    
    # 1. Vérification fréquente (toutes les 10s) pour être précis
    schedule.every(10).seconds.do(check_deadlines)
    
    # 2. Nettoyage du cache toutes les heures
    schedule.every(1).hour.do(clean_cache)
    
    # 3. Programmation Hebdo dynamique
    day = config.get('weekly_report_day', 'monday').lower()
    at_time = config.get('weekly_report_time', '09:00')
    
    try:
        # Magie python pour appeler schedule.every().lundi() dynamiquement
        scheduler_job = getattr(schedule.every(), day)
        scheduler_job.at(at_time).do(weekly_report)
        print(f"✅ Rapport hebdo programmé : {day} à {at_time}")
    except AttributeError:
        print(f"❌ Erreur config jour : '{day}' n'est pas valide.")

    # Boucle infinie
    while True:
        schedule.run_pending()
        time.sleep(5) # Pause courte pour ne pas surcharger le CPU