import os
import sqlite3
from werkzeug.security import generate_password_hash
from database import (
  ADMIN_EMAIL, ADMIN_NAME, ADMIN_PASSWORD_HASH, ADMIN_USERNAME,
  BASE_DIR, DATABASE_PATH, init_db, get_direct_connection
)

UPLOADS_DIR = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOADS_DIR, exist_ok=True)

def create_svg_image(filename, title, subtitle, icon_svg, bg_color="#F1F5F9", accent_color="#0F172A"):
    filepath = os.path.join(UPLOADS_DIR, filename)
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400" width="100%" height="100%">
  <defs>
    <linearGradient id="grad_{filename.replace('.', '_')}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg_color}" />
      <stop offset="100%" stop-color="#E2E8F0" />
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="6" stdDeviation="8" flood-opacity="0.08" />
    </filter>
  </defs>
  <rect width="600" height="400" rx="16" fill="url(#grad_{filename.replace('.', '_')})" />
  <g transform="translate(300, 180) scale(1.1)">
    <g filter="url(#shadow)">
      {icon_svg}
    </g>
  </g>
  <text x="300" y="325" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="20" font-weight="700" fill="{accent_color}" text-anchor="middle" letter-spacing="0.5">{title}</text>
  <text x="300" y="352" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="14" font-weight="500" fill="#64748B" text-anchor="middle">{subtitle}</text>
  <circle cx="50" cy="50" r="14" fill="{accent_color}" fill-opacity="0.1" />
  <circle cx="50" cy="50" r="6" fill="{accent_color}" fill-opacity="0.6" />
  <text x="75" y="55" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="12" font-weight="600" fill="#64748B" letter-spacing="1">CAMPUS PROPERTY VERIFIED</text>
