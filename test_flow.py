"""Quick integration test: signup → report → DB counts → search."""
import io
from app import app
from database import get_direct_connection

app.config['TESTING'] = True
client = app.test_client()

# Reject Gmail
r = client.post(
    '/signup',
    data={
        'name': 'Test',
        'email': 'bad@gmail.com',
        'password': 'password123',
        'confirm_password': 'password123',
    },
    follow_redirects=True,
)
assert b'Personal email' in r.data or b'.edu.in' in r.data, 'Gmail should be rejected'

email = 'flowtest@college.edu.in'
client.post(
    '/signup',
    data={
        'name': 'Flow Test',
        'email': email,
        'password': 'password123',
        'confirm_password': 'password123',
    },
)

client.post('/login', data={'username': 'flowtest', 'password': 'password123'})

# Students must neither see nor access the administration console.
r = client.get('/')
assert b'Admin Console' not in r.data
r = client.get('/admin', follow_redirects=True)
assert b'Access denied' in r.data

# A changed session role alone cannot expose the console or grant access.
with client.session_transaction() as session:
    session['role'] = 'admin'
r = client.get('/')
assert b'Admin Console' not in r.data
r = client.get('/admin', follow_redirects=True)
assert b'Access denied' in r.data
with client.session_transaction() as session:
    session['role'] = 'student'

conn = get_direct_connection()
before = conn.execute('SELECT COUNT(*) FROM items').fetchone()[0]
conn.close()
assert before >= 16, f'Expected seeded reports, got {before}'

# Minimal valid PNG
png_bytes = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00'
    b'\x01\x01\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)
buf = io.BytesIO(png_bytes)

r = client.post(
    '/report',
    data={
        'item_name': 'Purple Test Wallet',
        'type': 'Lost',
        'category': 'Wallet/Money',
        'location': 'Library',
        'date': '2026-09-18',
        'contact': email,
        'description': 'Integration test report',
        'image': (buf, 'test_wallet.png'),
    },
    content_type='multipart/form-data',
    follow_redirects=True,
)
assert r.status_code == 200

conn = get_direct_connection()
after = conn.execute('SELECT COUNT(*) FROM items').fetchone()[0]
row = conn.execute(
    'SELECT id, image_path, status FROM items ORDER BY id DESC LIMIT 1'
).fetchone()
conn.close()
assert after == before + 1, f'Expected one new item after report, got {before} -> {after}'
assert row['image_path'].startswith('/static/uploads/'), row['image_path']
assert row['status'] == 'Open' or row['status'] == 'Potential Match'

r = client.get('/')
assert b'Purple Test Wallet' in r.data

r = client.get('/my-reports')
assert b'Purple Test Wallet' in r.data

client.get('/logout')
client.post('/login', data={'username': 'admin@bvrithyderabad.edu.in', 'password': '25WH5A0518'})
r = client.get('/admin')
assert str(after).encode() in r.data
assert b'Admin Console' in r.data
r = client.get('/admin/cases')
assert b'Purple Test Wallet' in r.data

print(f'OK: full flow passed ({before} -> {after}, live SQLite everywhere)')
