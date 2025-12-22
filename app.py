import streamlit as st
import yaml
import threading
import pandas as pd
from datetime import datetime, time as dt_time
import time
import streamlit.components.v1 as components
import uuid

# Imports locaux (assure-toi que les fichiers existent dans /database et /modules)
from database.db import init_db, add_task, get_tasks, mark_done, delete_task, get_groups, add_group, delete_group
from modules.scheduler import run_scheduler

# ==============================================================================
# 1. SETUP & INITIALISATION
# ==============================================================================

st.set_page_config(page_title="PolyTask", page_icon="✅", layout="wide")

# Chargement de la configuration
try:
    with open('config/config.yaml') as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    st.error("❌ Fichier config/config.yaml introuvable.")
    st.stop()

# Initialisation de la Base de données et du Scheduler (une seule fois)
if 'init_done' not in st.session_state:
    init_db()
    # Lancement du thread en arrière-plan pour les tâches planifiées (Telegram)
    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()
    st.session_state.init_done = True

# Récupération des données dynamiques
available_groups = get_groups()
priorities_map = {v: k for k, v in config['priorities'].items()} # Ex: "Haute" -> 3

# ==============================================================================
# 2. FONCTIONS DE CALLBACK (GESTION DU FORMULAIRE)
# ==============================================================================
# Ces fonctions sont exécutées AVANT le rechargement de la page pour éviter
# les erreurs de modification du session_state.

def clear_form_callback():
    """Vide tous les champs du formulaire d'ajout."""
    st.session_state["new_title"] = ""
    st.session_state["new_desc"] = ""
    st.session_state["new_tags"] = ""
    st.session_state["new_has_due"] = False
    # On peut aussi reset les index des selectbox si nécessaire, mais souvent inutile.

def add_task_callback():
    """Récupère les données, ajoute la tâche et nettoie le formulaire."""
    # 1. Récupération
    title = st.session_state.get("new_title", "").strip()
    
    if not title:
        st.error("⚠️ Le titre est obligatoire.")
        return # On arrête si pas de titre

    desc = st.session_state.get("new_desc", "")
    group = st.session_state.get("new_grp_select")
    prio_key = st.session_state.get("new_prio")
    prio_val = priorities_map.get(prio_key, 2)
    tags_str = st.session_state.get("new_tags", "")
    tags = [t.strip() for t in tags_str.split(',') if t]

    # 2. Gestion de la date (si activée)
    due_val = None
    if st.session_state.get("new_has_due", False):
        try:
            d = st.session_state.get("new_date")
            # Les heures/minutes sont des chaînes "00", "01"... on convertit en int
            h = int(st.session_state.get("new_h", 12))
            m = int(st.session_state.get("new_m", 0))
            due_val = datetime.combine(d, dt_time(h, m))
        except Exception as e:
            print(f"Erreur date: {e}")

    # 3. Ajout en BDD
    add_task(title, desc, group, prio_val, tags, due_val)
    
    # 4. Feedback et Nettoyage
    st.toast(f"Tâche '{title}' ajoutée !", icon="✅")
    clear_form_callback()