</svg>'''
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    return f"/static/uploads/{filename}"

def generate_sample_images():
    # 1. Wallet
    wallet_svg = '''
    <g transform="translate(-60, -45)">
      <rect x="0" y="0" width="120" height="80" rx="10" fill="#334155" />
      <path d="M 0 20 L 120 20" stroke="#1E293B" stroke-width="3" />
      <rect x="75" y="28" width="45" height="32" rx="6" fill="#475569" />
      <circle cx="95" cy="44" r="5" fill="#F8FAFC" />
      <path d="M 10 10 L 40 10" stroke="#64748B" stroke-width="3" stroke-linecap="round" />
    </g>'''
    create_svg_image("wallet.svg", "BLACK LEATHER WALLET", "Bifold with embossed texture", wallet_svg, "#F8FAFC", "#0F172A")

    # 2. Calculator
    calc_svg = '''
    <g transform="translate(-45, -60)">
      <rect x="0" y="0" width="90" height="125" rx="12" fill="#1E293B" />
      <rect x="12" y="14" width="66" height="28" rx="4" fill="#94A3B8" />
      <text x="70" y="34" font-family="monospace" font-size="14" font-weight="bold" fill="#0F172A" text-anchor="end">3.14159</text>
      <!-- Buttons -->
      <g fill="#475569">
        <rect x="12" y="52" width="12" height="10" rx="2" fill="#0284C7"/>
        <rect x="30" y="52" width="12" height="10" rx="2" fill="#0284C7"/>
        <rect x="48" y="52" width="12" height="10" rx="2" fill="#0284C7"/>
        <rect x="66" y="52" width="12" height="10" rx="2" fill="#DC2626"/>

        <rect x="12" y="68" width="12" height="10" rx="2"/>
        <rect x="30" y="68" width="12" height="10" rx="2"/>
        <rect x="48" y="68" width="12" height="10" rx="2"/>
        <rect x="66" y="68" width="12" height="10" rx="2"/>

        <rect x="12" y="84" width="12" height="10" rx="2"/>
        <rect x="30" y="84" width="12" height="10" rx="2"/>
        <rect x="48" y="84" width="12" height="10" rx="2"/>
        <rect x="66" y="84" width="12" height="10" rx="2"/>

        <rect x="12" y="100" width="30" height="12" rx="2"/>
        <rect x="48" y="100" width="30" height="12" rx="2" fill="#16A34A"/>
      </g>
    </g>'''
    create_svg_image("calculator.svg", "SCIENTIFIC CALCULATOR", "Casio FX-991EX ClassWiz", calc_svg, "#F1F5F9", "#0284C7")

    # 3. Water Bottle
    bottle_svg = '''
    <g transform="translate(-25, -65)">
      <rect x="15" y="0" width="20" height="15" rx="3" fill="#0369A1" />
      <rect x="8" y="15" width="34" height="14" rx="4" fill="#0284C7" />
      <rect x="0" y="28" width="50" height="105" rx="14" fill="#0EA5E9" />
      <path d="M 0 50 Q 25 58 50 50" stroke="#38BDF8" stroke-width="4" fill="none" />
      <path d="M 0 80 Q 25 88 50 80" stroke="#38BDF8" stroke-width="4" fill="none" />
      <circle cx="25" cy="105" r="8" fill="#E0F2FE" />
    </g>'''
    create_svg_image("water_bottle.svg", "BLUE WATER BOTTLE", "Hydro Flask 32oz Wide Mouth", bottle_svg, "#F0F9FF", "#0369A1")

    # 4. Travel Mug
    mug_svg = '''
    <g transform="translate(-30, -55)">
      <rect x="10" y="0" width="40" height="12" rx="3" fill="#334155" />
      <path d="M 5 12 L 10 105 L 50 105 L 55 12 Z" fill="#64748B" />
      <rect x="15" y="45" width="30" height="35" rx="4" fill="#475569" />
      <path d="M 55 30 C 75 30 75 80 52 80" stroke="#475569" stroke-width="7" fill="none" stroke-linecap="round" />
    </g>'''
    create_svg_image("travel_mug.svg", "STAINLESS STEEL MUG", "Contigo thermal travel tumbler", mug_svg, "#F8FAFC", "#334155")

    # 5. Backpack (recovery board)
    backpack_svg = '''
    <g transform="translate(-45, -60)">
      <path d="M 20 25 C 20 0 70 0 70 25" stroke="#1E293B" stroke-width="8" fill="none" stroke-linecap="round"/>
      <rect x="5" y="20" width="80" height="100" rx="18" fill="#1E293B" />
      <rect x="15" y="60" width="60" height="50" rx="8" fill="#334155" />
      <path d="M 15 65 L 75 65" stroke="#0F172A" stroke-width="3" />
      <circle cx="45" cy="85" r="4" fill="#94A3B8" />
      <rect x="35" y="32" width="20" height="15" rx="3" fill="#475569" />
    </g>'''
    create_svg_image("backpack_lost.svg", "BLACK BACKPACK", "North Face Vault with Laptop Sleeve", backpack_svg, "#F8FAFC", "#0F172A")
    create_svg_image("backpack_found.svg", "BLACK BACKPACK (FOUND)", "Black nylon backpack with grey trims", backpack_svg, "#F8FAFC", "#0F172A")

    # 6. ID Card
    id_svg = '''
    <g transform="translate(-65, -45)">
      <rect x="0" y="0" width="130" height="85" rx="8" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="2" />
      <rect x="0" y="0" width="130" height="22" rx="8" fill="#1E3A8A" />
      <text x="12" y="15" font-family="sans-serif" font-size="9" font-weight="bold" fill="#FFFFFF">CAMPUS UNIVERSITY ID</text>
      <rect x="12" y="30" width="32" height="42" rx="4" fill="#94A3B8" />
      <circle cx="28" cy="46" r="10" fill="#64748B" />
      <path d="M 16 70 C 16 58 40 58 40 70 Z" fill="#64748B" />
      <rect x="52" y="34" width="65" height="7" rx="2" fill="#1E293B" />
      <rect x="52" y="46" width="45" height="5" rx="2" fill="#64748B" />
      <rect x="52" y="56" width="55" height="5" rx="2" fill="#94A3B8" />
      <rect x="52" y="66" width="30" height="4" rx="2" fill="#CBD5E1" />
    </g>'''
    create_svg_image("id_card.svg", "STUDENT ID CARD", "University Smart Card with Photo", id_svg, "#EFF6FF", "#1E3A8A")

    # 7. Laptop Charger
    charger_svg = '''
    <g transform="translate(-45, -45)">
      <rect x="0" y="10" width="60" height="60" rx="8" fill="#F8FAFC" stroke="#94A3B8" stroke-width="3" />
      <circle cx="30" cy="40" r="12" fill="#E2E8F0" />
      <path d="M 24 0 L 24 10 M 36 0 L 36 10" stroke="#64748B" stroke-width="4" stroke-linecap="round" />
      <path d="M 60 40 C 95 40 95 80 115 80" stroke="#94A3B8" stroke-width="5" fill="none" stroke-linecap="round" />
      <rect x="115" y="74" width="20" height="12" rx="3" fill="#475569" />
    </g>'''
    create_svg_image("charger.svg", "65W TYPE-C CHARGER", "Apple/Dell Compatible White Adapter", charger_svg, "#F8FAFC", "#475569")

    # 8. Earbuds
    earbuds_svg = '''
    <g transform="translate(-50, -45)">
      <rect x="0" y="0" width="70" height="50" rx="18" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="3" />
      <circle cx="35" cy="25" r="3" fill="#22C55E" />
      <!-- Left Bud -->
      <g transform="translate(75, 10)">
        <circle cx="10" cy="10" r="10" fill="#FFFFFF" stroke="#94A3B8" stroke-width="2" />
        <rect x="7" y="18" width="6" height="20" rx="3" fill="#E2E8F0" />
      </g>
    </g>'''
    create_svg_image("earbuds.svg", "WIRELESS EARBUDS", "White Bluetooth In-Ear Headphones", earbuds_svg, "#F0FDF4", "#16A34A")

    # 9. Keys
    keys_svg = '''
    <g transform="translate(-40, -45)">
      <circle cx="25" cy="25" r="22" stroke="#64748B" stroke-width="6" fill="none" />
      <g transform="rotate(30 25 25)">
        <path d="M 40 25 L 85 25 L 85 35 L 75 35 L 75 25 L 65 33 L 55 25" stroke="#334155" stroke-width="5" fill="none" />
        <circle cx="35" cy="25" r="6" fill="#334155" />
      </g>
      <g transform="rotate(75 25 25)">
        <path d="M 40 25 L 80 25 L 80 32 L 70 32 L 60 25" stroke="#0284C7" stroke-width="4" fill="none" />
      </g>
    </g>'''
    create_svg_image("keys.svg", "METAL KEYCHAIN", "3 Room Keys with Blue Lanyard", keys_svg, "#F8FAFC", "#0F172A")

    # 10. Notebook
    notebook_svg = '''
    <g transform="translate(-45, -55)">
      <rect x="0" y="0" width="85" height="110" rx="6" fill="#1E3A8A" />
      <rect x="0" y="0" width="14" height="110" rx="3" fill="#172554" />
      <rect x="25" y="25" width="48" height="28" rx="4" fill="#FFFFFF" />
      <line x1="30" y1="35" x2="65" y2="35" stroke="#94A3B8" stroke-width="2" />
      <line x1="30" y1="45" x2="55" y2="45" stroke="#94A3B8" stroke-width="2" />
      <!-- Spiral dots -->
      <circle cx="7" cy="15" r="3" fill="#94A3B8" />
      <circle cx="7" cy="35" r="3" fill="#94A3B8" />
      <circle cx="7" cy="55" r="3" fill="#94A3B8" />
      <circle cx="7" cy="75" r="3" fill="#94A3B8" />
      <circle cx="7" cy="95" r="3" fill="#94A3B8" />
    </g>'''
    create_svg_image("notebook.svg", "ENGINEERING NOTEBOOK", "Hardcover Grid Journal (Calculus Notes)", notebook_svg, "#EFF6FF", "#1E3A8A")

    # 11. USB Flash Drive
    usb_svg = '''
    <g transform="translate(-50, -25)">
      <rect x="0" y="8" width="60" height="32" rx="6" fill="#DC2626" />
      <rect x="60" y="14" width="25" height="20" rx="2" fill="#CBD5E1" />
      <rect x="70" y="18" width="6" height="5" fill="#1E293B" />
      <rect x="70" y="25" width="6" height="5" fill="#1E293B" />
      <circle cx="15" cy="24" r="5" fill="#991B1B" />
      <text x="35" y="28" font-family="sans-serif" font-size="10" font-weight="bold" fill="#FFFFFF">64GB</text>
    </g>'''
    create_svg_image("usb_drive.svg", "KINGSTON USB FLASH DRIVE", "64GB Red/Silver USB 3.1", usb_svg, "#FEF2F2", "#DC2626")

    # 12. Glasses
    glasses_svg = '''
    <g transform="translate(-65, -30)">
      <circle cx="25" cy="25" r="22" stroke="#78350F" stroke-width="6" fill="none" />
      <circle cx="95" cy="25" r="22" stroke="#78350F" stroke-width="6" fill="none" />
      <path d="M 47 25 Q 60 18 73 25" stroke="#78350F" stroke-width="5" fill="none" />
      <line x1="3" y1="20" x2="-15" y2="10" stroke="#78350F" stroke-width="4" stroke-linecap="round" />
      <line x1="117" y1="20" x2="135" y2="10" stroke="#78350F" stroke-width="4" stroke-linecap="round" />
    </g>'''
    create_svg_image("glasses.svg", "TORTOISE OPTICAL GLASSES", "Prescription Spectacles with Case", glasses_svg, "#FFFBEB", "#B45309")

    # 13. Smartwatch
    watch_svg = '''
    <g transform="translate(-25, -60)">
      <rect x="5" y="0" width="40" height="120" rx="6" fill="#1E293B" />
      <rect x="0" y="32" width="50" height="56" rx="14" fill="#0F172A" stroke="#475569" stroke-width="2" />
      <circle cx="25" cy="60" r="18" fill="#0284C7" fill-opacity="0.2" />
      <text x="25" y="64" font-family="monospace" font-size="12" font-weight="bold" fill="#38BDF8" text-anchor="middle">10:42</text>
    </g>'''
    create_svg_image("smartwatch.svg", "FITNESS SMARTWATCH", "Black Silicone Band with Heart Rate Monitor", watch_svg, "#F8FAFC", "#0F172A")

    # 14. TI-84
    ti_svg = '''
    <g transform="translate(-45, -60)">
      <rect x="0" y="0" width="90" height="125" rx="10" fill="#334155" />
      <rect x="12" y="12" width="66" height="34" rx="3" fill="#E2E8F0" />
      <text x="16" y="30" font-family="monospace" font-size="10" fill="#0F172A">y = x^2 - 4x</text>
      <rect x="12" y="55" width="66" height="60" rx="4" fill="#1E293B" />
      <circle cx="45" cy="68" r="8" fill="#64748B" />
    </g>'''
    create_svg_image("ti84.svg", "TI-84 PLUS CE", "Graphing Calculator (Silver Edition)", ti_svg, "#F1F5F9", "#334155")

    # 15. Scarf
    scarf_svg = '''
    <g transform="translate(-50, -40)">
      <path d="M 10 20 Q 50 0 90 20 Q 50 40 10 20 Z" fill="#64748B" />
      <path d="M 30 30 L 30 90 L 50 90 L 50 30 Z" fill="#475569" />
      <line x1="30" y1="92" x2="30" y2="100" stroke="#334155" stroke-width="3" stroke-linecap="round" />
      <line x1="40" y1="92" x2="40" y2="100" stroke="#334155" stroke-width="3" stroke-linecap="round" />
      <line x1="50" y1="92" x2="50" y2="100" stroke="#334155" stroke-width="3" stroke-linecap="round" />
    </g>'''
    create_svg_image("scarf.svg", "GREY KNITTED SCARF", "Woolen winter wrap with fringe ends", scarf_svg, "#F8FAFC", "#475569")

def seed_database():
    init_db()
    generate_sample_images()
    conn = get_direct_connection()
    cur = conn.cursor()

    # Clear existing records for clean workshop state
    cur.execute("DELETE FROM verifications")
    cur.execute("DELETE FROM case_events")
    cur.execute("DELETE FROM matches")
    cur.execute("DELETE FROM items")
    cur.execute("DELETE FROM users")
    cur.execute(
      "DELETE FROM sqlite_sequence WHERE name IN (?, ?, ?, ?, ?)" ,
      ("users", "items", "matches", "case_events", "verifications")
    )

    # Users
    pw_student = generate_password_hash("student123")

    users_data = [
        # Admins
        (ADMIN_USERNAME, ADMIN_PASSWORD_HASH, "admin", ADMIN_NAME, ADMIN_EMAIL, "2026-08-01 09:00:00"),
        # Students
        ("student1", pw_student, "student", "Alex Chen", "alex.chen@campus.edu.in", "2026-08-20 10:15:00"),
        ("student2", pw_student, "student", "Priya Patel", "priya.patel@campus.edu.in", "2026-08-21 11:30:00"),
        ("student3", pw_student, "student", "Jordan Taylor", "jordan.taylor@campus.edu.in", "2026-08-22 14:00:00"),
        ("student4", pw_student, "student", "Maya Lin", "maya.lin@campus.edu.in", "2026-08-25 09:45:00"),
        ("student5", pw_student, "student", "Marcus Johnson", "marcus.j@campus.edu.in", "2026-08-26 12:20:00"),
        ("student6", pw_student, "student", "Emily Davis", "emily.d@campus.edu.in", "2026-08-28 16:10:00"),
        ("student7", pw_student, "student", "Liam O'Connor", "liam.oc@campus.edu.in", "2026-09-01 08:30:00"),
        ("student8", pw_student, "student", "Sophia Rodriguez", "sophia.r@campus.edu.in", "2026-09-02 13:40:00"),
        ("student9", pw_student, "student", "Daniel Kim", "daniel.kim@campus.edu.in", "2026-09-05 15:50:00"),
        ("student10", pw_student, "student", "Hannah Scott", "hannah.s@campus.edu.in", "2026-09-08 11:10:00"),
        ("student11", pw_student, "student", "Ethan Brown", "ethan.b@campus.edu.in", "2026-09-10 10:05:00"),
        ("student12", pw_student, "student", "Chloe Wilson", "chloe.w@campus.edu.in", "2026-09-12 14:25:00"),
    ]

    user_id_map = {}
    for uname, pwhash, role, name, email, created_at in users_data:
        cur.execute(
            "INSERT INTO users (username, password_hash, role, name, email, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (uname, pwhash, role, name, email, created_at)
        )
        user_id_map[uname] = cur.lastrowid

    # Items
    # Note: 17 Sep 2026 is the reference timeframe (current date is Sep 2026)
    items_data = [
        # 1. Open Lost - Black Wallet
        {
            "id": 1,
            "item_name": "Black Leather Wallet",
            "description": "Black leather bifold wallet with student card and debit cards inside. Lost near the 2nd floor library reading desks.",
            "type": "Lost",
            "category": "Wallet/Money",
            "location": "Library",
            "date": "2026-09-17",
            "contact": "alex.chen@campus.edu.in | +91 98765 43210",
            "image_path": "/static/uploads/wallet.svg",
            "status": "Open",
            "reported_by": user_id_map["student1"],
            "created_at": "2026-09-17 10:42:00",
            "updated_at": "2026-09-17 10:42:00"
        },
        # 2. Open Lost - Scientific Calculator
        {
            "id": 2,
            "item_name": "Scientific Calculator",
            "description": "Casio FX-991EX ClassWiz in black case. Left on workbench 4 after afternoon physics practical.",
            "type": "Lost",
            "category": "Electronics",
            "location": "Lab 3",
            "date": "2026-09-16",
            "contact": "jordan.taylor@campus.edu.in",
            "image_path": "/static/uploads/calculator.svg",
            "status": "Open",
            "reported_by": user_id_map["student3"],
            "created_at": "2026-09-16 16:15:00",
            "updated_at": "2026-09-16 16:15:00"
        },
        # 3. Open Found - Blue Water Bottle
        {
            "id": 3,
            "item_name": "Blue Water Bottle",
            "description": "Hydro Flask 32oz vacuum insulated bottle in Pacific blue. Found on bench outside CSE Block room 204.",
            "type": "Found",
            "category": "Accessories",
            "location": "CSE Block",
            "date": "2026-09-17",
            "contact": "priya.patel@campus.edu.in",
            "image_path": "/static/uploads/water_bottle.svg",
            "status": "Open",
            "reported_by": user_id_map["student2"],
            "created_at": "2026-09-17 09:10:00",
            "updated_at": "2026-09-17 09:10:00"
        },
        # 4. Open Found - Stainless Steel Travel Mug
        {
            "id": 4,
            "item_name": "Stainless Steel Travel Mug",
            "description": "Contigo Autoseal insulated travel mug found on cafeteria corner table near juice counter.",
            "type": "Found",
            "category": "Accessories",
            "location": "Cafeteria",
            "date": "2026-09-17",
            "contact": "marcus.j@campus.edu.in",
            "image_path": "/static/uploads/travel_mug.svg",
            "status": "Open",
            "reported_by": user_id_map["student5"],
            "created_at": "2026-09-17 11:30:00",
            "updated_at": "2026-09-17 11:30:00"
        },
        # 5. Potential Match Pair - Lost Black Backpack (student4)
        {
            "id": 5,
            "item_name": "Black Backpack",
            "description": "The North Face black backpack containing notebooks, water bottle, and laptop charger. Left under booth seating during lunch hour.",
            "type": "Lost",
            "category": "Accessories",
            "location": "Cafeteria",
            "date": "2026-09-16",
            "contact": "maya.lin@campus.edu.in | +1 (555) 345-6789",
            "image_path": "/static/uploads/backpack_lost.svg",
            "status": "Potential Match",
            "reported_by": user_id_map["student4"],
            "created_at": "2026-09-16 13:20:00",
            "updated_at": "2026-09-16 14:15:00"
        },
        # 6. Potential Match Pair - Found Black Backpack (student5)
        {
            "id": 6,
            "item_name": "Black Backpack",
            "description": "Found black North Face backpack near the main entrance vestibule of the campus cafeteria.",
            "type": "Found",
            "category": "Accessories",
            "location": "Cafeteria",
            "date": "2026-09-16",
            "contact": "marcus.j@campus.edu.in (Turned over to Cafeteria Staff)",
            "image_path": "/static/uploads/backpack_found.svg",
            "status": "Potential Match",
            "reported_by": user_id_map["student5"],
            "created_at": "2026-09-16 14:05:00",
            "updated_at": "2026-09-16 14:15:00"
        },
        # 7. Verification - Student ID Card
        {
            "id": 7,
            "item_name": "Student ID Card",
            "description": "Campus undergraduate smart card belonging to Emily Davis (Civil Eng). Dropped near Registrar Office stairs.",
            "type": "Lost",
            "category": "ID/Documents",
            "location": "Main Block",
            "date": "2026-09-15",
            "contact": "emily.d@campus.edu.in",
            "image_path": "/static/uploads/id_card.svg",
            "status": "Verification",
            "reported_by": user_id_map["student6"],
            "created_at": "2026-09-15 11:00:00",
            "updated_at": "2026-09-16 10:20:00"
        },
        # 8. Resolved - Laptop Charger
        {
            "id": 8,
            "item_name": "Laptop Charger",
            "description": "Dell 65W Type-C AC adapter found plugged in by workstation 12 in Computer Lab 1.",
            "type": "Found",
            "category": "Electronics",
            "location": "Lab 1",
            "date": "2026-09-14",
            "contact": "liam.oc@campus.edu.in",
            "image_path": "/static/uploads/charger.svg",
            "status": "Resolved",
            "reported_by": user_id_map["student7"],
            "created_at": "2026-09-14 17:30:00",
            "updated_at": "2026-09-15 14:00:00"
        },
        # 9. Resolved - Wireless Earbuds
        {
            "id": 9,
            "item_name": "Wireless Earbuds",
            "description": "White true wireless earbuds inside charging case found on row D seat in Seminar Hall.",
            "type": "Found",
            "category": "Electronics",
            "location": "Seminar Hall",
            "date": "2026-09-13",
            "contact": "daniel.kim@campus.edu.in",
            "image_path": "/static/uploads/earbuds.svg",
            "status": "Resolved",
            "reported_by": user_id_map["student9"],
            "created_at": "2026-09-13 16:45:00",
            "updated_at": "2026-09-14 11:30:00"
        },
        # 10. Open Found - Metal Keychain
        {
            "id": 10,
            "item_name": "Keyring with 3 Keys",
            "description": "Silver ring with 2 brass mortise keys, 1 bike lock key, and a woven blue paracord tag. Found in North Parking Lot row C.",
            "type": "Found",
            "category": "Keys",
            "location": "Parking",
            "date": "2026-09-17",
            "contact": "hannah.s@campus.edu.in",
            "image_path": "/static/uploads/keys.svg",
            "status": "Open",
            "reported_by": user_id_map["student10"],
            "created_at": "2026-09-17 08:20:00",
            "updated_at": "2026-09-17 08:20:00"
        },
        # 11. Open Lost - Engineering Graph Notebook
        {
            "id": 11,
            "item_name": "Engineering Graph Notebook",
            "description": "Blue National Brand quad-ruled computation notebook with multivariable calculus notes and assignment sheets.",
            "type": "Lost",
            "category": "Stationery",
            "location": "Lab 2",
            "date": "2026-09-16",
            "contact": "priya.patel@campus.edu.in",
            "image_path": "/static/uploads/notebook.svg",
            "status": "Open",
            "reported_by": user_id_map["student2"],
            "created_at": "2026-09-16 15:40:00",
            "updated_at": "2026-09-16 15:40:00"
        },
        # 12. Open Found - 64GB Kingston USB Drive
        {
            "id": 12,
            "item_name": "64GB Kingston USB Drive",
            "description": "Red and silver USB 3.1 flash drive left in Library public terminal #7 front port.",
            "type": "Found",
            "category": "Electronics",
            "location": "Library",
            "date": "2026-09-17",
            "contact": "jordan.taylor@campus.edu.in",
            "image_path": "/static/uploads/usb_drive.svg",
            "status": "Open",
            "reported_by": user_id_map["student3"],
            "created_at": "2026-09-17 12:10:00",
            "updated_at": "2026-09-17 12:10:00"
        },
        # 13. Open Lost - Grey Knitted Scarf
        {
            "id": 13,
            "item_name": "Grey Knitted Scarf",
            "description": "Charcoal grey knit wool scarf lost during the morning orientation talk in Seminar Hall.",
            "type": "Lost",
            "category": "Clothing",
            "location": "Seminar Hall",
            "date": "2026-09-17",
            "contact": "sophia.r@campus.edu.in",
            "image_path": "/static/uploads/scarf.svg",
            "status": "Open",
            "reported_by": user_id_map["student8"],
            "created_at": "2026-09-17 13:00:00",
            "updated_at": "2026-09-17 13:00:00"
        },
        # 14. Verification - Prescription Glasses
        {
            "id": 14,
            "item_name": "Tortoise Optical Glasses",
            "description": "Ray-Ban round tortoise shell prescription eyeglasses with brown faux-leather case found near quiet study pod 3.",
            "type": "Found",
            "category": "Accessories",
            "location": "Library",
            "date": "2026-09-15",
            "contact": "ethan.b@campus.edu.in",
            "image_path": "/static/uploads/glasses.svg",
            "status": "Verification",
            "reported_by": user_id_map["student11"],
            "created_at": "2026-09-15 14:30:00",
            "updated_at": "2026-09-16 11:00:00"
        },
        # 15. Open Lost - Fitness Smartwatch
        {
            "id": 15,
            "item_name": "Fitness Smartwatch",
            "description": "Fitbit Charge 5 with black silicone band. Slipped off during badminton game at campus recreation center.",
            "type": "Lost",
            "category": "Electronics",
            "location": "Main Block",
            "date": "2026-09-16",
            "contact": "alex.chen@campus.edu.in",
            "image_path": "/static/uploads/smartwatch.svg",
            "status": "Open",
            "reported_by": user_id_map["student1"],
            "created_at": "2026-09-16 18:20:00",
            "updated_at": "2026-09-16 18:20:00"
        },
        # 16. Potential Match - Found TI-84 Graphing Calculator
        {
            "id": 16,
            "item_name": "TI-84 Graphing Calculator",
            "description": "Texas Instruments TI-84 Plus silver edition calculator found on table in Lab 3.",
            "type": "Found",
            "category": "Electronics",
            "location": "Lab 3",
            "date": "2026-09-16",
            "contact": "chloe.w@campus.edu.in",
            "image_path": "/static/uploads/ti84.svg",
            "status": "Potential Match",
            "reported_by": user_id_map["student12"],
            "created_at": "2026-09-16 17:00:00",
            "updated_at": "2026-09-16 17:10:00"
        }
    ]

    for item in items_data:
        cur.execute(
            """INSERT INTO items 
            (id, item_name, description, type, category, location, date, contact, image_path, status, reported_by, created_at, updated_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item["id"], item["item_name"], item["description"], item["type"], item["category"],
                item["location"], item["date"], item["contact"], item["image_path"], item["status"],
                item["reported_by"], item["created_at"], item["updated_at"]
            )
        )

    # Matches
    # Match 1: Items 5 (Lost Backpack) & 6 (Found Backpack) -> 88%
    cur.execute(
        """INSERT INTO matches (lost_item_id, found_item_id, match_score, status, created_at)
        VALUES (?, ?, ?, ?, ?)""",
        (5, 6, 88, "Pending", "2026-09-16 14:15:00")
    )
    # Match 2: Items 2 (Lost Calculator) & 16 (Found TI-84) -> 74%
    cur.execute(
        """INSERT INTO matches (lost_item_id, found_item_id, match_score, status, created_at)
        VALUES (?, ?, ?, ?, ?)""",
        (2, 16, 74, "Pending", "2026-09-16 17:10:00")
    )

    # Case Events (Timeline history)
    case_events_data = [
        # Item 1 (Black Wallet)
        (1, "Report Created", "Alex Chen submitted report for lost Black Leather Wallet in Library.", "2026-09-17 10:42:00", "student1"),
        
        # Item 2 (Calculator)
        (2, "Report Created", "Jordan Taylor reported lost Scientific Calculator in Lab 3.", "2026-09-16 16:15:00", "student3"),
        (2, "Potential Match Detected", "System detected 74% match with Found TI-84 Graphing Calculator in Lab 3.", "2026-09-16 17:10:00", "System Matching Engine"),
        
        # Item 3 (Blue Water Bottle)
        (3, "Report Created", "Priya Patel turned in Found Blue Water Bottle from CSE Block.", "2026-09-17 09:10:00", "student2"),

        # Item 4 (Travel Mug)
        (4, "Report Created", "Marcus Johnson found Stainless Steel Travel Mug in Cafeteria.", "2026-09-17 11:30:00", "student5"),

        # Item 5 (Lost Backpack)
        (5, "Report Created", "Maya Lin reported lost Black North Face Backpack in Cafeteria.", "2026-09-16 13:20:00", "student4"),
        (5, "Potential Match Detected", "Automated system detected 88% correlation with Found Black Backpack (Case #6).", "2026-09-16 14:15:00", "System Matching Engine"),

        # Item 6 (Found Backpack)
        (6, "Report Created", "Marcus Johnson reported found Black Backpack near Cafeteria entrance.", "2026-09-16 14:05:00", "student5"),
        (6, "Potential Match Detected", "Automated system linked this report to Lost Black Backpack (Case #5).", "2026-09-16 14:15:00", "System Matching Engine"),

        # Item 7 (Student ID Card)
        (7, "Report Created", "Emily Davis reported lost Student ID Card in Main Block.", "2026-09-15 11:00:00", "student6"),
        (7, "Verification Requested", "Owner submitted a private identifying detail for staff review (detail not stored in timeline).", "2026-09-16 10:20:00", "student6"),

        # Item 8 (Laptop Charger - Resolved)
        (8, "Report Created", "Liam O'Connor reported found 65W Dell Charger in Lab 1.", "2026-09-14 17:30:00", "student7"),
        (8, "Potential Match Detected", "Owner matched through serial number description.", "2026-09-15 10:15:00", ADMIN_USERNAME),
        (8, "Verification Requested", "Owner submitted a private identifying detail for staff review (detail not stored in timeline).", "2026-09-15 13:10:00", "student7"),
        (8, "Verification Completed", "Private detail confirmed. Ownership validated without exposing sensitive information.", "2026-09-15 13:45:00", "admin"),
        (8, "Case Resolved", "Item verified and handed over to owner. Case closed.", "2026-09-15 14:00:00", "admin"),

        # Item 9 (Earbuds - Resolved)
        (9, "Report Created", "Daniel Kim turned in found Wireless Earbuds in Seminar Hall.", "2026-09-13 16:45:00", "student9"),
        (9, "Verification Requested", "Owner submitted a private identifying detail for staff review (detail not stored in timeline).", "2026-09-14 10:45:00", "student9"),
        (9, "Verification Completed", "Private detail confirmed. Ownership validated without exposing sensitive information.", "2026-09-14 11:15:00", "admin"),
        (9, "Case Resolved", "Property returned successfully. Case closed.", "2026-09-14 11:30:00", "admin"),

        # Item 10 (Keys)
        (10, "Report Created", "Hannah Scott reported found Keyring with 3 Keys in Parking Lot.", "2026-09-17 08:20:00", "student10"),

        # Item 11 (Notebook)
        (11, "Report Created", "Priya Patel reported lost Engineering Graph Notebook in Lab 2.", "2026-09-16 15:40:00", "student2"),

        # Item 12 (USB Drive)
        (12, "Report Created", "Jordan Taylor reported found 64GB Kingston USB Drive in Library.", "2026-09-17 12:10:00", "student3"),

        # Item 13 (Scarf)
        (13, "Report Created", "Sophia Rodriguez reported lost Grey Knitted Scarf in Seminar Hall.", "2026-09-17 13:00:00", "student8"),

        # Item 14 (Glasses)
        (14, "Report Created", "Ethan Brown turned in Tortoise Optical Glasses found in Library.", "2026-09-15 14:30:00", "student11"),
        (14, "Verification Requested", "Owner submitted a private identifying detail for staff review (detail not stored in timeline).", "2026-09-16 11:00:00", "student11"),

        # Item 15 (Smartwatch)
        (15, "Report Created", "Alex Chen reported lost Fitness Smartwatch near Main Block gym.", "2026-09-16 18:20:00", "student1"),

        # Item 16 (TI-84)
        (16, "Report Created", "Chloe Wilson reported found TI-84 Graphing Calculator in Lab 3.", "2026-09-16 17:00:00", "student12"),
        (16, "Potential Match Detected", "Correlated with Case #2 in Lab 3.", "2026-09-16 17:10:00", "System Matching Engine")
    ]

    for item_id, event, desc, created_at, created_by in case_events_data:
        cur.execute(
            "INSERT INTO case_events (item_id, event, description, created_at, created_by) VALUES (?, ?, ?, ?, ?)",
            (item_id, event, desc, created_at, created_by)
        )

    conn.commit()
    conn.close()
    print("Database successfully seeded with realistic campus data!")

if __name__ == '__main__':
    seed_database()
