"""
WSGI entrypoint for AWS EC2 Ubuntu Gunicorn deployment.
Usage: gunicorn --workers 3 --bind 127.0.0.1:5000 wsgi:app
"""
import os
from app import app
from database import ensure_instance_dir

ensure_instance_dir()

# Ensure SQLite database is initialized and seeded if brand new
from database import DATABASE_PATH
if not os.path.exists(DATABASE_PATH):
    from seed import seed_database
    seed_database()

if __name__ == "__main__":
    app.run()
