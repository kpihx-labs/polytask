CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    group_name VARCHAR(50),
    priority INT DEFAULT 2,
    tags TEXT[],
    due_date TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Table pour gérer les groupes dynamiquement
CREATE TABLE IF NOT EXISTS task_groups (
    name VARCHAR(50) PRIMARY KEY
);

-- On insère les groupes par défaut si la table est vide
INSERT INTO task_groups (name) VALUES ('Default'), ('Root'), ('Dev'), ('Perso') ON CONFLICT DO NOTHING;