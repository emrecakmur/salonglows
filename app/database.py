import sqlite3
import os
import re
import hashlib
import random
from datetime import datetime, timedelta

DATABASE_URL = os.environ.get("DATABASE_URL")

class DictRow(dict):
    def __init__(self, data_dict, tuple_data=None):
        super().__init__(data_dict)
        self._tuple = tuple_data if tuple_data is not None else tuple(data_dict.values())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._tuple[key]
        return super().__getitem__(key)

class DBConnection:
    def __init__(self):
        self.is_pg = bool(DATABASE_URL)
        if self.is_pg:
            import psycopg2
            pg_url = DATABASE_URL
            if pg_url.startswith("postgres://"):
                pg_url = pg_url.replace("postgres://", "postgresql://", 1)
            self.conn = psycopg2.connect(pg_url)
        else:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salonn_app.db")
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row

    def cursor(self):
        return DBCursor(self.conn, self.is_pg)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        try:
            self.conn.rollback()
        except Exception:
            pass

    def close(self):
        self.conn.close()

class DBCursor:
    def __init__(self, conn, is_pg):
        self.conn = conn
        self.is_pg = is_pg
        self.raw_cursor = conn.cursor()
        self.lastrowid = None

    def execute(self, query, params=None):
        params = params or ()
        if self.is_pg:
            query_pg = query.replace("?", "%s")
            query_pg = query_pg.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
            query_pg = query_pg.replace("MIN(total_sessions, completed_sessions + 1)", "LEAST(total_sessions, completed_sessions + 1)")
            
            is_insert = query_pg.strip().upper().startswith("INSERT")
            if is_insert and "RETURNING" not in query_pg.upper():
                query_pg_ret = query_pg.strip() + " RETURNING id"
                try:
                    self.raw_cursor.execute(query_pg_ret, params)
                    res = self.raw_cursor.fetchone()
                    if res:
                        self.lastrowid = res[0]
                    return
                except Exception:
                    try:
                        self.conn.rollback()
                    except Exception:
                        pass
                    self.raw_cursor.execute(query_pg, params)
                    return

            self.raw_cursor.execute(query_pg, params)
        else:
            self.raw_cursor.execute(query, params)
            self.lastrowid = self.raw_cursor.lastrowid

    def executemany(self, query, params_list):
        if self.is_pg:
            query_pg = query.replace("?", "%s")
            self.raw_cursor.executemany(query_pg, params_list)
        else:
            self.raw_cursor.executemany(query, params_list)

    def fetchone(self):
        row = self.raw_cursor.fetchone()
        if not row:
            return None
        if self.is_pg:
            if hasattr(self.raw_cursor, 'description') and self.raw_cursor.description:
                colnames = [desc[0] for desc in self.raw_cursor.description]
                d = dict(zip(colnames, row))
                return DictRow(d, tuple(row))
            return row
        d = dict(row)
        return DictRow(d, tuple(d.values()))

    def fetchall(self):
        rows = self.raw_cursor.fetchall()
        if not rows:
            return []
        if self.is_pg:
            if hasattr(self.raw_cursor, 'description') and self.raw_cursor.description:
                colnames = [desc[0] for desc in self.raw_cursor.description]
                res = []
                for row in rows:
                    d = dict(zip(colnames, row))
                    res.append(DictRow(d, tuple(row)))
                return res
            return rows
        res = []
        for r in rows:
            d = dict(r)
            res.append(DictRow(d, tuple(d.values())))
        return res

