-- Find-My-Item Database Schema (SQLite)

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'admin')),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL CHECK (type IN ('Lost', 'Found')),
    category TEXT NOT NULL,
    location TEXT NOT NULL,
    date TEXT NOT NULL,
    contact TEXT NOT NULL,
    image_path TEXT,
    status TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open', 'Potential Match', 'Verification', 'Resolved')),
    resolution_path TEXT CHECK (resolution_path IN ('SELF_RECOVERY', 'FOUND_BY_OTHER')),
    reported_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reported_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lost_item_id INTEGER NOT NULL,
    found_item_id INTEGER NOT NULL,
    match_score INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Accepted', 'Rejected')),
    image_similarity_score INTEGER,
    image_validation_status TEXT NOT NULL DEFAULT 'Unavailable',
    image_validation_reason TEXT,
    image_validation_evidence TEXT,
    image_validated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lost_item_id) REFERENCES items(id) ON DELETE CASCADE,
    FOREIGN KEY (found_item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS case_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    event TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_type ON items(type);
CREATE INDEX IF NOT EXISTS idx_items_location ON items(location);
CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);
CREATE INDEX IF NOT EXISTS idx_case_events_item ON case_events(item_id);
CREATE INDEX IF NOT EXISTS idx_matches_lost ON matches(lost_item_id);
CREATE INDEX IF NOT EXISTS idx_matches_found ON matches(found_item_id);

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