# ==============================================================================
# 3. SIDEBAR (ACTIONS)
# ==============================================================================
with st.sidebar:
    st.title("⚡ Actions")
    
    # Bouton pour demander la permission de notification au navigateur
    if st.button("🔔 Autoriser Notifications"):
        js_perm = """
        <script>
            Notification.requestPermission().then(function(permission) {
                if(permission === 'granted') { 
                    new Notification('PolyTask', { body: 'Notifications actives !' }); 
                }
            });
        </script>
        """
        components.html(js_perm, height=0)

    tab_task, tab_group = st.tabs(["Nouvelle Tâche", "Gérer Groupes"])
    
    # --- ONGLET 1 : CRÉATION DE TÂCHE ---
    with tab_task:
        st.header("➕ Nouvelle Tâche")
        
        # Champs liés au session_state via 'key'
        st.text_input("Titre", key="new_title")
        st.text_area("Description", key="new_desc")
        
        c1, c2 = st.columns(2)
        with c1:
            st.selectbox("Groupe", available_groups if available_groups else ["Défaut"], key="new_grp_select")
        with c2:
            st.select_slider("Priorité", options=list(priorities_map.keys()), value="Moyenne", key="new_prio")
        
        # Toggle pour la date
        st.toggle("Ajouter une échéance ?", key="new_has_due")
        
        # Affichage conditionnel de la date (Réactif)
        if st.session_state.get("new_has_due", False):
            st.write("📅 **Date & Heure**")
            st.date_input("Jour", label_visibility="collapsed", key="new_date")
            
            ch, cm = st.columns(2)
            with ch:
                hours = [f"{i:02d}" for i in range(24)]
                st.selectbox("Heure", hours, index=12, label_visibility="collapsed", key="new_h")
            with cm:
                minutes = [f"{i:02d}" for i in range(60)]
                st.selectbox("Min", minutes, index=0, label_visibility="collapsed", key="new_m")
            
            # Petit aperçu visuel
            try:
                # On recrée l'objet pour l'affichage temps réel
                cur_d = st.session_state.new_date
                cur_h = st.session_state.new_h
                cur_m = st.session_state.new_m
                st.caption(f"Pour le : {cur_d.strftime('%d/%m')} à {cur_h}h{cur_m}")
            except: pass

        st.text_input("Tags (sep. virgule)", key="new_tags")
        
        # Boutons d'action utilisant les Callbacks
        col_btn1, col_btn2 = st.columns(2)
        col_btn1.button("Ajouter", type="primary", on_click=add_task_callback)
        col_btn2.button("Vider", on_click=clear_form_callback)

    # --- ONGLET 2 : GESTION DES GROUPES ---
    with tab_group:
        new_grp = st.text_input("Nouveau Groupe")
        if st.button("Créer Groupe"):
            if new_grp:
                if add_group(new_grp):
                    st.success(f"Groupe '{new_grp}' créé")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Ce groupe existe déjà.")
        
        st.divider()
        grp_to_del = st.selectbox("Supprimer un groupe", available_groups, key="del_grp")
        if st.button("Supprimer", type="primary"):
            delete_group(grp_to_del)
            st.rerun()

# ==============================================================================
# 4. PAGE PRINCIPALE (AFFICHAGE)
# ==============================================================================
st.title(f"🚀 {config['app_name']}")

