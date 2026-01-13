import sqlite3
from datetime import datetime

DB_NAME = "bot_database.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Admins table
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY,
        username TEXT,
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Keywords table
    c.execute('''CREATE TABLE IF NOT EXISTS keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        keyword TEXT,
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Private groups table (where results are sent)
    c.execute('''CREATE TABLE IF NOT EXISTS private_groups (
        admin_id INTEGER PRIMARY KEY,
        group_id INTEGER,
        group_name TEXT,
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Search groups table (where userbot looks for keywords)
    c.execute('''CREATE TABLE IF NOT EXISTS search_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        group_id INTEGER,
        group_name TEXT,
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Settings table
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # Userbot APIs table (optional but good for management)
    c.execute('''CREATE TABLE IF NOT EXISTS userbot_apis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_id INTEGER,
        api_hash TEXT,
        phone TEXT,
        session_string TEXT,
        is_active INTEGER DEFAULT 1,
        last_check DATETIME
    )''')
    
    conn.commit()
    conn.close()

# Admin functions
def add_admin(admin_id, username):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO admins (id, username) VALUES (?, ?)", (admin_id, username))
    conn.commit()
    conn.close()

def remove_admin(admin_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE id = ?", (admin_id,))
    c.execute("DELETE FROM keywords WHERE admin_id = ?", (admin_id,))
    c.execute("DELETE FROM private_groups WHERE admin_id = ?", (admin_id,))
    c.execute("DELETE FROM search_groups WHERE admin_id = ?", (admin_id,))
    conn.commit()
    conn.close()

def is_admin(user_id, super_admin_id):
    if user_id == super_admin_id:
        return True
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM admins WHERE id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def get_all_admins():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username FROM admins")
    admins = [(row['id'], row['username']) for row in c.fetchall()]
    conn.close()
    return admins

# Keyword functions
def add_keyword(admin_id, keyword):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO keywords (admin_id, keyword) VALUES (?, ?)", (admin_id, keyword))
    conn.commit()
    conn.close()

def get_keywords(admin_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, keyword FROM keywords WHERE admin_id = ?", (admin_id,))
    keywords = [(row['id'], row['keyword']) for row in c.fetchall()]
    conn.close()
    return keywords

def remove_keyword(keyword_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))
    conn.commit()
    conn.close()

# Private group functions
def set_private_group(admin_id, group_id, group_name):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO private_groups (admin_id, group_id, group_name) VALUES (?, ?, ?)", 
              (admin_id, group_id, group_name))
    conn.commit()
    conn.close()

def get_private_group(admin_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT group_id, group_name FROM private_groups WHERE admin_id = ?", (admin_id,))
    result = c.fetchone()
    conn.close()
    return result

def remove_private_group(admin_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM private_groups WHERE admin_id = ?", (admin_id,))
    conn.commit()
    conn.close()

# Search group functions
def add_search_group(admin_id, group_id, group_name):
    conn = get_db()
    c = conn.cursor()
    # Check rate limit: 1 group per hour for normal admins
    # (Super admin check should be done in bot.py)
    c.execute("INSERT INTO search_groups (admin_id, group_id, group_name) VALUES (?, ?, ?)", 
              (admin_id, group_id, group_name))
    conn.commit()
    conn.close()

def get_last_search_group_time(admin_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT added_at FROM search_groups WHERE admin_id = ? ORDER BY added_at DESC LIMIT 1", (admin_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return datetime.strptime(result['added_at'], '%Y-%m-%d %H:%M:%S')
    return None

def get_search_groups(admin_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, group_id, group_name FROM search_groups WHERE admin_id = ?", (admin_id,))
    groups = [(row['id'], row['group_id'], row['group_name']) for row in c.fetchall()]
    conn.close()
    return groups

def remove_search_group(group_id_in_db):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM search_groups WHERE id = ?", (group_id_in_db,))
    conn.commit()
    conn.close()

# Settings functions
def get_setting(key, default=None):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    return result['value'] if result else default

def set_setting(key, value):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# Core logic function
def check_keywords_in_message(group_id, message_text):
    conn = get_db()
    c = conn.cursor()
    # Find all keywords for admins who are monitoring this group
    c.execute("""
        SELECT k.keyword, k.admin_id, p.group_id as private_group_id
        FROM keywords k
        JOIN search_groups s ON k.admin_id = s.admin_id
        LEFT JOIN private_groups p ON k.admin_id = p.admin_id
        WHERE s.group_id = ?
    """, (group_id,))
    
    matches = []
    message_lower = message_text.lower()
    
    for row in c.fetchall():
        if row['keyword'].lower() in message_lower:
            matches.append({
                'keyword': row['keyword'],
                'admin_id': row['admin_id'],
                'private_group_id': row['private_group_id']
            })
    
    conn.close()
    return matches
