# Find-My-Item — Production Architecture

A complete, production-grade web application built with **Python Flask + SQLite + HTML/CSS/Vanilla JavaScript**, designed for campus recovery operations and deployment on **AWS EC2 (Ubuntu) with Nginx and Gunicorn**.

---

## Architecture Overview

* **Backend**: Python Flask (`app.py`), session authentication, RESTful routing, and incident correlation scoring engine.
* **Database**: SQLite (`instance/campus.db`), schema with foreign keys, index optimization, and full data integrity. **100% of all UI metrics, tables, timelines, and cards are computed directly from SQLite**.
* **Frontend**: Responsive HTML5, modular CSS3 (`static/css/style.css`), vanilla JavaScript (`static/js/script.js`), asymmetric login panel, incident timeline, and recovery board.
* **Deployment Pipeline**: GitHub &rarr; AWS EC2 Ubuntu 24.04 &rarr; Nginx Reverse Proxy &rarr; Gunicorn WSGI &rarr; Flask &rarr; SQLite.

---

## Seed Accounts for Demonstrations

| Role | Username | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@bvrithyderabad.edu.in` | configured private password | Security & Facilities Console, Case Resolution, Deletion |
| **Student 1** | `student1` | `student123` | Report Filing, My Reports, Case Inquiry |
| **Student 2** | `student2` | `student123` | Report Filing, My Reports, Case Inquiry |

*(The login screen provides a student demo shortcut; the administrator credentials are intentionally not exposed in the UI.)*

---

## AWS EC2 Ubuntu Deployment Walkthrough

### AI Image Validation Configuration

Every Found report linked to a Lost report must include a real PNG, JPG, JPEG, or WEBP upload. The backend sends both stored upload bytes to the configured vision model after the required details match, then stores the returned score, assessment, evidence, and validation timestamp in `matches`. A high visual score is only a potential match; human verification is still required before resolution.

Set the vision service configuration in the process environment before starting Flask or Gunicorn:

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_VISION_MODEL="gpt-4.1-mini"  # optional
```

If `OPENAI_API_KEY` is missing, either uploaded image is unavailable, or the vision request fails, the match is rejected or shown as **AI image validation unavailable**. The application never invents an image score. Do not expose `OPENAI_API_KEY` in source control.

### 1. Launch AWS EC2 Instance
* **AMI**: Ubuntu 24.04 LTS (HVM)
* **Instance Type**: `t2.micro` or `t3.micro` (Free Tier eligible)
* **Security Group**: Allow **SSH (Port 22)**, **HTTP (Port 80)**, and **HTTPS (Port 443)** from `0.0.0.0/0`.

### 2. Connect & Install Dependencies
```bash
ssh -i "your-key.pem" ubuntu@<your-ec2-public-ip>

sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv nginx git
```

### 3. Clone Repository & Setup Virtual Environment
```bash
cd /home/ubuntu
git clone <your-github-repo-url> campus-lost-found
cd campus-lost-found

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run initial database setup and seeding
python3 seed.py
```

### 4. Configure Systemd Service
```bash
sudo cp lostfound.service /etc/systemd/system/lostfound.service
sudo systemctl daemon-reload
sudo systemctl start lostfound
sudo systemctl enable lostfound
sudo systemctl status lostfound
```

### 5. Configure Nginx Reverse Proxy
```bash
sudo cp nginx.conf /etc/nginx/sites-available/lostfound
sudo ln -s /etc/nginx/sites-available/lostfound /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Verify Deployment
Navigate to `http://<your-ec2-public-ip>` in your web browser. The Find-My-Item application is now live on the public internet.

---

## Project Structure

```
├── app.py                  # Flask routes, auth decorators, and matching engine
├── database.py             # SQLite connection management & helpers
├── schema.sql              # Relational schema (users, items, matches, case_events)
├── seed.py                 # Demonstrative campus data generator
├── wsgi.py                 # WSGI entrypoint for Gunicorn
├── nginx.conf              # Production Nginx reverse proxy configuration
├── lostfound.service       # Systemd service unit for Ubuntu
├── requirements.txt        # Python package dependencies
├── templates/              # Jinja2 templates
│   ├── base.html           # Master layout & global navigation
│   ├── login.html          # Asymmetric split-screen login
│   ├── index.html          # Student recovery feed & multi-filter search
│   ├── report.html         # Incident intake form with drag-and-drop upload
│   ├── item.html           # Case view, match scoring, and incident timeline
│   ├── my_reports.html     # User's personal submission tracker
│   ├── admin.html          # Operations center overview & KPI metrics
│   ├── admin_cases.html    # Master case audit table with resolution controls
│   ├── admin_users.html    # User directory with active report counts
│   └── admin_activity.html # System-wide chronological event audit log
├── static/
│   ├── css/style.css       # Clean academic design system
│   ├── js/script.js        # Form validation, drag-and-drop, and modal scripts
│   └── uploads/            # Incident photos and category illustrations
└── server.ts               # Gateway runner for dev preview & container ingress
```
