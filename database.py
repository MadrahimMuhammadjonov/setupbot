# database.py - Database boshqaruvi
import sqlite3
from datetime import datetime

DB_NAME = 'userbot.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        admin_id INTEGER PRIMARY KEY,
        username TEXT,
        added_date TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        keyword TEXT,
        FOREIGN KEY (admin_id) REFERENCES admins(admin_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS search_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        group_id INTEGER,
        group_link TEXT,
        group_name TEXT,
        FOREIGN KEY (admin_id) REFERENCES admins(admin_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS private_groups (
        admin_id INTEGER PRIMARY KEY,
        group_id INTEGER,
        group_link TEXT,
        group_name TEXT,
        FOREIGN KEY (admin_id) REFERENCES admins(admin_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS userbot_apis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_id INTEGER,
        api_hash TEXT,
        phone_number TEXT,
        session_string TEXT,
        is_active INTEGER DEFAULT 1,
        added_date TEXT,
        last_check TEXT
    )''')
    
    conn.commit()
    conn.close()

def is_admin(user_id, super_admin_id):
    if user_id == super_admin_id:
        return True
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT admin_id FROM admins WHERE admin_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def add_admin(admin_id, username):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO admins (admin_id, username, added_date) VALUES (?, ?, ?)",
                  (admin_id, username, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def get_all_admins():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT admin_id, username FROM admins")
    admins = [(row['admin_id'], row['username']) for row in c.fetchall()]
    conn.close()
    return admins

def remove_admin(admin_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE admin_id = ?", (admin_id,))
    c.execute("DELETE FROM keywords WHERE admin_id = ?", (admin_id,))
    c.execute("DELETE FROM search_groups WHERE admin_id = ?", (admin_id,))
    c.execute("DELETE FROM private_groups WHERE admin_id = ?", (admin_id,))
    conn.commit()
    conn.close()

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

def add_search_group(admin_id, super_admin_id, group_id=None, group_link=None, group_name=None, bypass_limit=False):
    conn = get_db()
    c = conn.cursor()
    
    if not bypass_limit and admin_id != super_admin_id:
        c.execute("SELECT COUNT(*) as cnt FROM search_groups WHERE admin_id = ?", (admin_id,))
        count = c.fetchone()['cnt']
        if count >= 100:
            conn.close()
            return False, "Limit to'lgan (100/100)"
    
    c.execute("INSERT INTO search_groups (admin_id, group_id, group_link, group_name) VALUES (?, ?, ?, ?)",
              (admin_id, group_id, group_link, group_name))
    conn.commit()
    conn.close()
    return True, "Izlovchi guruh qo'shildi"

def get_search_groups(admin_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, group_name FROM search_groups WHERE admin_id = ?", (admin_id,))
    groups = [(row['id'], row['group_name']) for row in c.fetchall()]
    conn.close()
    return groups

def remove_search_group(group_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM search_groups WHERE id = ?", (group_id,))
    conn.commit()
    conn.close()

def add_private_group(admin_id, group_id=None, group_link=None, group_name=None):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM private_groups WHERE admin_id = ?", (admin_id,))
    c.execute("INSERT INTO private_groups (admin_id, group_id, group_link, group_name) VALUES (?, ?, ?, ?)",
              (admin_id, group_id, group_link, group_name))
    conn.commit()
    conn.close()

def get_private_group_name(admin_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT group_name FROM private_groups WHERE admin_id = ?", (admin_id,))
    result = c.fetchone()
    conn.close()
    return result['group_name'] if result else None

def get_private_group_id(admin_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT group_id FROM private_groups WHERE admin_id = ?", (admin_id,))
    result = c.fetchone()
    conn.close()
    return result['group_id'] if result else None

def remove_private_group(admin_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM private_groups WHERE admin_id = ?", (admin_id,))
    conn.commit()
    conn.close()

def check_keywords_in_message(group_id, message_text):
    conn = get_db()
    c = conn.cursor()
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

def add_api(api_id, api_hash, phone_number, verification_code=None):
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        import asyncio
        
        async def create_session():
            client = TelegramClient(StringSession(), api_id, api_hash)
            await client.connect()
            
            if not await client.is_user_authorized():
                await client.send_code_request(phone_number)
                if verification_code:
                    await client.sign_in(phone_number, verification_code)
            
            session_string = client.session.save()
            await client.disconnect()
            return session_string
        
        session_string = asyncio.run(create_session())
        
        conn = get_db()
        c = conn.cursor()
        c.execute("""INSERT INTO userbot_apis 
                    (api_id, api_hash, phone_number, session_string, is_active, added_date)
                    VALUES (?, ?, ?, ?, 1, ?)""",
                  (api_id, api_hash, phone_number, session_string, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"API qo'shishda xato: {e}")
        return False

def get_all_apis():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM userbot_apis ORDER BY id DESC")
    apis = [dict(row) for row in c.fetchall()]
    conn.close()
    return apis

def get_active_apis():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM userbot_apis WHERE is_active = 1")
    apis = [dict(row) for row in c.fetchall()]
    conn.close()
    return apis

def remove_api(api_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM userbot_apis WHERE id = ?", (api_id,))
    conn.commit()
    conn.close()

def update_api_status(api_id, is_active):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE userbot_apis SET is_active = ?, last_check = ? WHERE id = ?",
              (is_active, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), api_id))
    conn.commit()
    conn.close()
