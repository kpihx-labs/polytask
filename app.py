import streamlit as st
import yaml
import threading
import pandas as pd
from datetime import datetime, time as dt_time
import time
import streamlit.components.v1 as components
import uuid

# Imports locaux
from database.db import init_db, add_task, get_tasks, mark_done, delete_task, get_groups, add_group, delete_group
from modules.scheduler import run_scheduler

# ==============================================================================
# 1. SETUP & INITIALISATION
# ==============================================================================

st.set_page_config(page_title="PolyTask", page_icon="✅", layout="wide")

# Chargement Config
try:
    with open('config/config.yaml') as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    st.error("❌ Fichier config/config.yaml introuvable.")
    st.stop()

# Lancement BDD et Scheduler (Background)
if 'init_done' not in st.session_state:
    init_db()
    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()
    st.session_state.init_done = True

# --- GESTION DU "FORM ID" (Anti-Fantôme) ---
if 'form_id' not in st.session_state:
    st.session_state.form_id = 0

def reset_form():
    """Incrémente l'ID, forçant Streamlit à générer de nouveaux widgets vides."""
    st.session_state.form_id += 1

available_groups = get_groups()
priorities_map = {v: k for k, v in config['priorities'].items()}

# ==============================================================================
# 2. CALLBACK D'AJOUT (Logique Métier)
# ==============================================================================
def add_task_callback():
    """Récupère les données des widgets actuels et ajoute la tâche."""
    fid = st.session_state.form_id
    
    # Récupération via les clés dynamiques
    title = st.session_state.get(f"title_{fid}", "").strip()
    desc = st.session_state.get(f"desc_{fid}", "")
    group = st.session_state.get(f"grp_{fid}")
    prio_key = st.session_state.get(f"prio_{fid}")
    prio_val = priorities_map.get(prio_key, 2)
    
    tags_str = st.session_state.get(f"tags_{fid}", "")
    tags = [t.strip() for t in tags_str.split(',') if t]

    # Gestion Date
    due_val = None
    if st.session_state.get(f"has_due_{fid}", False):
        try:
            d = st.session_state.get(f"date_{fid}")
            h = int(st.session_state.get(f"h_{fid}", 12))
            m = int(st.session_state.get(f"m_{fid}", 0))
            due_val = datetime.combine(d, dt_time(h, m))
        except Exception as e:
            print(f"Erreur date: {e}")

    # Validation et Ajout
    if title:
        add_task(title, desc, group, prio_val, tags, due_val)
        st.toast(f"Tâche '{title}' ajoutée !", icon="✅")
        # CRUCIAL : On change l'ID pour le prochain affichage -> Reset visuel
        reset_form()
    else:
        st.error("⚠️ Le titre est obligatoire.")

