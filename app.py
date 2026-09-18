import os
import re
import uuid
import base64
import json
import mimetypes
import urllib.error
import urllib.request
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, g, jsonify, abort
)

from database import ADMIN_EMAIL, get_db, close_db, ensure_instance_dir, ensure_migrations, init_db

app = Flask(__name__)
# A known fallback key would let someone forge a session cookie.  Deployments
# should set SECRET_KEY; the per-process fallback remains safe for local use.
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(32)
app.teardown_appcontext(close_db)

_db_migrated = False


@app.before_request
def _ensure_schema():
    global _db_migrated
    if not _db_migrated:
        ensure_migrations()
        _db_migrated = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
ALLOWED_EXTENSIONS_SEED = ALLOWED_EXTENSIONS | {'svg'}

BLOCKED_EMAIL_DOMAINS = (
    'gmail.com', 'googlemail.com', 'yahoo.com', 'yahoo.co.in', 'outlook.com',
    'hotmail.com', 'live.com', 'icloud.com', 'protonmail.com', 'rediffmail.com'
)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
app.config['VISION_MINIMUM_SCORE'] = 70

CAMPUS_LOCATIONS = [
    'Library', 'CSE Block', 'Cafeteria', 'Lab 1', 'Lab 2',
    'Lab 3', 'Main Block', 'Seminar Hall', 'Parking', 'Gymnasium'
]

CAMPUS_CATEGORIES = [
    'Electronics', 'ID/Documents', 'Wallet/Money', 'Stationery',
    'Accessories', 'Keys', 'Clothing', 'Other'
]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def is_valid_student_email(email):
    """Students must register with a college email ending in .edu.in."""
    email = (email or '').strip().lower()
    if not email or '@' not in email:
        return False, 'Please enter a valid college email address.'
    local, domain = email.rsplit('@', 1)
    if not local:
        return False, 'Please enter a valid college email address.'
    for blocked in BLOCKED_EMAIL_DOMAINS:
        if domain == blocked or domain.endswith('.' + blocked):
            return False, 'Personal email providers are not allowed. Use your official college email ending in .edu.in.'
    if not domain.endswith('.edu.in'):
        return False, 'Registration requires an official college email ending in .edu.in.'
    return True, None


def username_from_email(email):
    local = email.strip().lower().split('@')[0]
    safe = re.sub(r'[^a-z0-9._-]', '', local)
    return safe or 'student'

def is_verified_admin():
    """Return true only for the reserved administrator account in the database."""
    user_id = session.get('user_id')
    if not user_id or session.get('email', '').lower() != ADMIN_EMAIL:
        return False

    user = get_db().execute(
        "SELECT role, email FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return bool(
        user
        and user['role'] == 'admin'
        and user['email'].lower() == ADMIN_EMAIL
    )


# Context processor to inject common variables into templates
@app.context_processor
def inject_globals():
    return {
        'current_user': {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('role'),
            'name': session.get('name'),
            'email': session.get('email')
        } if 'user_id' in session else None,
        'is_verified_admin': is_verified_admin(),
        'locations': CAMPUS_LOCATIONS,
        'categories': CAMPUS_CATEGORIES,
        'now_year': datetime.now().year,
        'now_date': datetime.now().strftime('%Y-%m-%d'),
        'product_name': 'Find-My-Item'
    }