def get_db():
    return DBConnection()

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
            google_maps_url TEXT,
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
            category TEXT NOT NULL,
            is_flash_deal INTEGER DEFAULT 0,
            discount_percent INTEGER DEFAULT 0
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

    # Ensure created_at column exists in salons table
    try:
        cursor.execute("ALTER TABLE salons ADD COLUMN created_at TEXT")
        conn.commit()
    except Exception:
        conn.rollback()
    
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
        VALUES ('Glamour Güzellik Salonu', 'glamour-guzellik', 'Zeynep Yılmaz', 'demo@glamour.com', ?, '0532 555 1234', 'İstanbul / Kadıköy', '3 Günlük PRO Deneme Paketi', 'ACTIVE')
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
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO salons (name, slug, owner_name, email, password_hash, phone, city, subscription_plan, subscription_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, '3 Günlük PRO Deneme Paketi', 'ACTIVE', ?)
    """, (name, slug, owner_name, email, pass_hash, phone, city, now_str))
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

def get_salon_dashboard_data(salon_id, target_date=None):
    conn = get_db()
    cursor = conn.cursor()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    selected_date = target_date if target_date else today_str

    try:
        dt = datetime.strptime(selected_date, "%Y-%m-%d")
    except Exception:
        dt = datetime.now()
        selected_date = today_str

    yesterday_date = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow_date = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
    
    cursor.execute("SELECT * FROM salons WHERE id = ?", (salon_id,))
    salon_row = cursor.fetchone()
    if not salon_row:
        conn.close()
        return None
    salon = dict(salon_row)
    
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(price), 0) FROM appointments WHERE salon_id = ? AND appointment_date = ?", (salon_id, selected_date))
    row = cursor.fetchone()
    today_count = row[0]
    today_revenue = row[1]
    
    cursor.execute("SELECT COUNT(DISTINCT customer_phone) FROM appointments WHERE salon_id = ?", (salon_id,))
    total_customers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM customer_packages WHERE salon_id = ? AND completed_sessions < total_sessions", (salon_id,))
    active_packages_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT * FROM appointments WHERE salon_id = ? AND appointment_date = ? ORDER BY appointment_time ASC", (salon_id, selected_date))
    today_appointments = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM staff WHERE salon_id = ?", (salon_id,))
    staff = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM services WHERE salon_id = ?", (salon_id,))
    services = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM customer_packages WHERE salon_id = ? ORDER BY id DESC", (salon_id,))
    packages = [dict(r) for r in cursor.fetchall()]

    # Detect inactive/lost customers (who last visited 20+ days ago)
    cutoff_date = (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d")
    try:
        cursor.execute("""
            SELECT MAX(customer_name) as customer_name, customer_phone, MAX(appointment_date) as last_date, COUNT(*) as visit_count
            FROM appointments
            WHERE salon_id = ?
            GROUP BY customer_phone
            HAVING MAX(appointment_date) <= ?
            ORDER BY last_date ASC
            LIMIT 10
        """, (salon_id, cutoff_date))
        lost_customers = [dict(r) for r in cursor.fetchall()]
    except Exception:
        conn.rollback()
        lost_customers = []

    if not lost_customers:
        lost_customers = [
            {"customer_name": "Selin Demir", "customer_phone": "0533 111 2233", "last_date": "2026-08-10", "visit_count": 3},
            {"customer_name": "Elif Kaya", "customer_phone": "0544 222 3344", "last_date": "2026-08-01", "visit_count": 5},
            {"customer_name": "Deniz Arslan", "customer_phone": "0555 333 4455", "last_date": "2026-07-25", "visit_count": 2}
        ]

    birthday_customers = [
        {"customer_name": "Zeynep Yılmaz", "customer_phone": "0532 555 1234", "birth_date": "25 Eylül (Bugün 🥳)", "suggested_gift": "%25 İndirimli Fön & Cilt Bakımı"},
        {"customer_name": "Merve Öztürk", "customer_phone": "0542 333 4455", "birth_date": "28 Eylül", "suggested_gift": "%20 İndirimli Lazer Seansı"},
        {"customer_name": "Büşra Yıldız", "customer_phone": "0535 777 8899", "birth_date": "30 Eylül", "suggested_gift": "Hediye Manikür & Kalıcı Oje"}
    ]

    conn.close()

    # Check 3-day (72-hour) trial expiration
    created_at_str = salon.get('created_at')
    is_expired = False
    days_left = 3
    hours_left = 0
    total_hours_left = 72

    if created_at_str and 'Deneme' in salon.get('subscription_plan', '') and not str(created_at_str).startswith('2099'):
        try:
            created_dt = datetime.strptime(str(created_at_str).split('.')[0], "%Y-%m-%d %H:%M:%S")
            elapsed_seconds = (datetime.now() - created_dt).total_seconds()
            total_seconds_left = max(0, 259200 - elapsed_seconds)
            total_hours_left = int(total_seconds_left / 3600)
            days_left = int(total_hours_left / 24)
            hours_left = total_hours_left % 24
            if elapsed_seconds >= 259200:
                is_expired = True
        except Exception:
            pass
    
    return {
        "selected_date": selected_date,
        "yesterday_date": yesterday_date,
        "tomorrow_date": tomorrow_date,
        "today_date": today_str,
        "today_count": today_count,
        "today_revenue": today_revenue,
        "total_customers": total_customers,
        "active_packages_count": active_packages_count,
        "today_appointments": today_appointments,
        "lost_customers": lost_customers,
        "birthday_customers": birthday_customers,
        "staff": staff,
        "services": services,
        "packages": packages,
        "salon": salon,
        "is_expired": is_expired,
        "days_left": days_left,
        "hours_left": hours_left,
        "total_hours_left": total_hours_left
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

def delete_appointment(appointment_id, salon_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE id = ? AND salon_id = ?", (appointment_id, salon_id))
    conn.commit()
    conn.close()

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

def delete_customer_package(package_id, salon_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM customer_packages WHERE id = ? AND salon_id = ?", (package_id, salon_id))
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

def delete_service_item(service_id, salon_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM services WHERE id = ? AND salon_id = ?", (service_id, salon_id))
    conn.commit()
    conn.close()

def update_service_item(service_id, salon_id, name, duration_minutes, price):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE services 
        SET name = ?, duration_minutes = ?, price = ? 
        WHERE id = ? AND salon_id = ?
    """, (name, duration_minutes, price, service_id, salon_id))
    conn.commit()
    conn.close()