# ==============================================================================
# 3. SIDEBAR (ACTIONS)
# ==============================================================================
with st.sidebar:
    st.title("⚡ Actions")
    
    # Permission Notifications Navigateur
    if st.button("🔔 Autoriser Notifications"):
        components.html("""<script>Notification.requestPermission()</script>""", height=0)

    tab_task, tab_group = st.tabs(["Nouvelle Tâche", "Gérer Groupes"])
    
    # --- FORMULAIRE AVEC CLÉS DYNAMIQUES ---
    with tab_task:
        st.header("➕ Nouvelle Tâche")
        
        # On récupère l'ID actuel pour construire les clés
        fid = st.session_state.form_id
        
        st.text_input("Titre", key=f"title_{fid}")
        st.text_area("Description", key=f"desc_{fid}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.selectbox("Groupe", available_groups or ["Défaut"], key=f"grp_{fid}")
        with c2:
            st.select_slider("Priorité", options=list(priorities_map.keys()), value="Moyenne", key=f"prio_{fid}")
        
        # Toggle Date
        has_due = st.toggle("Échéance ?", key=f"has_due_{fid}")
        
        if has_due:
            st.write("📅 **Date & Heure**")
            st.date_input("Jour", label_visibility="collapsed", key=f"date_{fid}")
            
            ch, cm = st.columns(2)
            with ch: 
                hours = [f"{i:02d}" for i in range(24)]
                st.selectbox("H", hours, index=12, label_visibility="collapsed", key=f"h_{fid}")
            with cm: 
                mins = [f"{i:02d}" for i in range(60)]
                st.selectbox("M", mins, index=0, label_visibility="collapsed", key=f"m_{fid}")

        st.text_input("Tags (sep. virgule)", key=f"tags_{fid}")
        
        # Boutons d'action
        col_b1, col_b2 = st.columns(2)
        
        # Le bouton appelle le callback AVANT le rerun
        col_b1.button("Ajouter", type="primary", on_click=add_task_callback)
        
        # Le bouton Vider appelle juste le reset d'ID
        col_b2.button("Vider", on_click=reset_form)

    # --- GESTION GROUPES ---
    with tab_group:
        new_grp = st.text_input("Nouveau Groupe")
        if st.button("Créer Groupe"):
            if new_grp:
                if add_group(new_grp):
                    st.success(f"Groupe '{new_grp}' créé")
                    time.sleep(0.5)
                    st.rerun()
                else: st.error("Existe déjà")
        
        st.divider()
        g_del = st.selectbox("Supprimer", available_groups, key="g_del")
        if st.button("Confirmer Suppression", type="primary"):
            delete_group(g_del)
            st.rerun()

# ==============================================================================
# 4. PAGE PRINCIPALE
# ==============================================================================
st.title(f"🚀 {config['app_name']}")

# Fonction d'affichage d'une carte (Robuste aux erreurs de données)
def display_task_card(row, state="normal"):
    prio_colors = {3: "red", 2: "orange", 1: "green"}
    color = prio_colors.get(row['priority'], "grey")
    
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([0.5, 4, 2, 0.5])
        
        # Valider
        if row['status'] == 'pending':
            if c1.button("✅", key=f"ok_{row['id']}"):
                mark_done(row['id'])
                st.rerun()
        else:
            c1.write("🏁")

        # Infos
        with c2:
            prefix = "🔥 " if state == 'overdue' else "⏳ " if state == 'upcoming' else ""
            st.markdown(f":{color}[●] **{prefix}{row['title']}**")
            if row['description']: st.caption(row['description'])
            
            # Affichage Tags (Sécurité type list)
            tags = row['tags'] if isinstance(row['tags'], list) else []
            if tags: st.write(" ".join([f"`#{t}`" for t in tags]))

        # Métadonnées
        with c3:
            st.caption(f"📂 {row['group_name']}")
            # Gestion Date (Sécurité NaT)
            if not pd.isna(row['due_date']):
                try:
                    d_obj = row['due_date'].to_pydatetime() if hasattr(row['due_date'], 'to_pydatetime') else row['due_date']
                    d_str = d_obj.strftime('%d/%m %H:%M')
                    if state == 'overdue': st.markdown(f":red[**🚨 {d_str}**]")
                    elif state == 'upcoming': st.markdown(f":blue[📅 {d_str}]")
                    else: st.caption(f"📅 {d_str}")
                except: pass
            elif state == 'nodate':
                st.caption("♾️ Pas de date")

        # Supprimer
        if c4.button("🗑️", key=f"del_{row['id']}"):
            delete_task(row['id'])
            st.rerun()

# --- FILTRES ---
main_container = st.container()
with main_container:
    with st.expander("🔍 Filtres", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        search = c1.text_input("Recherche")
        
        # Récupération tags uniques
        df_raw = get_tasks()
        all_tags = set()
        if not df_raw.empty and 'tags' in df_raw.columns:
            for t in df_raw['tags'].dropna():
                if isinstance(t, list): all_tags.update(t)
        
        tags_sel = c2.multiselect("Tags", sorted(list(all_tags)))
        prio_sel = c3.multiselect("Priorité", list(priorities_map.keys()))
        mode = c4.radio("Vue", ["En cours", "Terminées"], horizontal=True)
        view_type = st.radio("Style", ["Liste", "Par Groupe"], horizontal=True)

    # Récupération Données
    status_db = 'pending' if mode == "En cours" else 'done'
    df = get_tasks(status_db)

    # Filtrage
    if not df.empty:
        if search:
            df = df[df['title'].str.contains(search, case=False, na=False) | 
                    df['description'].str.contains(search, case=False, na=False)]
        if tags_sel:
            df = df[df['tags'].apply(lambda x: bool(set(x) & set(tags_sel)) if isinstance(x, list) else False)]
        if prio_sel:
            p_ints = [priorities_map[p] for p in prio_sel]
            df = df[df['priority'].isin(p_ints)]

    # Notifications JS (Injecté uniquement si besoin)
    now = datetime.now()
    if not df.empty:
        for _, row in df.iterrows():
            if not pd.isna(row['due_date']):
                try:
                    d_obj = row['due_date'].to_pydatetime() if hasattr(row['due_date'], 'to_pydatetime') else row['due_date']
                    diff = (d_obj - now).total_seconds()
                    # Si échéance dans la minute
                    if 0 < diff < 60:
                        uid = uuid.uuid4()
                        js = f"""<script>(function(){{if(Notification.permission==="granted"){{new Notification("⏰ Rappel",{{body:"{row['title']} arrive à échéance !",icon:"https://cdn-icons-png.flaticon.com/512/2693/2693507.png"}});}}}})();</script><div style="display:none">{uid}</div>"""
                        components.html(js, height=0)
                except: pass

    # --- RENDU 3 SECTIONS ---
    if df.empty:
        st.info("Aucune tâche ne correspond aux critères.")
    else:
        if view_type == "Liste":
            if mode == "En cours":
                # Tri des DataFrames
                over = df[(df['due_date'].notna()) & (df['due_date'] < now)].sort_values(by='priority', ascending=False)
                upco = df[(df['due_date'].notna()) & (df['due_date'] >= now)].sort_values(by='due_date')
                noda = df[df['due_date'].isna()].sort_values(by='priority', ascending=False)

                if not over.empty:
                    st.error(f"🔥 **EN RETARD ({len(over)})**")
                    for _, r in over.iterrows(): display_task_card(r, 'overdue')
                    st.divider()

                if not upco.empty:
                    st.info(f"📅 **À VENIR ({len(upco)})**")
                    for _, r in upco.iterrows(): display_task_card(r, 'upcoming')
                    st.divider()

                if not noda.empty:
                    st.write(f"♾️ **SANS ÉCHÉANCE ({len(noda)})**")
                    for _, r in noda.iterrows(): display_task_card(r, 'nodate')
            else:
                st.success("🏁 **TERMINÉES**")
                for _, r in df.sort_values(by='id', ascending=False).iterrows(): display_task_card(r, 'done')
        
        else: # Par Groupe
            groups = sorted(df['group_name'].unique())
            for grp in groups:
                sub_df = df[df['group_name'] == grp].sort_values(by=['priority', 'due_date'], ascending=[False, True])
                with st.expander(f"📂 {grp} ({len(sub_df)})", expanded=True):
                    for _, r in sub_df.iterrows():
                        state = 'done'
                        if mode == "En cours":
                            if pd.isna(r['due_date']): state = 'nodate'
                            else:
                                d_obj = r['due_date'].to_pydatetime() if hasattr(r['due_date'], 'to_pydatetime') else r['due_date']
                                state = 'overdue' if d_obj < now else 'upcoming'
                        display_task_card(r, state)

# Refresh Auto
time.sleep(60)
st.rerun()