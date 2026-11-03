"""database.py - all SQLite code lives here (tables, queries, reports)."""
import sqlite3
import hashlib
from datetime import datetime

DB_NAME = "campus.db"


def connect():
    return sqlite3.connect(DB_NAME)


def hash_password(password):
    """Store a hash of the password, never the plain text."""
    return hashlib.sha256(password.encode()).hexdigest()


def create_tables():
    conn = connect()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS campuses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL,
                    campus_id INTEGER)""")
    # UNIQUE on code stops duplicate resources
    c.execute("""CREATE TABLE IF NOT EXISTS resources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    campus_id INTEGER NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_id INTEGER NOT NULL,
                    lecturer_id INTEGER NOT NULL,
                    campus_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    start_hour INTEGER NOT NULL,
                    duration INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active')""")
    conn.commit()
    conn.close()


def seed_data():
    """Add starting campuses, admins, an operator and some resources (only once)."""
    conn = connect()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM campuses").fetchone()[0] > 0:
        conn.close()
        return
    campuses = [("Johannesburg", "jhb"), ("Durban", "dbn"), ("Cape Town", "cpt")]
    for name, short in campuses:
        c.execute("INSERT INTO campuses (name) VALUES (?)", (name,))
        campus_id = c.lastrowid
        c.execute("INSERT INTO users (username, password, role, campus_id) VALUES (?,?,?,?)",
                  ("admin_" + short, hash_password("admin123"), "admin", campus_id))
        c.execute("INSERT INTO resources (code, name, campus_id) VALUES (?,?,?)",
                  (short.upper() + "-LAB1", "Computer Lab 1", campus_id))
        c.execute("INSERT INTO resources (code, name, campus_id) VALUES (?,?,?)",
                  (short.upper() + "-PROJ1", "Multimedia Projector", campus_id))
        c.execute("INSERT INTO resources (code, name, campus_id) VALUES (?,?,?)",
                  (short.upper() + "-SEM1", "Seminar Room", campus_id))
    c.execute("INSERT INTO users (username, password, role, campus_id) VALUES (?,?,?,?)",
              ("operator", hash_password("oper123"), "operator", None))
    conn.commit()
    conn.close()


# ---------- users ----------
def add_user(username, password, role, campus_id=None):
    """Returns True if saved, False if the username already exists."""
    conn = connect()
    try:
        conn.execute("INSERT INTO users (username, password, role, campus_id) VALUES (?,?,?,?)",
                     (username, hash_password(password), role, campus_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def check_login(username, password):
    """Returns (id, username, role, campus_id) or None."""
    conn = connect()
    row = conn.execute("SELECT id, username, role, campus_id FROM users "
                       "WHERE username=? AND password=?",
                       (username, hash_password(password))).fetchone()
    conn.close()
    return row


# ---------- campuses ----------
def get_campuses():
    conn = connect()
    rows = conn.execute("SELECT id, name FROM campuses ORDER BY name").fetchall()
    conn.close()
    return rows


# ---------- resources ----------
def get_resources(campus_id):
    conn = connect()
    rows = conn.execute("SELECT id, code, name FROM resources WHERE campus_id=? ORDER BY code",
                        (campus_id,)).fetchall()
    conn.close()
    return rows


def get_all_resources():
    conn = connect()
    rows = conn.execute("SELECT r.id, c.name, r.code, r.name FROM resources r "
                        "JOIN campuses c ON r.campus_id = c.id ORDER BY c.name, r.code").fetchall()
    conn.close()
    return rows


def add_resource(code, name, campus_id):
    """Returns False if a resource with this code already exists."""
    conn = connect()
    try:
        conn.execute("INSERT INTO resources (code, name, campus_id) VALUES (?,?,?)",
                     (code, name, campus_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_resource(resource_id, new_name):
    conn = connect()
    conn.execute("UPDATE resources SET name=? WHERE id=?", (new_name, resource_id))
    conn.commit()
    conn.close()


def has_future_bookings(resource_id):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = connect()
    count = conn.execute("SELECT COUNT(*) FROM bookings WHERE resource_id=? "
                         "AND status='active' AND date>=?", (resource_id, today)).fetchone()[0]
    conn.close()
    return count > 0


def delete_resource(resource_id):
    conn = connect()
    conn.execute("DELETE FROM resources WHERE id=?", (resource_id,))
    conn.commit()
    conn.close()


def is_in_use_now(resource_id):
    now = datetime.now()
    conn = connect()
    count = conn.execute("SELECT COUNT(*) FROM bookings WHERE resource_id=? AND status='active' "
                         "AND date=? AND start_hour<=? AND start_hour+duration>?",
                         (resource_id, now.strftime("%Y-%m-%d"), now.hour, now.hour)).fetchone()[0]
    conn.close()
    return count > 0


# ---------- bookings ----------
def has_overlap(resource_id, date, start, duration):
    """True if an active booking for this resource overlaps the requested time."""
    end = start + duration
    conn = connect()
    count = conn.execute("SELECT COUNT(*) FROM bookings WHERE resource_id=? AND date=? "
                         "AND status='active' AND start_hour<? AND start_hour+duration>?",
                         (resource_id, date, end, start)).fetchone()[0]
    conn.close()
    return count > 0


def add_booking(resource_id, lecturer_id, campus_id, date, start, duration):
    conn = connect()
    conn.execute("INSERT INTO bookings (resource_id, lecturer_id, campus_id, date, start_hour, duration) "
                 "VALUES (?,?,?,?,?,?)", (resource_id, lecturer_id, campus_id, date, start, duration))
    conn.commit()
    conn.close()


def cancel_booking(booking_id):
    conn = connect()
    conn.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (booking_id,))
    conn.commit()
    conn.close()


def get_bookings(campus_id=None, lecturer_id=None):
    """Rows: (id, resource, campus, lecturer, date, start, duration, status)."""
    sql = ("SELECT b.id, r.name, c.name, u.username, b.date, b.start_hour, b.duration, b.status "
           "FROM bookings b JOIN resources r ON b.resource_id=r.id "
           "JOIN campuses c ON b.campus_id=c.id JOIN users u ON b.lecturer_id=u.id")
    params = []
    if campus_id is not None:
        sql += " WHERE b.campus_id=?"
        params.append(campus_id)
    elif lecturer_id is not None:
        sql += " WHERE b.lecturer_id=?"
        params.append(lecturer_id)
    sql += " ORDER BY b.date DESC, b.start_hour DESC"
    conn = connect()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


# ---------- reports ----------
def campus_report(campus_id):
    """Returns a dictionary with the report figures for one campus."""
    conn = connect()
    total = conn.execute("SELECT COUNT(*) FROM bookings WHERE campus_id=? AND status='active'",
                         (campus_id,)).fetchone()[0]
    avg = conn.execute("SELECT AVG(duration) FROM bookings WHERE campus_id=? AND status='active'",
                       (campus_id,)).fetchone()[0]
    top = conn.execute("SELECT r.name, COUNT(*) AS n FROM bookings b JOIN resources r "
                       "ON b.resource_id=r.id WHERE b.campus_id=? AND b.status='active' "
                       "GROUP BY r.name ORDER BY n DESC LIMIT 3", (campus_id,)).fetchall()
    months = conn.execute("SELECT substr(date,1,7), COUNT(*) FROM bookings WHERE campus_id=? "
                          "AND status='active' GROUP BY substr(date,1,7) ORDER BY 1",
                          (campus_id,)).fetchall()
    conn.close()
    return {"total": total, "average": avg or 0, "top": top, "months": months}