# SUPER ADMIN DATABASE FUNCTIONS
def get_all_salons_admin():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, 
               (SELECT COUNT(*) FROM appointments WHERE salon_id = s.id) as total_appointments,
               (SELECT COUNT(*) FROM customer_packages WHERE salon_id = s.id) as total_packages
        FROM salons s
        ORDER BY s.id DESC
    """)
    salons = [dict(r) for r in cursor.fetchall()]
    
    for s in salons:
        created_at_str = s.get('created_at')
        is_expired = False
        is_new_user = False
        days_left = 3
        hours_left = 0
        total_hours_left = 72
        if created_at_str and not str(created_at_str).startswith('2099'):
            try:
                created_dt = datetime.strptime(str(created_at_str).split('.')[0], "%Y-%m-%d %H:%M:%S")
                elapsed_seconds = (datetime.now() - created_dt).total_seconds()
                total_seconds_left = max(0, 259200 - elapsed_seconds)
                total_hours_left = int(total_seconds_left / 3600)
                days_left = int(total_hours_left / 24)
                hours_left = total_hours_left % 24
                if elapsed_seconds <= 172800:  # 48 hours
                    is_new_user = True
                if 'Deneme' in s.get('subscription_plan', '') and elapsed_seconds >= 259200:
                    is_expired = True
            except Exception:
                pass
        s['is_expired'] = is_expired
        s['is_new_user'] = is_new_user
        s['days_left'] = days_left
        s['hours_left'] = hours_left
        s['total_hours_left'] = total_hours_left
        
    conn.close()
    return salons

def update_salon_subscription(salon_id, new_plan):
    conn = get_db()
    cursor = conn.cursor()
    
    # Safely ensure created_at column exists if older DB schema
    try:
        cursor.execute("ALTER TABLE salons ADD COLUMN created_at TEXT")
        conn.commit()
    except Exception:
        conn.rollback()

    if 'Deneme' in new_plan:
        created_at_val = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        created_at_val = '2099-01-01 00:00:00'

    cursor.execute("""
        UPDATE salons 
        SET subscription_plan = ?, subscription_status = 'ACTIVE', created_at = ? 
        WHERE id = ?
    """, (new_plan, created_at_val, salon_id))
    conn.commit()
    conn.close()

def delete_salon_admin(salon_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE salon_id = ?", (salon_id,))
    cursor.execute("DELETE FROM customer_packages WHERE salon_id = ?", (salon_id,))
    cursor.execute("DELETE FROM staff WHERE salon_id = ?", (salon_id,))
    cursor.execute("DELETE FROM services WHERE salon_id = ?", (salon_id,))
    cursor.execute("DELETE FROM salons WHERE id = ?", (salon_id,))
    conn.commit()
    conn.close()

def update_salon_google_maps(salon_id, maps_url):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE salons ADD COLUMN google_maps_url TEXT")
        conn.commit()
    except Exception:
        conn.rollback()
    cursor.execute("UPDATE salons SET google_maps_url = ? WHERE id = ?", (maps_url, salon_id))
    conn.commit()
    conn.close()

def toggle_service_flash_deal(service_id, salon_id, is_flash_deal: bool, discount_percent: int = 20):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE services ADD COLUMN is_flash_deal INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        conn.rollback()

    try:
        cursor.execute("ALTER TABLE services ADD COLUMN discount_percent INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        conn.rollback()

    cursor.execute("UPDATE services SET is_flash_deal = ?, discount_percent = ? WHERE id = ? AND salon_id = ?", (1 if is_flash_deal else 0, discount_percent, service_id, salon_id))
    conn.commit()
    conn.close()
