import psycopg2
import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION SQLALCHEMY (Pour Pandas) ---
def get_engine():
    """Crée un moteur SQLAlchemy pour les lectures Pandas (supprime le Warning)."""
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASS")
    host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    # Chaîne de connexion standard : postgresql+psycopg2://user:pass@host/db
    return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}/{db_name}")

# --- CONFIGURATION PSYCOPG2 (Pour les Écritures/Rapide) ---
def get_connection():
    """Connexion brute pour les INSERT/UPDATE (plus léger)."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS")
    )

def init_db():
    try:
        conn = get_connection()
        cur = conn.cursor()
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        with open(schema_path, 'r') as f:
            cur.execute(f.read())
        conn.commit()
        conn.close()
        print("✅ DB Init OK")
    except Exception as e:
        print(f"❌ DB Init Error: {e}")

def get_tasks(status=None):
    """Lecture via SQLAlchemy pour éviter le Warning."""
    engine = get_engine()
    query = "SELECT * FROM tasks"
    if status:
        query += f" WHERE status = '{status}'"
    
    # Pandas utilise maintenant l'engine SQLAlchemy = Plus de warning !
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    return df

def add_task(title, desc, group, priority, tags, due_date):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tasks (title, description, group_name, priority, tags, due_date, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'pending')
    """, (title, desc, group, priority, tags, due_date))
    conn.commit()
    conn.close()

def mark_done(task_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET status='done', completed_at=NOW() WHERE id=%s", (task_id,))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id=%s", (task_id,))
    conn.commit()
    conn.close()

# Gestion Groupes
def get_groups():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM task_groups ORDER BY name")
    groups = [row[0] for row in cur.fetchall()]
    conn.close()
    return groups

def add_group(name):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO task_groups (name) VALUES (%s)", (name,))
        conn.commit()
        res = True
    except:
        res = False
    finally:
        conn.close()
    return res

def delete_group(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM task_groups WHERE name=%s", (name,))
    conn.commit()
    conn.close()