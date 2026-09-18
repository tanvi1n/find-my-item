"""Authorization and Lost↔Found pairing integration checks using an isolated SQLite DB."""
import io
import os
import contextlib

import database


with contextlib.nullcontext(os.path.join(os.getcwd(), 'instance')) as temp_dir:
    database.INSTANCE_DIR = temp_dir
    database.DATABASE_PATH = os.path.join(temp_dir, 'authorization-test.db')

    from app import app

    def fake_image_validator(lost, found):
        return {
            'status': 'Passed',
            'score': 94,
            'reason': 'Stub validator confirms the images match the same object for testing.',
            'evidence': ['Same shape and color profile in the uploaded images.'],
            'validated_at': '2026-09-18 00:00:00',
        }

    app.config['TESTING'] = True
    app.config['IMAGE_VALIDATOR'] = fake_image_validator
    database.init_db()
    database.ensure_migrations()
    client = app.test_client()

    def signup_and_login(name, email):
        response = client.post('/signup', data={
            'name': name, 'email': email, 'password': 'password123',
            'confirm_password': 'password123',
        })
        assert response.status_code == 302
        response = client.post('/login', data={'username': email, 'password': 'password123'})
        assert response.status_code == 302

    def report(item_type, name, lost_item_id=None, description='Authorization test item'):
        png_bytes = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00'
            b'\x01\x01\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        data = {
            'item_name': name, 'type': item_type, 'category': 'Electronics',
            'location': 'Library', 'date': '2026-09-18',
            'contact': 'student@college.edu.in', 'description': description,
            'image': (io.BytesIO(png_bytes), f'{name.lower().replace(" ", "_")}.png'),
        }
        if lost_item_id is not None:
            data['lost_item_id'] = str(lost_item_id)
        return client.post('/report', data=data, content_type='multipart/form-data')

    def latest_id(item_type):
        conn = database.get_direct_connection()
        row = conn.execute('SELECT id FROM items WHERE type = ? ORDER BY id DESC LIMIT 1', (item_type,)).fetchone()
        conn.close()
        return row['id']

    signup_and_login('Student A', 'student-a@college.edu.in')
    assert report('Lost', 'A Lost Item').status_code == 302
    lost_a = latest_id('Lost')

    # A Lost owner can recover their own item without a Found report or verification.
    assert report('Lost', 'Owner Recovered Charger').status_code == 302
    self_recovered_id = latest_id('Lost')
    assert b'>Resolved<' in client.get(f'/item/{self_recovered_id}').data
    assert client.post(f'/report/{self_recovered_id}/resolve').status_code == 302
    conn = database.get_direct_connection()
    self_recovered = conn.execute(
        'SELECT status, resolution_path FROM items WHERE id = ?', (self_recovered_id,)
    ).fetchone()
    conn.close()
    assert self_recovered['status'] == 'Resolved'
    assert self_recovered['resolution_path'] == 'SELF_RECOVERY'
    assert self_recovered_id not in [entry['id'] for entry in client.get('/api/eligible-lost-reports').get_json()]
    client.get('/logout')

    signup_and_login('Student B', 'student-b@college.edu.in')
    assert report('Lost', 'B Lost Item').status_code == 302
    lost_b = latest_id('Lost')

    # Another student cannot delete or resolve Student A's Lost case.
    assert client.post(f'/report/{lost_a}/delete').status_code == 403
    assert client.post(f'/report/{lost_a}/resolve').status_code == 403

    # Admin can monitor and review, but cannot directly delete or resolve cases.
    client.get('/logout')
    client.post('/login', data={'username': 'admin@bvrithyderabad.edu.in', 'password': '25WH5A0518'})
    assert client.post(f'/admin/delete/{lost_a}').status_code == 403
    assert client.post(f'/admin/resolve/{lost_a}').status_code == 403
    client.get('/logout')
    client.post('/login', data={'username': 'student-b@college.edu.in', 'password': 'password123'})

    # A LOST submission may not carry a selected report ID.
    assert report('Lost', 'Invalid Lost-to-Lost', lost_b).status_code == 400

    # A Found report selecting a live Lost report is accepted.
    assert report('Found', 'A Lost Item', lost_a, description='Different identifying detail').status_code == 400
    assert report('Found', 'A Lost Item', lost_a).status_code == 302
    found_b = latest_id('Found')
    assert report('Found', 'A Lost Item', lost_a).status_code == 302
    found_b_second = latest_id('Found')

    # A Found report cannot select another Found report.
    assert client.post(f'/report/{found_b}/match', data={'target_item_id': found_b_second}).status_code == 400

    # A Lost reporter may propose an opposite-type Found report, never a same-type report.
    client.get('/logout')
    client.post('/login', data={'username': 'student-a@college.edu.in', 'password': 'password123'})
    assert client.post(f'/report/{lost_a}/match', data={'target_item_id': found_b}).status_code == 302
    assert client.post(f'/report/{lost_a}/match', data={'target_item_id': lost_b}).status_code == 400

    # A Found report cannot be linked to a different Lost item's details.
    assert report('Found', 'Owner Recovered Charger', lost_b).status_code == 400

    # The Lost owner can move their own case into verification, changing its status.
    conn = database.get_direct_connection()
    match_id = conn.execute(
        'SELECT id FROM matches WHERE lost_item_id = ? AND found_item_id = ?', (lost_a, found_b)
    ).fetchone()['id']
    conn.close()
    assert client.post(f'/match/{match_id}/request-verification', data={'private_detail': 'blue sticker'}).status_code == 302
    conn = database.get_direct_connection()
    assert conn.execute('SELECT status FROM items WHERE id = ?', (lost_a,)).fetchone()['status'] == 'Verification'
    conn.close()

    # Admins can advance a pending verification from the operations console.
    client.get('/logout')
    client.post('/login', data={'username': 'admin@bvrithyderabad.edu.in', 'password': '25WH5A0518'})
    assert b'Verify and Proceed' in client.get('/admin').data

    # The finder confirms verification; only the Lost owner then resolves it.
    client.get('/logout')
    client.post('/login', data={'username': 'student-b@college.edu.in', 'password': 'password123'})
    assert client.post(f'/match/{match_id}/complete-verification', data={'private_detail': 'blue sticker'}).status_code == 302
    client.get('/logout')
    client.post('/login', data={'username': 'student-a@college.edu.in', 'password': 'password123'})
    assert client.post(f'/report/{lost_a}/resolve').status_code == 302
    conn = database.get_direct_connection()
    resolved_lost = conn.execute(
        'SELECT status, resolution_path FROM items WHERE id = ?', (lost_a,)
    ).fetchone()
    conn.close()
    assert resolved_lost['status'] == 'Resolved'
    assert resolved_lost['resolution_path'] == 'FOUND_BY_OTHER'
    eligible = client.get('/api/eligible-lost-reports').get_json()
    assert lost_a not in [entry['id'] for entry in eligible]

print('OK: authorization and Lost-Found pairing rules passed')
os.remove(database.DATABASE_PATH)