# Decorators for auth
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Admin authentication required.', 'warning')
            return redirect(url_for('login', next=request.url))
        if not is_verified_admin():
            flash('Access denied. Administrator privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Matching Engine
def calculate_match_score(item1, item2):
    """
    Computes a realistic percentage match score between a Lost and Found item.
    Compares: Category (30%), Location (25%), Item Name (35%), Date proximity (10%).
    """
    score = 0
    # Category match
    if item1['category'].lower() == item2['category'].lower():
        score += 30

    # Location match
    loc1 = item1['location'].lower()
    loc2 = item2['location'].lower()
    if loc1 == loc2:
        score += 25
    elif ('lab' in loc1 and 'lab' in loc2) or ('hall' in loc1 and 'hall' in loc2):
        score += 15

    # Item name word similarity
    stopwords = {'a', 'an', 'the', 'and', 'with', 'for', 'in', 'on', 'near', 'lost', 'found', 'my'}
    words1 = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', item1['item_name'].lower())) - stopwords
    words2 = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', item2['item_name'].lower())) - stopwords
    if words1 and words2:
        overlap = words1.intersection(words2)
        if overlap:
            sim = len(overlap) / max(len(words1), len(words2))
            score += int(sim * 35)

    # Date proximity
    try:
        d1 = datetime.strptime(item1['date'], '%Y-%m-%d')
        d2 = datetime.strptime(item2['date'], '%Y-%m-%d')
        diff_days = abs((d1 - d2).days)
        if diff_days <= 1:
            score += 10
        elif diff_days <= 3:
            score += 7
        elif diff_days <= 7:
            score += 4
    except Exception:
        pass

    return min(score, 98)


def get_match_breakdown(lost_item, found_item):
    """Human-readable match explanation for the UI."""
    reasons = []
    score = 0

    if lost_item['category'].lower() == found_item['category'].lower():
        score += 30
        reasons.append({
            'label': 'Category',
            'detail': f"Both listed as \"{lost_item['category']}\" (+30%)"
        })

    loc_l = lost_item['location'].lower()
    loc_f = found_item['location'].lower()
    if loc_l == loc_f:
        score += 25
        reasons.append({
            'label': 'Location',
            'detail': f"Same campus area: {lost_item['location']} (+25%)"
        })
    elif ('lab' in loc_l and 'lab' in loc_f) or ('hall' in loc_l and 'hall' in loc_f):
        score += 15
        reasons.append({
            'label': 'Location',
            'detail': f"Nearby zones: {lost_item['location']} ↔ {found_item['location']} (+15%)"
        })

    stopwords = {'a', 'an', 'the', 'and', 'with', 'for', 'in', 'on', 'near', 'lost', 'found', 'my'}
    words_l = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', lost_item['item_name'].lower())) - stopwords
    words_f = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', found_item['item_name'].lower())) - stopwords
    if words_l and words_f:
        overlap = sorted(words_l.intersection(words_f))
        if overlap:
            sim = len(overlap) / max(len(words_l), len(words_f))
            pts = int(sim * 35)
            score += pts
            reasons.append({
                'label': 'Item name',
                'detail': f"Shared terms: {', '.join(overlap)} (+{pts}%)"
            })

    try:
        d_l = datetime.strptime(lost_item['date'], '%Y-%m-%d')
        d_f = datetime.strptime(found_item['date'], '%Y-%m-%d')
        diff_days = abs((d_l - d_f).days)
        if diff_days <= 1:
            score += 10
            reasons.append({'label': 'Date', 'detail': 'Reported within 1 day of each other (+10%)'})
        elif diff_days <= 3:
            score += 7
            reasons.append({'label': 'Date', 'detail': f'Reported {diff_days} days apart (+7%)'})
        elif diff_days <= 7:
            score += 4
            reasons.append({'label': 'Date', 'detail': f'Reported {diff_days} days apart (+4%)'})
    except Exception:
        pass

    return {
        'score': min(score, 98),
        'reasons': reasons
    }


def enrich_matches(db, matches_rows):
    """Attach lost/found rows, breakdown, and pending verification state."""
    enriched = []
    for match in matches_rows:
        lost = db.execute("SELECT * FROM items WHERE id = ?", (match['lost_item_id'],)).fetchone()
        found = db.execute("SELECT * FROM items WHERE id = ?", (match['found_item_id'],)).fetchone()
        if not lost or not found:
            continue
        breakdown = get_match_breakdown(lost, found)
        verification = db.execute(
            """SELECT verifications.*, users.name AS requested_by_name,
                      users.username AS requested_by_username
               FROM verifications
               JOIN users ON users.id = verifications.requested_by
               WHERE match_id = ? ORDER BY verifications.created_at DESC LIMIT 1""",
            (match['id'],)
        ).fetchone()
        row = dict(match)
        row['breakdown'] = breakdown
        try:
            row['image_validation_evidence_list'] = json.loads(row.get('image_validation_evidence') or '[]')
        except (TypeError, ValueError):
            row['image_validation_evidence_list'] = []
        row['verification'] = dict(verification) if verification else None
        enriched.append(row)
    return enriched


def resolve_matched_pair(db, lost_id, found_id, actor_username, actor_label):
    """Mark both items resolved and log timeline events."""
    for item_id in (lost_id, found_id):
        db.execute(
            "UPDATE items SET status = 'Resolved', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (item_id,)
        )
        db.execute(
            "INSERT INTO case_events (item_id, event, description, created_by) VALUES (?, ?, ?, ?)",
            (item_id, "Case Resolved",
             f"Ownership verified by {actor_label}. Case closed in SQLite.",
             actor_username)
        )
    db.execute(
        "UPDATE matches SET status = 'Accepted' WHERE lost_item_id = ? AND found_item_id = ?",
        (lost_id, found_id)
    )


EXACT_MATCH_FIELDS = ('item_name', 'category', 'location', 'date', 'description')


def has_exact_match_details(lost, found):
    """A Found report is valid only when every identifying field equals its Lost case."""
    return all((lost[field] or '') == (found[field] or '') for field in EXACT_MATCH_FIELDS)


def local_uploaded_image(image_path):
    """Resolve only a real raster upload stored by this application."""
    prefix = '/static/uploads/'
    if not image_path or not image_path.startswith(prefix):
        return None
    filename = os.path.basename(image_path)
    if not allowed_file(filename):
        return None
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return path if os.path.isfile(path) else None


def image_data_url(image_path):
    path = local_uploaded_image(image_path)
    if not path:
        return None
    mime_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    with open(path, 'rb') as image_file:
        encoded = base64.b64encode(image_file.read()).decode('ascii')
    return f'data:{mime_type};base64,{encoded}'


def image_validation_unavailable(reason):
    return {
        'status': 'Unavailable', 'score': None, 'reason': reason,
        'evidence': [], 'validated_at': None,
    }


def validate_match_images(lost, found):
    """Use a configured vision model to compare two stored raster uploads.

    This function never fabricates a score.  It returns Unavailable when no
    service or valid images exist, and only a model-produced result can pass.
    """
    test_validator = app.config.get('IMAGE_VALIDATOR')
    if test_validator:
        return test_validator(lost, found)

    lost_image = image_data_url(lost['image_path'])
    found_image = image_data_url(found['image_path'])
    if not lost_image or not found_image:
        return image_validation_unavailable('Both reports must have real uploaded PNG, JPG, JPEG, or WEBP images.')

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return image_validation_unavailable('AI image validation unavailable: OPENAI_API_KEY is not configured.')

    schema = {
        'type': 'object', 'additionalProperties': False,
        'properties': {
            'same_physical_object': {'type': 'boolean'},
            'similarity_score': {'type': 'integer', 'minimum': 0, 'maximum': 100},
            'assessment': {'type': 'string'},
            'evidence': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 4},
        },
        'required': ['same_physical_object', 'similarity_score', 'assessment', 'evidence'],
    }
    payload = {
        'model': os.environ.get('OPENAI_VISION_MODEL', 'gpt-4.1-mini'),
        'store': False,
        'input': [{
            'role': 'user',
            'content': [
                {'type': 'input_text', 'text': (
                    'Compare these two images of reported campus property. Determine whether they likely show '
                    'the same physical object based only on visible shape, color, markings, and features. '
                    'Return cautious JSON; do not claim certainty.'
                )},
                {'type': 'input_image', 'image_url': lost_image, 'detail': 'high'},
                {'type': 'input_image', 'image_url': found_image, 'detail': 'high'},
            ],
        }],
        'text': {'format': {'type': 'json_schema', 'name': 'image_comparison', 'strict': True, 'schema': schema}},
    }
    request_data = json.dumps(payload).encode('utf-8')
    request_obj = urllib.request.Request(
        'https://api.openai.com/v1/responses', data=request_data,
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}, method='POST'
    )
    try:
        with urllib.request.urlopen(request_obj, timeout=30) as response:
            response_data = json.loads(response.read().decode('utf-8'))
        text = next(
            content['text']
            for output in response_data.get('output', [])
            if output.get('type') == 'message'
            for content in output.get('content', [])
            if content.get('type') == 'output_text'
        )
        result = json.loads(text)
        score = result['similarity_score']
        same_object = result['same_physical_object'] and score >= app.config['VISION_MINIMUM_SCORE']
        return {
            'status': 'Passed' if same_object else 'Failed',
            'score': score,
            'reason': result['assessment'],
            'evidence': result['evidence'],
            'validated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        }
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, StopIteration, ValueError, TypeError) as error:
        return image_validation_unavailable(f'AI image validation unavailable: {error.__class__.__name__}.')


