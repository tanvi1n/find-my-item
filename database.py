import sqlite3
import os
from flask import g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
DATABASE_PATH = os.path.join(INSTANCE_DIR, 'campus.db')
ADMIN_EMAIL = 'admin@bvrithyderabad.edu.in'
ADMIN_USERNAME = 'admin'
ADMIN_NAME = 'Find-My-Item Administrator'
ADMIN_PASSWORD_HASH = 'scrypt:32768:8:1$oQxgRgAIfD5kVil3$c03fe0bd369f8154ad8158b1162b464ba43dec6d4d685c7958947eea4032ac9c3dc2d9570eccaf93ed6dc1ebf5071872abb0ad2765c8d07bfe3b1c818c6a17a7'

def ensure_instance_dir():
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    uploads_dir = os.path.join(BASE_DIR, 'static', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)

def get_db():
    ensure_instance_dir()
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def get_direct_connection():
    """Get standalone connection for scripts like seed.py"""
    ensure_instance_dir()
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    ensure_instance_dir()
    conn = get_direct_connection()
    schema_path = os.path.join(BASE_DIR, 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def ensure_migrations():
    """Apply lightweight schema upgrades for existing SQLite databases."""
    ensure_instance_dir()
    if not os.path.exists(DATABASE_PATH):
        return
    conn = get_direct_connection()
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if 'verifications' not in tables:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                lost_item_id INTEGER NOT NULL,
                found_item_id INTEGER NOT NULL,
                private_detail_hash TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Confirmed', 'Rejected')),
                requested_by INTEGER NOT NULL,
                verified_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
                FOREIGN KEY (lost_item_id) REFERENCES items(id) ON DELETE CASCADE,
                FOREIGN KEY (found_item_id) REFERENCES items(id) ON DELETE CASCADE,
                FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_verifications_match ON verifications(match_id);
        """)
        conn.commit()

    match_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(matches)").fetchall()
    }
    for column, definition in (
        ('image_similarity_score', 'INTEGER'),
        ('image_validation_status', "TEXT NOT NULL DEFAULT 'Unavailable'"),
        ('image_validation_reason', 'TEXT'),
        ('image_validation_evidence', 'TEXT'),
        ('image_validated_at', 'TIMESTAMP'),
    ):
        if column not in match_columns:
            conn.execute(f"ALTER TABLE matches ADD COLUMN {column} {definition}")

    item_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(items)").fetchall()
    }
    if 'resolution_path' not in item_columns:
        conn.execute(
            "ALTER TABLE items ADD COLUMN resolution_path TEXT CHECK (resolution_path IN ('SELF_RECOVERY', 'FOUND_BY_OTHER'))"
        )

    # A match row is valid only when it links an actual Lost report to an
    # actual Found report.  Keep this invariant in SQLite as well as Flask.
    conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS validate_match_types_before_insert
        BEFORE INSERT ON matches
        FOR EACH ROW
        WHEN (SELECT type FROM items WHERE id = NEW.lost_item_id) != 'Lost'
          OR (SELECT type FROM items WHERE id = NEW.found_item_id) != 'Found'
        BEGIN
            SELECT RAISE(ABORT, 'matches must pair Lost reports with Found reports');
        END;

        CREATE TRIGGER IF NOT EXISTS validate_match_types_before_update
        BEFORE UPDATE OF lost_item_id, found_item_id ON matches
        FOR EACH ROW
        WHEN (SELECT type FROM items WHERE id = NEW.lost_item_id) != 'Lost'
          OR (SELECT type FROM items WHERE id = NEW.found_item_id) != 'Found'
        BEGIN
            SELECT RAISE(ABORT, 'matches must pair Lost reports with Found reports');
        END;
    """)

    # Keep one private administrator identity while preserving all reports.
    conn.execute("UPDATE users SET role = 'student' WHERE role = 'admin' AND LOWER(email) != LOWER(?)", (ADMIN_EMAIL,))
    admin = conn.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (ADMIN_EMAIL,)).fetchone()
    if admin:
        conn.execute(
            """UPDATE users
               SET username = ?, password_hash = ?, role = 'admin', name = ?
               WHERE id = ?""",
            (ADMIN_USERNAME, ADMIN_PASSWORD_HASH, ADMIN_NAME, admin['id'])
        )
    else:
        existing_username = conn.execute("SELECT id FROM users WHERE username = ?", (ADMIN_USERNAME,)).fetchone()
        if existing_username:
            conn.execute(
                """UPDATE users
                   SET password_hash = ?, role = 'admin', name = ?, email = ?
                   WHERE id = ?""",
                (ADMIN_PASSWORD_HASH, ADMIN_NAME, ADMIN_EMAIL, existing_username['id'])
            )
        else:
            conn.execute(
                """INSERT INTO users (username, password_hash, role, name, email)
                   VALUES (?, ?, 'admin', ?, ?)""",
                (ADMIN_USERNAME, ADMIN_PASSWORD_HASH, ADMIN_NAME, ADMIN_EMAIL)
            )
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized at:", DATABASE_PATH)
