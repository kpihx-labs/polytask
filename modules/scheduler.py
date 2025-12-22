import time
import schedule
import yaml
import os
import pandas as pd
from datetime import datetime, timedelta
from database.db import get_tasks
from modules.notifications import send_telegram

# Chargement de la config
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yaml')
try:
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
except Exception as e:
    print(f"❌ Erreur chargement config scheduler: {e}")
    config = {}

def check_deadlines():
    """Vérifie les échéances (5 min avant ET à l'heure pile)."""
    try:
        df = get_tasks(status='pending')
        if df.empty: return

        now = datetime.now()
        # Marge de prévenance (par défaut 5 minutes) convertie en secondes
        reminder_sec = config.get('reminder_minutes', 5) * 60
        
        for _, row in df.iterrows():
            # On ignore les tâches sans date
            if pd.isna(row['due_date']):
                continue

            # Conversion sécurisée Timestamp -> Datetime
            try:
                due = row['due_date'].to_pydatetime()
            except:
                continue

            # Calcul du temps restant en secondes
            # diff > 0 : C'est dans le futur
            # diff < 0 : C'est déjà passé (en retard)
            diff = (due - now).total_seconds()

            # --- CAS 1 : RAPPEL PRÉVENTIF (ex: 5 min avant) ---
            # On vérifie si on est dans la fenêtre [5min, 6min[
            if reminder_sec <= diff < (reminder_sec + 60):
                minutes = int(reminder_sec / 60)
                send_telegram(
                    f"⏰ **PRÉVENANCE**\n"
                    f"La tâche arrive à échéance dans {minutes} min !\n\n"
                    f"📌 *{row['title']}*\n"
                    f"🕒 Prévu à : {due.strftime('%H:%M')}"
                )

            # --- CAS 2 : C'EST L'HEURE (T=0) ---
            # On vérifie si on est dans la fenêtre [0, 1min[
            elif 0 <= diff < 60:
                prio_icon = "🔴" if row['priority'] == 3 else "🟠"
                send_telegram(
                    f"🚨 **C'EST L'HEURE !**\n"
                    f"L'échéance est atteinte.\n\n"
                    f"{prio_icon} *{row['title']}*\n"
                    f"📂 Groupe : {row['group_name']}"
                )

    except Exception as e:
        print(f"❌ Erreur check_deadlines: {e}")

def weekly_report():
    """Envoie un bilan riche et structuré."""
    try:
        df = get_tasks(status='pending')
        if df.empty:
            send_telegram("📅 **Bilan Hebdo**\nBravo ! Aucune tâche en attente. 🎉")
            return

        now = datetime.now()
        total = len(df)
        
        # Statistiques
        high_prio = len(df[df['priority'] == 3])
        
        # On sépare ce qui est en retard de ce qui est à venir
        # Gestion des NaT pour la comparaison
        df_dates = df[df['due_date'].notna()].copy()
        
        # En retard (Date < Maintenant)
        overdue = df_dates[df_dates['due_date'] < now]
        # À venir cette semaine (Maintenant <= Date <= Maintenant + 7 jours)
        next_week = now + timedelta(days=7)
        upcoming = df_dates[(df_dates['due_date'] >= now) & (df_dates['due_date'] <= next_week)]

        # Construction du Message
        msg = f"📅 **BILAN HEBDOMADAIRE**\n"
        msg += f"Total tâches : **{total}** (Dont {high_prio} urgentes)\n"
        
        # Bloc 1 : Les retards (ALERTE)
        if not overdue.empty:
            msg += f"\n🔥 **EN RETARD ({len(overdue)})**\n"
            for _, row in overdue.sort_values(by='priority', ascending=False).head(5).iterrows():
                d_str = row['due_date'].strftime('%d/%m')
                msg += f"- {row['title']} ({d_str})\n"
            if len(overdue) > 5: msg += f"... et {len(overdue)-5} autres.\n"

        # Bloc 2 : Planning semaine
        if not upcoming.empty:
            msg += f"\n🗓️ **CETTE SEMAINE ({len(upcoming)})**\n"
            for _, row in upcoming.sort_values(by='due_date').head(5).iterrows():
                d_str = row['due_date'].strftime('%A %H:%M')
                msg += f"- {row['title']} ({d_str})\n"

        # Bloc 3 : Rappel des urgences sans date
        nodate_urgent = df[(df['due_date'].isna()) & (df['priority'] == 3)]
        if not nodate_urgent.empty:
            msg += f"\n⚡ **URGENCES SANS DATE**\n"
            for _, row in nodate_urgent.iterrows():
                msg += f"- {row['title']}\n"

        send_telegram(msg)

    except Exception as e:
        print(f"❌ Erreur weekly_report: {e}")

def run_scheduler():
    print("🕒 Scheduler v2 démarré (Rappels +5min & Instantané)...")
    
    # Vérification fréquente pour ne pas rater la minute exacte
    schedule.every(1).minutes.do(check_deadlines)
    
    # Configuration du rapport hebdo dynamique
    day = config.get('weekly_report_day', 'monday').lower()
    at_time = config.get('weekly_report_time', '09:00')
    
    try:
        scheduler_job = getattr(schedule.every(), day)
        scheduler_job.at(at_time).do(weekly_report)
        print(f"✅ Rapport hebdo programmé : {day} à {at_time}")
    except AttributeError:
        print(f"❌ Erreur config jour : {day}")

    # Boucle infinie
    while True:
        schedule.run_pending()
        time.sleep(30) # On dort 30s pour être sûr de capter chaque minute