def eligible_lost_reports(db):
    """Lost reports that can be selected by a new Found report."""
    return db.execute(
        """SELECT id, item_name, category, location, date, description
           FROM items
           WHERE type = 'Lost' AND status IN ('Open', 'Potential Match')
             AND TRIM(COALESCE(description, '')) != ''
             AND image_path GLOB '/static/uploads/*.*'
             AND image_path NOT LIKE '%.svg'
           ORDER BY created_at DESC"""
    ).fetchall()


def create_match(db, lost, found, actor_username, image_validation=None):
    """Create one valid Lost <-> Found match and update only active cases."""
    if lost['type'] != 'Lost' or found['type'] != 'Found':
        abort(400, 'Matches must pair one Lost report with one Found report.')
    if lost['status'] not in ('Open', 'Potential Match'):
        abort(400, 'The selected Lost report is not eligible for a new match.')
    if lost['status'] == 'Resolved' or found['status'] == 'Resolved':
        abort(400, 'Resolved reports cannot be matched.')
    if not has_exact_match_details(lost, found):
        abort(400, 'Found details must exactly match the selected Lost report.')

    image_validation = image_validation or validate_match_images(lost, found)
    if image_validation['status'] == 'Unavailable':
        abort(503, image_validation['reason'])
    if image_validation['status'] != 'Passed':
        abort(422, 'AI image validation indicates that these reports do not show the same physical object.')

    existing = db.execute(
        "SELECT id FROM matches WHERE lost_item_id = ? AND found_item_id = ?",
        (lost['id'], found['id'])
    ).fetchone()
    if existing:
        return existing['id']

    cur = db.execute(
        """INSERT INTO matches
           (lost_item_id, found_item_id, match_score, status, image_similarity_score,
            image_validation_status, image_validation_reason, image_validation_evidence, image_validated_at)
           VALUES (?, ?, ?, 'Pending', ?, ?, ?, ?, ?)""",
        (lost['id'], found['id'], calculate_match_score(lost, found), image_validation['score'], image_validation['status'],
         image_validation['reason'], json.dumps(image_validation['evidence']), image_validation['validated_at'])
    )
    for report in (lost, found):
        if report['status'] == 'Open':
            db.execute("UPDATE items SET status = 'Potential Match', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (report['id'],))
        db.execute(
            "INSERT INTO case_events (item_id, event, description, created_by) VALUES (?, ?, ?, ?)",
            (report['id'], 'Potential Match Detected',
             f'A Lost ↔ Found match was proposed with Case #{found["id"] if report["id"] == lost["id"] else lost["id"]}.',
             actor_username)
        )
    return cur.lastrowid


def run_matching_engine_for_item(item_id):
    """Checks the newly added item against existing opposite items and logs matches."""
    db = get_db()
    item = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not item or item['status'] == 'Resolved':
        return

    opposite_type = 'Found' if item['type'] == 'Lost' else 'Lost'
    candidates = db.execute(
        "SELECT * FROM items WHERE type = ? AND status != 'Resolved' AND id != ?",
        (opposite_type, item_id)
    ).fetchall()

    for candidate in candidates:
        if has_exact_match_details(item if item['type'] == 'Lost' else candidate,
                                   candidate if item['type'] == 'Lost' else item):
            lost_id = item['id'] if item['type'] == 'Lost' else candidate['id']
            found_id = candidate['id'] if item['type'] == 'Lost' else item['id']

            # Check if match already recorded
            existing = db.execute(
                "SELECT * FROM matches WHERE lost_item_id = ? AND found_item_id = ?",
                (lost_id, found_id)
            ).fetchone()

            if not existing:
                # Score-only automatic matches are intentionally disabled. A
                # Found report must select a Lost case and pass image validation.
                continue
                # Update item statuses if still 'Open'
                if item['status'] == 'Open':
                    db.execute("UPDATE items SET status = 'Potential Match', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (item['id'],))
                if candidate['status'] == 'Open':
                    db.execute("UPDATE items SET status = 'Potential Match', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (candidate['id'],))

                # Log case events
                db.execute(
                    "INSERT INTO case_events (item_id, event, description, created_by) VALUES (?, ?, ?, ?)",
                    (item['id'], "Potential Match Detected",
                     f"System detected an exact match with Case #{candidate['id']} ({candidate['item_name']}).",
                     "System Matching Engine")
                )
                db.execute(
                    "INSERT INTO case_events (item_id, event, description, created_by) VALUES (?, ?, ?, ?)",
                    (candidate['id'], "Potential Match Detected",
                     f"System detected an exact match with Case #{item['id']} ({item['item_name']}).",
                     "System Matching Engine")
                )
    db.commit()


# ==================== ROUTES ====================

@app.route('/')
def index():
    db = get_db()
    query_str = request.args.get('q', '').strip()
    type_filter = request.args.get('type', 'All')
    status_filter = request.args.get('status', 'All')
    location_filter = request.args.get('location', 'All')
    category_filter = request.args.get('category', 'All')

    # Build parameterized query
    sql = """
        SELECT items.*, users.name as reporter_name, users.username as reporter_username 
        FROM items 
        JOIN users ON items.reported_by = users.id 
        WHERE 1=1
    """
    params = []

    if query_str:
        sql += " AND (items.item_name LIKE ? OR items.description LIKE ? OR items.location LIKE ?)"
        like_term = f"%{query_str}%"
        params.extend([like_term, like_term, like_term])

    if type_filter in ['Lost', 'Found']:
        sql += " AND items.type = ?"
        params.append(type_filter)

    if status_filter in ['Open', 'Potential Match', 'Verification', 'Resolved']:
        sql += " AND items.status = ?"
        params.append(status_filter)

    if location_filter and location_filter != 'All':
        sql += " AND items.location = ?"
        params.append(location_filter)

    if category_filter and category_filter != 'All':
        sql += " AND items.category = ?"
        params.append(category_filter)

    sql += " ORDER BY items.created_at DESC"
    items = db.execute(sql, params).fetchall()

    # Dynamic metrics strictly calculated from SQLite
    total_count = db.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    open_count = db.execute("SELECT COUNT(*) FROM items WHERE status = 'Open'").fetchone()[0]
    matched_count = db.execute("SELECT COUNT(*) FROM items WHERE status = 'Potential Match'").fetchone()[0]
    verification_count = db.execute("SELECT COUNT(*) FROM items WHERE status = 'Verification'").fetchone()[0]
    resolved_count = db.execute("SELECT COUNT(*) FROM items WHERE status = 'Resolved'").fetchone()[0]

    return render_template(
        'index.html',
        items=items,
        query_str=query_str,
        type_filter=type_filter,
        status_filter=status_filter,
        location_filter=location_filter,
        category_filter=category_filter,
        stats={
            'total': total_count,
            'open': open_count,
            'matched': matched_count,
            'verification': verification_count,
            'resolved': resolved_count
        }
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        if is_verified_admin():
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter both username and password.', 'warning')
            return render_template('login.html')

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? OR LOWER(email) = LOWER(?)",
            (username, username)
        ).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['name'] = user['name']
            session['email'] = user['email']

            flash(f"Welcome back, {user['name']}!", 'success')
            next_page = request.args.get('next')

            if user['role'] == 'admin':
                return redirect(next_page or url_for('admin_dashboard'))
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not name or not email or not password:
            flash('Please complete all required fields.', 'warning')
            return render_template('signup.html')

        ok, err = is_valid_student_email(email)
        if not ok:
            flash(err, 'danger')
            return render_template('signup.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'warning')
            return render_template('signup.html')

        if password != confirm:
            flash('Passwords do not match.', 'warning')
            return render_template('signup.html')

        db = get_db()
        email_lower = email.lower()
        if email_lower == ADMIN_EMAIL:
            flash('This administrator email is reserved.', 'danger')
            return render_template('signup.html')
        existing_email = db.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email_lower,)).fetchone()
        if existing_email:
            flash('An account with this college email already exists. Please sign in.', 'warning')
            return redirect(url_for('login'))

        base_username = username_from_email(email_lower)
        username = base_username
        suffix = 1
        while db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
            username = f"{base_username}{suffix}"
            suffix += 1

        db.execute(
            """INSERT INTO users (username, password_hash, role, name, email)
            VALUES (?, ?, 'student', ?, ?)""",
            (username, generate_password_hash(password), name, email_lower)
        )
        db.commit()
        flash(
            f'Account created! Sign in with {email_lower} or username "{username}" and your password.',
            'success'
        )
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been securely logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/report', methods=['GET', 'POST'])
@login_required
def report_item():
    if request.method == 'POST':
        item_name = request.form.get('item_name', '').strip()
        item_type = request.form.get('type', 'Lost')
        category = request.form.get('category', 'Other')
        location = request.form.get('location', '').strip()
        date_str = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
        contact = request.form.get('contact', '').strip()
        description = request.form.get('description', '').strip()

        if item_type not in ('Lost', 'Found'):
            abort(400, 'Report type must be Lost or Found.')

        if not item_name or not location or not contact:
            flash('Please fill in the required fields (Item name, Location, and Contact).', 'warning')
            return render_template('report.html')

        db = get_db()
        selected_lost = None
        selected_lost_id = request.form.get('lost_item_id', '').strip()
        if item_type == 'Found':
            if not selected_lost_id.isdigit():
                abort(400, 'A Found report must select an eligible Lost report.')
            selected_lost = db.execute(
                """SELECT * FROM items WHERE id = ? AND type = 'Lost'
                   AND status IN ('Open', 'Potential Match')""",
                (int(selected_lost_id),)
            ).fetchone()
            if not selected_lost:
                abort(400, 'Select a current eligible Lost report; this report cannot be matched.')
            if not description:
                abort(400, 'A Found report must include the exact identifying description from the Lost report.')
            submitted_found = {
                'item_name': item_name,
                'category': category,
                'location': location,
                'date': date_str,
                'description': description,
            }
            if not has_exact_match_details(selected_lost, submitted_found):
                abort(400, 'Found details must exactly match the selected Lost report.')
        elif selected_lost_id:
            abort(400, 'Only Found reports may select a Lost report.')

        # A real raster upload is required: category SVG fallbacks are not
        # evidence that two reports show the same physical object.
        image_path = None
        file = request.files.get('image')
        if not file or not file.filename or not allowed_file(file.filename):
            abort(400, 'A real JPG, JPEG, PNG, or WEBP item image is required.')
        extension = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"{uuid.uuid4().hex}.{extension}")
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        image_path = f"/static/uploads/{filename}"

        image_validation = None
        if selected_lost:
            candidate_found = {
                'item_name': item_name, 'category': category, 'location': location,
                'date': date_str, 'description': description, 'image_path': image_path,
            }
            image_validation = validate_match_images(selected_lost, candidate_found)
            if image_validation['status'] != 'Passed':
                os.remove(save_path)
                if image_validation['status'] == 'Unavailable':
                    abort(503, image_validation['reason'])
                abort(422, 'AI image validation indicates that these images do not show the same physical object.')

        cur = db.cursor()
        cur.execute(
            """INSERT INTO items 
            (item_name, description, type, category, location, date, contact, image_path, status, reported_by) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Open', ?)""",
            (item_name, description, item_type, category, location, date_str, contact, image_path, session['user_id'])
        )
        new_item_id = cur.lastrowid

        # Insert initial timeline event
        cur.execute(
            "INSERT INTO case_events (item_id, event, description, created_by) VALUES (?, ?, ?, ?)",
            (new_item_id, "Report Created",
             f"{session.get('name')} submitted a new {item_type} item report.",
             session.get('username'))
        )
        db.commit()

        if selected_lost:
            found = db.execute("SELECT * FROM items WHERE id = ?", (new_item_id,)).fetchone()
            create_match(db, selected_lost, found, session.get('username', 'Unknown'), image_validation)
            db.commit()

        flash('✓ Report submitted! Your report has been added to the campus recovery board.', 'success')
        return redirect(url_for('item_detail', item_id=new_item_id))

    return render_template('report.html')


@app.route('/api/eligible-lost-reports')
@login_required
def api_eligible_lost_reports():
    reports = eligible_lost_reports(get_db())
    return jsonify([dict(report) for report in reports])


@app.route('/report/<int:item_id>/match', methods=['POST'])
@login_required
def propose_match(item_id):
    """Let a reporter propose an opposite-type match for their own report."""
    target_id = request.form.get('target_item_id', '').strip()
    if not target_id.isdigit():
        abort(400, 'Select a report to match.')

    db = get_db()
    source = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    target = db.execute("SELECT * FROM items WHERE id = ?", (int(target_id),)).fetchone()
    if not source or not target:
        abort(404)
    if source['reported_by'] != session['user_id']:
        abort(403)
    if source['id'] == target['id'] or source['type'] == target['type']:
        abort(400, 'Matches must pair one Lost report with one Found report.')
    if source['status'] == 'Resolved' or target['status'] == 'Resolved':
        abort(400, 'Resolved reports cannot be matched.')
    if source['type'] == 'Found' and target['status'] not in ('Open', 'Potential Match'):
        abort(400, 'The selected Lost report is not eligible for a new match.')

    lost, found = (source, target) if source['type'] == 'Lost' else (target, source)
    create_match(db, lost, found, session.get('username', 'Unknown'))
    db.commit()
    flash('Lost ↔ Found match proposed.', 'success')
    return redirect(url_for('item_detail', item_id=item_id))

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    db = get_db()
    item = db.execute(
        """SELECT items.*, users.name as reporter_name, users.username as reporter_username, users.email as reporter_email 
        FROM items 
        JOIN users ON items.reported_by = users.id 
        WHERE items.id = ?""",
        (item_id,)
    ).fetchone()

    if not item:
        abort(404)

    # Timeline events
    events = db.execute(
        "SELECT * FROM case_events WHERE item_id = ? ORDER BY created_at ASC",
        (item_id,)
    ).fetchall()

    # Look for matches in `matches` table
    match_sql = """
        SELECT matches.*, 
               lost.id as lost_id, lost.item_name as lost_name, lost.location as lost_loc, lost.image_path as lost_img, lost.date as lost_date,
               found.id as found_id, found.item_name as found_name, found.location as found_loc, found.image_path as found_img, found.date as found_date
        FROM matches
        JOIN items lost ON matches.lost_item_id = lost.id
        JOIN items found ON matches.found_item_id = found.id
        WHERE matches.lost_item_id = ? OR matches.found_item_id = ?
        ORDER BY matches.match_score DESC
    """
    matches = enrich_matches(db, db.execute(match_sql, (item_id, item_id)).fetchall())

    return render_template('item.html', item=item, events=events, matches=matches)

@app.route('/my-reports')
@login_required
def my_reports():
    db = get_db()
    user_id = session['user_id']
    status_filter = request.args.get('status', 'All')
    type_filter = request.args.get('type', 'All')

    sql = "SELECT * FROM items WHERE reported_by = ?"
    params = [user_id]

    if type_filter in ['Lost', 'Found']:
        sql += " AND type = ?"
        params.append(type_filter)

    if status_filter in ['Open', 'Potential Match', 'Verification', 'Resolved']:
        sql += " AND status = ?"
        params.append(status_filter)

    sql += " ORDER BY created_at DESC"
    reports = db.execute(sql, params).fetchall()
    report_rows = []
    for report in reports:
        row = dict(report)
        match = db.execute(
            """SELECT matches.id AS match_id, matches.image_validation_status,
                      verifications.status AS verification_status
               FROM matches
               LEFT JOIN verifications ON verifications.match_id = matches.id
               WHERE (matches.lost_item_id = ? OR matches.found_item_id = ?)
               ORDER BY verifications.created_at DESC, matches.created_at DESC
               LIMIT 1""",
            (report['id'], report['id'])
        ).fetchone()
        row['match_id'] = match['match_id'] if match else None
        row['image_validation_status'] = match['image_validation_status'] if match else None
        row['verification_status'] = match['verification_status'] if match else None
        report_rows.append(row)

    stats = {
        'total': db.execute("SELECT COUNT(*) FROM items WHERE reported_by = ?", (user_id,)).fetchone()[0],
        'open': db.execute("SELECT COUNT(*) FROM items WHERE reported_by = ? AND status = 'Open'", (user_id,)).fetchone()[0],
        'matched': db.execute("SELECT COUNT(*) FROM items WHERE reported_by = ? AND status = 'Potential Match'", (user_id,)).fetchone()[0],
        'resolved': db.execute("SELECT COUNT(*) FROM items WHERE reported_by = ? AND status = 'Resolved'", (user_id,)).fetchone()[0],
    }

    return render_template(
        'my_reports.html',
        reports=report_rows,
        stats=stats,
        status_filter=status_filter,
        type_filter=type_filter
    )


# ==================== ADMIN ROUTES ====================

@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()

    # Exact SQLite counts (No hardcoded values)
    total_reports = db.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    open_cases = db.execute("SELECT COUNT(*) FROM items WHERE status = 'Open'").fetchone()[0]
    potential_matches = db.execute("SELECT COUNT(*) FROM items WHERE status = 'Potential Match'").fetchone()[0]
    verification_cases = db.execute("SELECT COUNT(*) FROM items WHERE status = 'Verification'").fetchone()[0]
    resolved_cases = db.execute("SELECT COUNT(*) FROM items WHERE status = 'Resolved'").fetchone()[0]
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    # Recent cases
    recent_cases = db.execute(
        """SELECT items.*, users.name as reporter_name 
        FROM items 
        JOIN users ON items.reported_by = users.id 
        ORDER BY items.created_at DESC LIMIT 8"""
    ).fetchall()

    # Recent activity
    recent_activity = db.execute(
        """SELECT case_events.*, items.item_name 
        FROM case_events 
        JOIN items ON case_events.item_id = items.id 
        ORDER BY case_events.created_at DESC LIMIT 6"""
    ).fetchall()

    # Active matches requiring review
    pending_matches = db.execute(
        """SELECT matches.*, 
               lost.item_name as lost_name, lost.location as lost_loc,
             lost.image_path as lost_img, found.item_name as found_name,
             found.location as found_loc, found.image_path as found_img
        FROM matches
        JOIN items lost ON matches.lost_item_id = lost.id
        JOIN items found ON matches.found_item_id = found.id
        WHERE matches.status = 'Pending'
        ORDER BY matches.match_score DESC LIMIT 4"""
    ).fetchall()

    verification_requests = db.execute(
        """SELECT verifications.id, verifications.match_id, verifications.status, verifications.created_at,
                  lost.id as lost_id, lost.item_name as lost_name, lost.image_path as lost_img,
                  found.id as found_id, found.item_name as found_name, found.image_path as found_img,
                  matches.match_score, users.name as reporter_name, users.email as reporter_email
           FROM verifications
           JOIN items lost ON verifications.lost_item_id = lost.id
           JOIN items found ON verifications.found_item_id = found.id
           JOIN matches ON verifications.match_id = matches.id
           JOIN users ON verifications.requested_by = users.id
           WHERE verifications.status = 'Pending'
           ORDER BY verifications.created_at DESC"""
    ).fetchall()

    return render_template(
        'admin.html',
        stats={
            'total': total_reports,
            'open': open_cases,
            'matches': potential_matches,
            'verification': verification_cases,
            'resolved': resolved_cases,
            'users': total_users
        },
        recent_cases=recent_cases,
        recent_activity=recent_activity,
        pending_matches=pending_matches,
        verification_requests=verification_requests
    )

@app.route('/admin/cases')
@admin_required
def admin_cases():
    db = get_db()
    status_filter = request.args.get('status', 'All')
    type_filter = request.args.get('type', 'All')
    query_str = request.args.get('q', '').strip()

    sql = """
        SELECT items.*, users.name as reporter_name, users.username as reporter_username 
        FROM items 
        JOIN users ON items.reported_by = users.id 
        WHERE 1=1
    """
    params = []

    if query_str:
        sql += " AND (items.item_name LIKE ? OR items.location LIKE ? OR users.name LIKE ?)"
        like_term = f"%{query_str}%"
        params.extend([like_term, like_term, like_term])

    if status_filter in ['Open', 'Potential Match', 'Verification', 'Resolved']:
        sql += " AND items.status = ?"
        params.append(status_filter)

    if type_filter in ['Lost', 'Found']:
        sql += " AND items.type = ?"
        params.append(type_filter)

    sql += " ORDER BY items.created_at DESC"
    cases = db.execute(sql, params).fetchall()

    stats = {
        'total': db.execute("SELECT COUNT(*) FROM items").fetchone()[0],
        'open': db.execute("SELECT COUNT(*) FROM items WHERE status = 'Open'").fetchone()[0],
        'matches': db.execute("SELECT COUNT(*) FROM items WHERE status = 'Potential Match'").fetchone()[0],
        'verification': db.execute("SELECT COUNT(*) FROM items WHERE status = 'Verification'").fetchone()[0],
        'resolved': db.execute("SELECT COUNT(*) FROM items WHERE status = 'Resolved'").fetchone()[0],
    }

    return render_template(
        'admin_cases.html',
        cases=cases,
        stats=stats,
        status_filter=status_filter,
        type_filter=type_filter,
        query_str=query_str
    )

@app.route('/admin/item/<int:item_id>')
@admin_required
def admin_item_detail(item_id):
    db = get_db()
    item = db.execute(
        """SELECT items.*, users.name as reporter_name, users.username as reporter_username, users.email as reporter_email 
        FROM items 
        JOIN users ON items.reported_by = users.id 
        WHERE items.id = ?""",
        (item_id,)
    ).fetchone()

    if not item:
        abort(404)

    events = db.execute(
        "SELECT * FROM case_events WHERE item_id = ? ORDER BY created_at ASC",
        (item_id,)
    ).fetchall()

    matches = db.execute(
        """SELECT matches.*, 
               lost.id as lost_id, lost.item_name as lost_name, lost.location as lost_loc, lost.image_path as lost_img,
               found.id as found_id, found.item_name as found_name, found.location as found_loc, found.image_path as found_img
        FROM matches
        JOIN items lost ON matches.lost_item_id = lost.id
        JOIN items found ON matches.found_item_id = found.id
        WHERE matches.lost_item_id = ? OR matches.found_item_id = ?
        ORDER BY matches.match_score DESC""",
        (item_id, item_id)
    ).fetchall()

    matches = enrich_matches(db, matches)

    return render_template('item.html', item=item, events=events, matches=matches, is_admin_view=True)


@app.route('/match/<int:match_id>/request-verification', methods=['POST'])
@login_required
def request_verification(match_id):
    db = get_db()
    match = db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    if not match:
        abort(404)

    lost = db.execute("SELECT * FROM items WHERE id = ?", (match['lost_item_id'],)).fetchone()
    found = db.execute("SELECT * FROM items WHERE id = ?", (match['found_item_id'],)).fetchone()
    if not lost or not found:
        abort(404)
    if lost['type'] != 'Lost' or found['type'] != 'Found':
        abort(400, 'Invalid match: reports must be Lost and Found.')
    if match['image_validation_status'] != 'Passed':
        abort(400, 'Human verification requires a completed AI image comparison for both uploaded images.')

    if session['user_id'] != lost['reported_by']:
        abort(403)

    private_detail = request.form.get('private_detail', '').strip()
    if len(private_detail) < 3:
        flash('Provide a private distinguishing detail (not shown publicly).', 'warning')
        return redirect(url_for('item_detail', item_id=lost['id']))

    pending = db.execute(
        "SELECT id FROM verifications WHERE match_id = ? AND status = 'Pending'",
        (match_id,)
    ).fetchone()
    if pending:
        flash('Verification is already in progress for this match.', 'info')
        return redirect(url_for('item_detail', item_id=lost['id']))

    detail_hash = generate_password_hash(private_detail)
    db.execute(
        """INSERT INTO verifications
        (match_id, lost_item_id, found_item_id, private_detail_hash, status, requested_by)
        VALUES (?, ?, ?, ?, 'Pending', ?)""",
        (match_id, lost['id'], found['id'], detail_hash, session['user_id'])
    )

    for item_id in (lost['id'], found['id']):
        db.execute(
            "UPDATE items SET status = 'Verification', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (item_id,)
        )
        db.execute(
            "INSERT INTO case_events (item_id, event, description, created_by) VALUES (?, ?, ?, ?)",
            (item_id, "Verification Requested",
             "Owner submitted a private identifying detail for staff/finder review (detail not stored in timeline).",
             session.get('username'))
        )

    db.execute(
        "UPDATE matches SET status = 'Pending' WHERE id = ?",
        (match_id,)
    )
    db.commit()
    flash('Verification requested. A finder or admin will confirm your private detail.', 'success')
    return redirect(url_for('item_detail', item_id=lost['id']))


@app.route('/match/<int:match_id>/complete-verification', methods=['POST'])
@login_required
def complete_verification(match_id):
    db = get_db()
    match = db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    if not match:
        abort(404)

    lost = db.execute("SELECT * FROM items WHERE id = ?", (match['lost_item_id'],)).fetchone()
    found = db.execute("SELECT * FROM items WHERE id = ?", (match['found_item_id'],)).fetchone()
    verification = db.execute(
        "SELECT * FROM verifications WHERE match_id = ? AND status = 'Pending' ORDER BY created_at DESC LIMIT 1",
        (match_id,)
    ).fetchone()

    if not lost or not found or not verification:
        flash('No pending verification found for this match.', 'warning')
        return redirect(url_for('item_detail', item_id=match['lost_item_id']))

    if lost['type'] != 'Lost' or found['type'] != 'Found':
        abort(400, 'Invalid match: reports must be Lost and Found.')

    is_finder = session['user_id'] == found['reported_by']
    if not (is_finder or is_verified_admin()):
        abort(403)

    attempt = request.form.get('private_detail', '').strip()
    if not attempt:
        flash('Enter the private detail provided by the owner.', 'warning')
        return redirect(url_for('item_detail', item_id=found['id']))

    if not check_password_hash(verification['private_detail_hash'], attempt):
        flash('Private detail did not match. Case remains under verification.', 'danger')
        return redirect(url_for('item_detail', item_id=found['id']))

    actor = session.get('username', 'staff')

    db.execute(
        """UPDATE verifications SET status = 'Confirmed', verified_by = ?, verified_at = CURRENT_TIMESTAMP
        WHERE id = ?""",
        (actor, verification['id'])
    )

    for item_id in (lost['id'], found['id']):
        db.execute(
            "INSERT INTO case_events (item_id, event, description, created_by) VALUES (?, ?, ?, ?)",
            (item_id, "Verification Completed",
             "Private detail confirmed. Ownership validated without exposing sensitive information.",
             actor)
        )

    db.commit()
    flash('Verification successful. The Lost-report owner can now resolve their own case.', 'success')
    return redirect(url_for('item_detail', item_id=found['id']))

@app.route('/admin/resolve/<int:item_id>', methods=['POST'])
@admin_required
def admin_resolve_case(item_id):
    abort(403)

@app.route('/admin/delete/<int:item_id>', methods=['POST'])
@admin_required
def admin_delete_case(item_id):
    abort(403)


@app.route('/report/<int:item_id>/resolve', methods=['POST'])
@login_required
def resolve_own_lost_report(item_id):
    """Allow the Lost owner to resolve through self-recovery or verification."""
    db = get_db()
    item = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not item:
        abort(404)
    if item['reported_by'] != session['user_id']:
        abort(403)
    if item['type'] != 'Lost':
        abort(400, 'Only a Lost report can be resolved through this owner flow.')

    confirmed = db.execute(
        """SELECT verifications.id FROM verifications
           JOIN matches ON matches.id = verifications.match_id
           WHERE verifications.lost_item_id = ? AND verifications.status = 'Confirmed'
                         AND matches.lost_item_id = ? AND matches.image_validation_status = 'Passed'""",
        (item_id, item_id)
    ).fetchone()
    resolution_path = 'FOUND_BY_OTHER' if confirmed else 'SELF_RECOVERY'
    db.execute(
        "UPDATE items SET status = 'Resolved', resolution_path = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (resolution_path, item_id)
    )
    if confirmed:
        db.execute("UPDATE matches SET status = 'Accepted' WHERE lost_item_id = ?", (item_id,))
    db.execute(
        "INSERT INTO case_events (item_id, event, description, created_by) VALUES (?, ?, ?, ?)",
        (item_id, 'Case Resolved',
         'Lost-report owner resolved the case through ' +
         ('human verification after a Found report.' if confirmed else 'self-recovery.'),
         session.get('username'))
    )
    db.commit()
    flash('Your Lost report has been marked Resolved.', 'success')
    return redirect(url_for('item_detail', item_id=item_id))


@app.route('/report/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_own_report(item_id):
    db = get_db()
    item = db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not item:
        abort(404)
    if item['reported_by'] != session['user_id']:
        abort(403)
    if item['status'] == 'Resolved':
        flash('Resolved reports must remain in the database.', 'warning')
        return redirect(url_for('item_detail', item_id=item_id))

    db.execute("DELETE FROM case_events WHERE item_id = ?", (item_id,))
    db.execute("DELETE FROM matches WHERE lost_item_id = ? OR found_item_id = ?", (item_id, item_id))
    db.execute("DELETE FROM items WHERE id = ?", (item_id,))
    db.commit()
    flash(f"Your report #{item_id} has been deleted.", 'info')
    return redirect(url_for('my_reports'))

@app.route('/admin/users')
@admin_required
def admin_users():
    db = get_db()
    # Real report counts per user
    users = db.execute(
        """SELECT users.id, users.name, users.username, users.role, users.email, users.created_at,
                  COUNT(items.id) as reports_count
        FROM users
        LEFT JOIN items ON users.id = items.reported_by
        GROUP BY users.id
        ORDER BY users.role ASC, users.name ASC"""
    ).fetchall()

    return render_template('admin_users.html', users=users)

@app.route('/admin/activity')
@admin_required
def admin_activity():
    db = get_db()
    events = db.execute(
        """SELECT case_events.*, items.item_name, items.type as item_type, items.location, items.status as item_status
        FROM case_events
        JOIN items ON case_events.item_id = items.id
        ORDER BY case_events.created_at DESC"""
    ).fetchall()

    return render_template('admin_activity.html', events=events)

# API endpoint for instant search preview
@app.route('/api/search')
def api_search():
    db = get_db()
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])

    items = db.execute(
        """SELECT id, item_name, type, location, date, status, image_path 
        FROM items 
        WHERE item_name LIKE ? OR location LIKE ? OR description LIKE ?
        LIMIT 6""",
        (f"%{q}%", f"%{q}%", f"%{q}%")
    ).fetchall()

    return jsonify([dict(ix) for ix in items])

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    ensure_instance_dir()
    ensure_migrations()
    from database import DATABASE_PATH
    if not os.path.exists(DATABASE_PATH):
        from seed import seed_database
        seed_database()

    port = int(os.environ.get('FLASK_PORT', 5005))
    app.run(host='0.0.0.0', port=port, debug=False)
