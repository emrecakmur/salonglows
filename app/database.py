import sqlite3
import os
import re
import hashlib
import random
from datetime import datetime, timedelta
from app.ai_engine import get_salon_ai_insights

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
        if self.is_pg:
            query_pg = query.replace("?", "%s")
            query_pg = query_pg.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
            query_pg = query_pg.replace("MIN(total_sessions, completed_sessions + 1)", "LEAST(total_sessions, completed_sessions + 1)")
            
            is_insert = query_pg.strip().upper().startswith("INSERT")
            if is_insert and "RETURNING" not in query_pg.upper():
                query_pg_ret = query_pg.strip() + " RETURNING id"
                try:
                    if params:
                        self.raw_cursor.execute(query_pg_ret, params)
                    else:
                        self.raw_cursor.execute(query_pg_ret)
                    res = self.raw_cursor.fetchone()
                    if res:
                        self.lastrowid = res[0]
                    return
                except Exception:
                    try:
                        self.conn.rollback()
                    except Exception:
                        pass
                    if params:
                        self.raw_cursor.execute(query_pg, params)
                    else:
                        self.raw_cursor.execute(query_pg)
                    return

            if params:
                self.raw_cursor.execute(query_pg, params)
            else:
                self.raw_cursor.execute(query_pg)
        else:
            if params is not None:
                self.raw_cursor.execute(query, params)
            else:
                self.raw_cursor.execute(query)
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
                for r in rows:
                    d = dict(zip(colnames, r))
                    res.append(DictRow(d, tuple(r)))
                return res
            return rows
        res = []
        for r in rows:
            d = dict(r)
            res.append(DictRow(d, tuple(d.values())))
        return res

    def close(self):
        self.raw_cursor.close()

def get_db():
    return DBConnection()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def slugify(text: str) -> str:
    text = text.lower().strip()
    tr_map = {'ç':'c', 'ğ':'g', 'ı':'i', 'i':'i', 'ö':'o', 'ş':'s', 'ü':'u'}
    for k, v in tr_map.items():
        text = text.replace(k, v)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Salons table
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
    
    # 2. Password Resets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            reset_code TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            is_used INTEGER DEFAULT 0
        )
    """)

    # 3. Staff table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salon_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            title TEXT NOT NULL,
            color TEXT DEFAULT '#ec4899'
        )
    """)

    # 4. Services table
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

    # 5. Appointments table
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

    # 6. Customer Packages table
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

    # 7. AI Ciro Motoru Yeni Tabloları
    # ai_opportunities
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salon_id INTEGER NOT NULL,
            customer_name TEXT,
            customer_phone TEXT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            potential_revenue REAL NOT NULL,
            priority TEXT DEFAULT 'orta',
            status TEXT DEFAULT 'OPEN',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # customer_scores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salon_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            visit_count INTEGER DEFAULT 1,
            avg_spend REAL DEFAULT 0,
            last_visit_date TEXT,
            visit_interval_days INTEGER DEFAULT 30,
            ltv_annual REAL DEFAULT 0,
            churn_risk TEXT DEFAULT 'düşük',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ai_recommendations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salon_id INTEGER NOT NULL,
            recommendation_type TEXT NOT NULL,
            target_customer TEXT,
            target_phone TEXT,
            suggested_action TEXT NOT NULL,
            potential_revenue REAL NOT NULL,
            priority TEXT DEFAULT 'orta',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # recovery_campaigns (Geri kazanım ve kampanya logları)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recovery_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salon_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            campaign_type TEXT NOT NULL,
            offer_details TEXT,
            message_text TEXT,
            message_sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_converted INTEGER DEFAULT 0,
            converted_amount REAL DEFAULT 0,
            converted_at TIMESTAMP
        )
    """)

    # revenue_attribution (Gerçekleşen Ciro Atıf Sistemi)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS revenue_attribution (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salon_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            campaign_type TEXT NOT NULL,
            attribution_type TEXT NOT NULL,
            actual_revenue REAL NOT NULL,
            appointment_id INTEGER,
            package_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    # Ensure created_at column exists in salons table
    try:
        cursor.execute("SELECT created_at FROM salons LIMIT 1")
    except Exception:
        conn.rollback()
        try:
            cursor.execute("ALTER TABLE salons ADD COLUMN created_at TEXT")
            conn.commit()
        except Exception:
            conn.rollback()
    
    # Seed default demo salon if empty or missing rich appointments
    try:
        cursor.execute("SELECT count(*) FROM salons")
        salon_cnt_row = cursor.fetchone()
        if not salon_cnt_row or salon_cnt_row[0] == 0:
            seed_demo_salon(cursor)
            conn.commit()
        else:
            # Check if demo salon has rich historical appointments
            cursor.execute("SELECT count(*) FROM appointments WHERE salon_id = ? AND customer_name LIKE ?", (1, '%Ayşe Yılmaz%'))
            app_cnt_row = cursor.fetchone()
            if app_cnt_row and app_cnt_row[0] == 0:
                enrich_demo_salon(cursor, salon_id=1)
                try:
                    cursor.execute("UPDATE customer_packages SET completed_sessions = 7 WHERE salon_id = 1")
                except Exception:
                    pass
                conn.commit()
    except Exception:
        conn.rollback()

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
        (salon_id, 'Protez Tırnak & Kalıcı Oje', 60, 850.0, 'Tırnak & Manikür'),
        (salon_id, 'Medikal Pedikür & Spa', 45, 750.0, 'Tır