# --- FILTRES ---
main_container = st.container()
with main_container:
    with st.expander("🔍 Filtres & Recherche", expanded=True):
        col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 2])
        search_txt = col_f1.text_input("Mot-clé")
        
        # Récupération de tous les tags existants pour le filtre
        df_all = get_tasks()
        all_tags = set()
        if not df_all.empty and 'tags' in df_all.columns:
            for tags_list in df_all['tags'].dropna():
                if isinstance(tags_list, list): all_tags.update(tags_list)
        
        filter_tags = col_f2.multiselect("Tags", sorted(list(all_tags)))
        filter_prio = col_f3.multiselect("Priorité", list(priorities_map.keys()))
        view_mode = col_f4.radio("Statut", ["En cours", "Terminées"], horizontal=True)
        view_type = st.radio("Vue", ["Liste", "Par Groupe"], horizontal=True)

    # --- RÉCUPÉRATION DES DONNÉES ---
    status_db = 'pending' if view_mode == "En cours" else 'done'
    df = get_tasks(status_db)

    # Application des filtres
    if not df.empty:
        if search_txt:
            df = df[df['title'].str.contains(search_txt, case=False, na=False) | 
                    df['description'].str.contains(search_txt, case=False, na=False)]

        if filter_tags:
            # Vérifie si l'intersection des tags n'est pas vide
            df = df[df['tags'].apply(lambda x: bool(set(x) & set(filter_tags)) if isinstance(x, list) else False)]

        if filter_prio:
            prio_ints = [priorities_map[p] for p in filter_prio]
            df = df[df['priority'].isin(prio_ints)]

    # --- GESTION NOTIFICATIONS NAVIGATEUR ---
    now = datetime.now()
    if not df.empty:
        for _, row in df.iterrows():
            if not pd.isna(row['due_date']):
                d_obj = row['due_date'].to_pydatetime() if hasattr(row['due_date'], 'to_pydatetime') else row['due_date']
                diff = (d_obj - now).total_seconds()
                
                # Si l'échéance est dans la minute à venir
                if 0 < diff < 60:
                    unique_id = uuid.uuid4()
                    js = f"""
                    <script>
                        (function() {{
                            if (Notification.permission === "granted") {{
                                new Notification("⏰ Rappel PolyTask", {{ 
                                    body: "{row['title']} arrive à échéance !",
                                    icon: "https://cdn-icons-png.flaticon.com/512/2693/2693507.png"
                                }});
                            }}
                        }})();
                    </script>
                    <div style="display:none">{unique_id}</div>
                    """
                    components.html(js, height=0)

    # --- FONCTION D'AFFICHAGE D'UNE CARTE ---
    def display_task_card(row, state="normal"):
        """
        state: 'overdue' (retard), 'upcoming' (futur), 'nodate' (sans date), 'done' (terminé)
        """
        prio_colors = {3: "red", 2: "orange", 1: "green"}
        color = prio_colors.get(row['priority'], "grey")
        
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([0.5, 4, 2, 0.5])
            
            # Bouton Valider
            if row['status'] == 'pending':
                if c1.button("✅", key=f"ok_{row['id']}"):
                    mark_done(row['id'])
                    st.rerun()
            else:
                c1.write("🏁")

            # Informations
            with c2:
                prefix = "🔥 " if state == 'overdue' else "⏳ " if state == 'upcoming' else ""
                st.markdown(f":{color}[●] **{prefix}{row['title']}**")
                
                if row['description']: 
                    st.caption(row['description'])
                
                tags = row['tags'] if isinstance(row['tags'], list) else []
                if tags: 
                    st.write(" ".join([f"`#{t}`" for t in tags]))

            # Métadonnées (Date, Groupe)
            with c3:
                st.caption(f"📂 {row['group_name']}")
                
                if not pd.isna(row['due_date']):
                    try:
                        d_obj = row['due_date'].to_pydatetime() if hasattr(row['due_date'], 'to_pydatetime') else row['due_date']
                        date_str = d_obj.strftime('%d/%m %H:%M')
                        
                        if state == 'overdue':
                            st.markdown(f":red[**🚨 {date_str}**]")
                        elif state == 'upcoming':
                            st.markdown(f":blue[📅 {date_str}]")
                        else:
                            st.caption(f"📅 {date_str}")
                    except: pass
                elif state == 'nodate':
                    st.caption("♾️ Pas de date")

            # Bouton Supprimer
            if c4.button("🗑️", key=f"del_{row['id']}"):
                delete_task(row['id'])
                st.rerun()

    # --- RENDU FINAL ---
    if df.empty:
        st.info("Aucune tâche ne correspond aux critères.")
    else:
        # VUE LISTE (3 SECTIONS)
        if view_type == "Liste":
            if view_mode == "En cours":
                # Tri et segmentation
                # A. En Retard
                df_overdue = df[(df['due_date'].notna()) & (df['due_date'] < now)].sort_values(by=['priority'], ascending=False)
                # B. À Venir
                df_upcoming = df[(df['due_date'].notna()) & (df['due_date'] >= now)].sort_values(by=['due_date'], ascending=True)
                # C. Sans Date
                df_nodate = df[df['due_date'].isna()].sort_values(by=['priority'], ascending=False)

                if not df_overdue.empty:
                    st.error(f"🔥 **EN RETARD ({len(df_overdue)})**")
                    for _, row in df_overdue.iterrows(): display_task_card(row, 'overdue')
                    st.divider()

                if not df_upcoming.empty:
                    st.info(f"📅 **À VENIR ({len(df_upcoming)})**")
                    for _, row in df_upcoming.iterrows(): display_task_card(row, 'upcoming')
                    st.divider()

                if not df_nodate.empty:
                    st.write(f"♾️ **SANS ÉCHÉANCE ({len(df_nodate)})**")
                    for _, row in df_nodate.iterrows(): display_task_card(row, 'nodate')
            
            else:
                # Vue Terminées
                st.success(f"🏁 **TERMINÉES ({len(df)})**")
                # Tri par date de complétion inverse (non stockée ici mais on prend id desc par défaut)
                for _, row in df.sort_values(by='id', ascending=False).iterrows(): 
                    display_task_card(row, 'done')
        
        # VUE PAR GROUPE
        else:
            for grp in sorted(df['group_name'].unique()):
                df_grp = df[df['group_name'] == grp].sort_values(by=['priority'], ascending=False)
                
                with st.expander(f"📂 {grp} ({len(df_grp)})", expanded=True):
                    for _, row in df_grp.iterrows():
                        state = 'done'
                        if view_mode == "En cours":
                            if pd.isna(row['due_date']): 
                                state = 'nodate'
                            else:
                                d_obj = row['due_date'].to_pydatetime() if hasattr(row['due_date'], 'to_pydatetime') else row['due_date']
                                state = 'overdue' if d_obj < now else 'upcoming'
                        
                        display_task_card(row, state)

# Rafraîchissement automatique pour mettre à jour les statuts (Retard...)
time.sleep(60)
st.rerun()