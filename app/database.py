import sqlite3
import os
import re
import hashlib
import random
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salonn_app.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def tr_slugify(text):
    if not text:
        return "salon"
    text = text.lower()
    mapping = {
        'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
        'İ': 'i', 'I': 'i', 'Ğ': 'g', 'Ü': 'u', 'Ş': 's', 'Ö': 'o', 'Ç': 'c'
    }
    for k, v in mapping.items():
        text = text.replace(k, v)
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text or "salon"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Salons table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS salons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            owner_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            phone TEXT NOT NULL,
            city TEXT NOT NULL,
            subscription_plan TEXT DEFAULT 'Aylık PRO Salon Paketi',
            subscription_status TEXT DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Password Resets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            reset_code TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            is_used INTEGER DEFAULT 0
        )
    """)

    # Staff table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salon_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            title TEXT NOT NULL,
            color TEXT DEFAULT '#ec4899'
        )
    """)

    # Services table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salon_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            duration_minutes INTEGER DEFAULT 45,
            price REAL NOT NULL,
            category TEXT NOT NULL
        )
    """)

    # Appointments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salon_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            staff_name TEXT NOT NULL,
            service_name TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            price REAL NOT NULL,
            status TEXT DEFAULT 'APPROVED',
            wa_sent INTEGER DEFAULT 1,
            notes TEXT
        )
    """)

    # Customer Packages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salon_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            package_name TEXT NOT NULL,
            total_sessions INTEGER NOT NULL,
            completed_sessions INTEGER DEFAULT 0,
            total_price REAL NOT NULL,
            paid_amount REAL NOT NULL,
            created_at TEXT
        )
    """)

    conn.commit()
    
    # Seed default demo salon if empty
    cursor.execute("SELECT count(*) FROM salons")
    if cursor.fetchone()[0] == 0:
        seed_demo_salon(cursor)
        conn.commit()

    conn.close()

def seed_demo_salon(cursor):
    pass_hash = hash_password("123456")
    cursor.execute("""
        INSERT INTO salons (name, slug, owner_name, email, password_hash, phone, city, subscription_plan, subscription_status)
        VALUES ('Glamour Güzellik Salonu', 'glamour-guzellik', 'Zeynep Yılmaz', 'demo@glamour.com', ?, '0532 555 1234', 'İstanbul / Kadıköy', 'Aylık PRO Salon Paketi', 'ACTIVE')
    """, (pass_hash,))
    salon_id = cursor.lastrowid

    # Staff
    staff_members = [
        (salon_id, 'Ayşe Uzun', 'Güzellik Uzmanı & Estetisyen', '#ec4899'),
        (salon_id, 'Merve Kaya', 'Lazer & Cilt Bakım Uzmanı', '#8b5cf6'),
        (salon_id, 'Mehmet Can', 'Kıdemli Kuaför & Saç Tasarım', '#3b82f6'),
        (salon_id, 'Zeynep Hanım', 'Protez Tırnak & Manikür Uzmanı', '#10b981')
    ]
    cursor.executemany("INSERT INTO staff (salon_id, name, title, color) VALUES (?, ?, ?, ?)", staff_members)

    # Services
    services = [
        (salon_id, 'Hydrafacial Derin Cilt Bakımı', 60, 1200.0, 'Cilt Bakımı'),
        (salon_id, 'Buz Lazer Epilasyon (Tüm Vücut)', 45, 1800.0, 'Lazer Epilasyon'),
        (salon_id, 'Profesyonel Saç Kesim & Fön', 45, 650.0, 'Saç Tasarım'),
        (salon_id, 'Protez Tırnak & Kalıcı Oje', 60, 850.0, 'Tırnak & Manikür')
    ]
    cursor.executemany("INSERT INTO services (salon_id, name, duration_minutes, price, category) VALUES (?, ?, ?, ?, ?)", services)

    # Demo Appointments
    today_str = datetime.now().strftime("%Y-%m-%d")
    demo_apps = [
        (salon_id, 'Selin Demir', '0533 111 2233', 'Ayşe Uzun', 'Hydrafacial Derin Cilt Bakımı', today_str, '10:00', 1200.0, 'APPROVED', 1, 'Hassas cilt, maske uygulandı.'),
        (salon_id, 'Elif Kaya', '0544 222 3344', 'Merve Kaya', 'Buz Lazer Epilasyon (Tüm Vücut)', today_str, '11:30', 1800.0, 'APPROVED', 1, '4. Seans uygulaması yapıldı.')
    ]
    cursor.executemany("""
        INSERT INTO appointments (salon_id, customer_name, customer_phone, staff_name, service_name, appointment_date, appointment_time, price, status, wa_sent, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, demo_apps)

    # Demo Packages
    demo_packages = [
        (salon_id, 'Elif Kaya', '0544 222 3344', '8 Seans Buz Lazer Paketi', 8, 4, 9600.0, 9600.0, '2026-08-15')
    ]
    cursor.executemany("""
        INSERT INTO customer_packages (salon_id, customer_name, customer_phone, package_name, total_sessions, completed_sessions, total_price, paid_amount, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, demo_packages)

def register_new_salon(name, owner_name, email, password, phone, city):
    conn = get_db()
    cursor = conn.cursor()
    
    base_slug = tr_slugify(name)
    slug = base_slug
    counter = 1
    while True:
        cursor.execute("SELECT id FROM salons WHERE slug = ?", (slug,))
        if not cursor.fetchone():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
        
    pass_hash = hash_password(password)
    
    cursor.execute("""
        INSERT INTO salons (name, slug, owner_name, email, password_hash, phone, city, subscription_plan, subscription_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Aylık PRO Salon Paketi (14 Gün Deneme)', 'ACTIVE')
    """, (name, slug, owner_name, email, pass_hash, phone, city))
    salon_id = cursor.lastrowid
    
    # Add starter staff for new salon
    starter_staff = [
        (salon_id, owner_name, 'Baş Uzman & Kurucu', '#ec4899'),
        (salon_id, 'Yardımcı Uzman', 'Güzellik & Estetik Uzmanı', '#8b5cf6')
    ]
    cursor.executemany("INSERT INTO staff (salon_id, name, title, color) VALUES (?, ?, ?, ?)", starter_staff)
    
    # Add starter services for new salon
    starter_services = [
        (salon_id, 'Cilt Bakımı & Maske', 60, 1000.0, 'Cilt Bakımı'),
        (salon_id, 'Lazer Epilasyon Seansı', 45, 1500.0, 'Lazer Epilasyon'),
        (salon_id, 'Profesyonel Saç Kesim', 45, 500.0, 'Saç Tasarım'),
        (salon_id, 'Manikür & Pedikür', 45, 600.0, 'El & Ayak')
    ]
    cursor.executemany("INSERT INTO services (salon_id, name, duration_minutes, price, category) VALUES (?, ?, ?, ?, ?)", starter_services)
    
    conn.commit()
    conn.close()
    
    return salon_id, slug

def authenticate_salon(email, password):
    conn = get_db()
    cursor = conn.cursor()
    pass_hash = hash_password(password)
    cursor.execute("SELECT * FROM salons WHERE email = ? AND password_hash = ?", (email, pass_hash))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_password_reset_code(email):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM salons WHERE email = ?", (email,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None  # Email not registered
        
    code = f"{random.randint(100000, 999999)}"
    expires_at = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO password_resets (email, reset_code, expires_at, is_used)
        VALUES (?, ?, ?, 0)
    """, (email, code, expires_at))
    conn.commit()
    conn.close()
    return code

def verify_and_reset_password(email, code, new_password):
    conn = get_db()
    cursor = conn.cursor()
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        SELECT id FROM password_resets 
        WHERE email = ? AND reset_code = ? AND is_used = 0 AND expires_at > ?
        ORDER BY id DESC LIMIT 1
    """, (email, code, now_str))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
        
    reset_id = row[0]
    new_pass_hash = hash_password(new_password)
    
    # Update salon password
    cursor.execute("UPDATE salons SET password_hash = ? WHERE email = ?", (new_pass_hash, email))
    # Mark reset code as used
    cursor.execute("UPDATE password_resets SET is_used = 1 WHERE id = ?", (reset_id,))
    
    conn.commit()
    conn.close()
    return True

def get_salon_dashboard_data(salon_id):
    conn = get_db()
    cursor = conn.cursor()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute("SELECT * FROM salons WHERE id = ?", (salon_id,))
    salon_row = cursor.fetchone()
    if not salon_row:
        conn.close()
        return None
    salon = dict(salon_row)
    
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(price), 0) FROM appointments WHERE salon_id = ? AND appointment_date = ?", (salon_id, today_str))
    row = cursor.fetchone()
    today_count = row[0]
    today_revenue = row[1]
    
    cursor.execute("SELECT COUNT(DISTINCT customer_phone) FROM appointments WHERE salon_id = ?", (salon_id,))
    total_customers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM customer_packages WHERE salon_id = ? AND completed_sessions < total_sessions", (salon_id,))
    active_packages_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT * FROM appointments WHERE salon_id = ? AND appointment_date = ? ORDER BY appointment_time ASC", (salon_id, today_str))
    today_appointments = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM staff WHERE salon_id = ?", (salon_id,))
    staff = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM services WHERE salon_id = ?", (salon_id,))
    services = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM customer_packages WHERE salon_id = ? ORDER BY id DESC", (salon_id,))
    packages = [dict(r) for r in cursor.fetchall()]

    conn.close()
    
    return {
        "today_count": today_count,
        "today_revenue": today_revenue,
        "total_customers": total_customers,
        "active_packages_count": active_packages_count,
        "today_appointments": today_appointments,
        "staff": staff,
        "services": services,
        "packages": packages,
        "salon": salon
    }

def add_new_appointment(salon_id, customer_name, customer_phone, staff_name, service_name, appointment_date, appointment_time, price, notes=""):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO appointments (salon_id, customer_name, customer_phone, staff_name, service_name, appointment_date, appointment_time, price, status, wa_sent, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'APPROVED', 1, ?)
    """, (salon_id, customer_name, customer_phone, staff_name, service_name, appointment_date, appointment_time, price, notes))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def add_new_package(salon_id, customer_name, customer_phone, package_name, total_sessions, total_price, paid_amount):
    conn = get_db()
    cursor = conn.cursor()
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        INSERT INTO customer_packages (salon_id, customer_name, customer_phone, package_name, total_sessions, completed_sessions, total_price, paid_amount, created_at)
        VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
    """, (salon_id, customer_name, customer_phone, package_name, total_sessions, total_price, paid_amount, today_str))
    conn.commit()
    conn.close()

def increment_package_session(package_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE customer_packages SET completed_sessions = MIN(total_sessions, completed_sessions + 1) WHERE id = ?", (package_id,))
    conn.commit()
    conn.close()

def add_staff_member(salon_id, name, title, color='#ec4899'):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO staff (salon_id, name, title, color) VALUES (?, ?, ?, ?)", (salon_id, name, title, color))
    conn.commit()
    conn.close()

def add_service_item(salon_id, name, duration_minutes, price, category="Genel"):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO services (salon_id, name, duration_minutes, price, category) VALUES (?, ?, ?, ?, ?)", (salon_id, name, duration_minutes, price, category))
    conn.commit()
    conn.close()
