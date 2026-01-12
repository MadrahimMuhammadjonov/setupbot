# ============================================
# database.py - Shared Database Module
# Bot va Userbot uchun umumiy database
# ============================================

import sqlite3
import logging
from datetime import datetime, timedelta

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "bot_data.db"

def get_db():
    """Database connection yaratish"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Database jadvallari va indekslarni yaratish"""
    conn = get_db()
    c = conn.cursor()

    # Adminlar jadvali
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        added_date TEXT,
        last_group_add TEXT
    )''')

    # Kalit so'zlar jadvali
    c.execute('''CREATE TABLE IF NOT EXISTS keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER NOT NULL,
        keyword TEXT NOT NULL,
        created_date TEXT,
        FOREIGN KEY(admin_id) REFERENCES admins(user_id) ON DELETE CASCADE
    )''')

    # Shaxsiy guruhlar jadvali
    c.execute('''CREATE TABLE IF NOT EXISTS private_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER UNIQUE NOT NULL,
        group_id INTEGER,
        group_link TEXT,
        group_name TEXT,
        added_date TEXT,
        FOREIGN KEY(admin_id) REFERENCES admins(user_id) ON DELETE CASCADE
    )''')

    # Izlovchi guruhlar jadvali
    c.execute('''CREATE TABLE IF NOT EXISTS search_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER NOT NULL,
        group_id INTEGER,
        group_link TEXT,
        group_name TEXT,
        added_date TEXT,
        FOREIGN KEY(admin_id) REFERENCES admins(user_id) ON DELETE CASCADE
    )''')

    # Bot sozlamalari
    c.execute('''CREATE TABLE IF NOT EXISTS bot_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    # Indekslar
    c.execute('CREATE INDEX IF NOT EXISTS idx_keywords_admin ON keywords(admin_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_search_groups_admin ON search_groups(admin_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_search_groups_group ON search_groups(group_id)')
    
    conn.commit()
    conn.close()
    logger.info("✅ Database initialized")

# ==================== ADMIN FUNKSIYALARI ====================

def is_admin(user_id, super_admin_id):
    """Admin yoki super admin ekanligini tekshirish"""
    if user_id == super_admin_id:
        return True
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def add_admin(user_id, username):
    """Yangi admin qo'shish"""
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO admins (user_id, username, added_date) VALUES (?, ?, ?)",
                  (user_id, username, datetime.now().isoformat()))
        conn.commit()
        success = c.rowcount > 0
    except Exception as e:
        logger.error(f"Admin qo'shishda xato: {e}")
        success = False
    conn.close()
    return success

def remove_admin(user_id):
    """Adminni o'chirish (barcha ma'lumotlari bilan)"""
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    c.execute("DELETE FROM keywords WHERE admin_id = ?", (user_id,))
    c.execute("DELETE FROM private_groups WHERE admin_id = ?", (user_id,))
    c.execute("DELETE FROM search_groups WHERE admin_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True

def get_all_admins():
    """Barcha adminlar ro'yxatini olish"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id, username FROM admins")
    admins = [(r['user_id'], r['username']) for r in c.fetchall()]
    conn.close()
    return admins

# ==================== KALIT SO'ZLAR ====================

def add_keyword(admin_id, keyword):
    """Kalit so'z qo'shish"""
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO keywords (admin_id, keyword, created_date) VALUES (?, ?, ?)",
              (admin_id, keyword, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return True

def get_keywords(admin_id):
    """Admin kalit so'zlarini olish"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, keyword FROM keywords WHERE admin_id = ?", (admin_id,))
    keywords = [(r['id'], r['keyword']) for r in c.fetchall()]
    conn.close()
    return keywords

def remove_keyword(keyword_id):
    """Kalit so'zni o'chirish"""
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))
    conn.commit()
    conn.close()
    return True

# ==================== SHAXSIY GURUHLAR ====================

def add_private_group(admin_id, group_id=None, group_link=None, group_name=None):
    """Shaxsiy guruh qo'shish"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO private_groups
                 (admin_id, group_id, group_link, group_name, added_date)
                 VALUES (?, ?, ?, ?, ?)""",
              (admin_id, group_id, group_link, group_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return True

def get_private_group(admin_id):
    """Admin shaxsiy guruhini olish"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT group_id, group_name FROM private_groups WHERE admin_id = ?", (admin_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return {'group_id': result['group_id'], 'group_name': result['group_name']}
    return None

def get_private_group_name(admin_id):
    """Admin shaxsiy guruh nomini olish"""
    group = get_private_group(admin_id)
    return group['group_name'] if group else None

def remove_private_group(admin_id):
    """Shaxsiy guruhni o'chirish"""
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM private_groups WHERE admin_id = ?", (admin_id,))
    conn.commit()
    conn.close()
    return True

# ==================== IZLOVCHI GURUHLAR ====================

def can_add_search_group(admin_id, super_admin_id):
    """Izlovchi guruh qo'shish mumkinligini tekshirish (1 soat limiti)"""
    if admin_id == super_admin_id:
        return True, None
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT last_group_add FROM admins WHERE user_id = ?", (admin_id,))
    result = c.fetchone()
    conn.close()
    
    if not result or not result['last_group_add']:
        return True, None
    
    last_add = datetime.fromisoformat(result['last_group_add'])
    time_diff = datetime.now() - last_add
    
    if time_diff < timedelta(hours=1):
        remaining = timedelta(hours=1) - time_diff
        minutes = int(remaining.total_seconds() / 60)
        return False, minutes
    
    return True, None

def add_search_group(admin_id, super_admin_id, group_id=None, group_name=None, group_link=None):
    """Izlovchi guruh qo'shish"""
    conn = get_db()
    c = conn.cursor()
    
    # 100 ta limit tekshirish
    c.execute("SELECT COUNT(*) AS cnt FROM search_groups WHERE admin_id = ?", (admin_id,))
    count = c.fetchone()['cnt']
    if count >= 100:
        conn.close()
        return False, "Maksimal 100 ta guruh!"
    
    # Vaqt limiti tekshirish
    can_add, remaining_minutes = can_add_search_group(admin_id, super_admin_id)
    if not can_add:
        conn.close()
        return False, f"Yana {remaining_minutes} daqiqadan keyin qo'shishingiz mumkin!"
    
    # Guruh qo'shish
    c.execute("""INSERT INTO search_groups
                 (admin_id, group_id, group_name, group_link, added_date)
                 VALUES (?, ?, ?, ?, ?)""",
              (admin_id, group_id, group_name, group_link, datetime.now().isoformat()))
    
    # Last_group_add yangilash (super admin uchun emas)
    if admin_id != super_admin_id:
        c.execute("UPDATE admins SET last_group_add = ? WHERE user_id = ?",
                  (datetime.now().isoformat(), admin_id))
    
    conn.commit()
    conn.close()
    return True, "Guruh qo'shildi!"

def get_search_groups(admin_id):
    """Admin izlovchi guruhlarini olish"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, group_name FROM search_groups WHERE admin_id = ?", (admin_id,))
    groups = [(r['id'], r['group_name']) for r in c.fetchall()]
    conn.close()
    return groups

def remove_search_group(row_id):
    """Izlovchi guruhni o'chirish"""
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM search_groups WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()
    return True

# ==================== KEYWORD TEKSHIRISH ====================

def check_keywords_in_message(group_id, message_text):
    """Guruh xabarida kalit so'zlarni tekshirish"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT DISTINCT k.admin_id, k.keyword, pg.group_id AS private_group_id
                 FROM keywords k
                 JOIN search_groups sg ON k.admin_id = sg.admin_id
                 JOIN private_groups pg ON k.admin_id = pg.admin_id
                 WHERE sg.group_id = ?""", (group_id,))
    results = c.fetchall()
    conn.close()
    
    matches = []
    msg_lower = (message_text or "").lower()
    for r in results:
        if (r['keyword'] or "").lower() in msg_lower:
            matches.append({
                'admin_id': r['admin_id'],
                'keyword': r['keyword'],
                'private_group_id': r['private_group_id']
            })
    return matches

# ==================== BOT SOZLAMALARI ====================

def get_setting(key, default=None):
    """Bot sozlamasini olish"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM bot_settings WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    return result['value'] if result else default

def set_setting(key, value):
    """Bot sozlamasini saqlash"""
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


# ============================================
# bot.py - Telegram Bot
# ============================================

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import database as db

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== SOZLAMALAR ====================
TOKEN = "8332172370:AAHpj0H_6sss-bMoGizp1ulUFQkmkEdC_PA"
SUPER_ADMIN_ID = 7740552653

# ==================== KEYBOARD ====================

def super_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Yangi admin qo'shish", callback_data='add_admin')],
        [InlineKeyboardButton("📋 Adminlar ro'yxati", callback_data='list_admins')],
        [InlineKeyboardButton("🗑 Admin o'chirish", callback_data='remove_admin')],
        [InlineKeyboardButton("🚪 Admin xonasiga o'tish", callback_data='enter_admin_room')]
    ])

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kalit so'z", callback_data='add_keyword'), 
         InlineKeyboardButton("📋 Ko'rish", callback_data='view_keywords')],
        [InlineKeyboardButton("🗑 So'z o'chirish", callback_data='delete_keyword')],
        [InlineKeyboardButton("➕ Shaxsiy guruh", callback_data='add_private_group')],
        [InlineKeyboardButton("👁 Ko'rish", callback_data='view_private_group'), 
         InlineKeyboardButton("🗑 O'chirish", callback_data='delete_private_group')],
        [InlineKeyboardButton("➕ Izlovchi guruh", callback_data='add_search_group')],
        [InlineKeyboardButton("📋 Ko'rish", callback_data='view_search_groups'), 
         InlineKeyboardButton("🗑 O'chirish", callback_data='delete_search_group')]
    ])

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')]])

# ==================== HANDLERS ====================

def start(update: Update, context: CallbackContext):
    """Start command handler"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    if user_id == SUPER_ADMIN_ID:
        update.message.reply_text(
            "🔐 Assalomu alaykum, Super Admin!\n\nMenyudan kerakli bo'limni tanlang:",
            reply_markup=super_admin_keyboard()
        )
    elif db.is_admin(user_id, SUPER_ADMIN_ID):
        update.message.reply_text(
            f"👋 Assalomu alaykum, {username}!\n\n🏠 Shaxsiy xonangizga xush kelibsiz:",
            reply_markup=admin_keyboard()
        )
    else:
        keyboard = [[InlineKeyboardButton("👤 Adminga bog'lanish", url=f"tg://user?id={SUPER_ADMIN_ID}")]]
        update.message.reply_text(
            f"👋 Assalomu alaykum, {username}!\n\n⚠️ Botdan faqat adminlar foydalana oladi!\nBotdan foydalanish uchun adminga murojaat qiling!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def get_chat_id(update: Update, context: CallbackContext):
    """Guruh ID olish"""
    chat_id = update.effective_chat.id
    update.message.reply_text(f"📊 Bu guruh ID: {chat_id}")

def button_callback(update: Update, context: CallbackContext):
    """Inline button callback handler"""
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    data = query.data

    # Super Admin - Admin qo'shish
    if data == 'add_admin' and user_id == SUPER_ADMIN_ID:
        context.user_data['waiting'] = 'admin_id'
        query.edit_message_text("📝 Yangi admin ID raqamini yuboring:", reply_markup=back_button())

    # Super Admin - Adminlar ro'yxati
    elif data == 'list_admins' and user_id == SUPER_ADMIN_ID:
        admins = db.get_all_admins()
        if admins:
            keyboard = [[InlineKeyboardButton(f"👤 {u} (ID: {i})", url=f"tg://user?id={i}")] for i, u in admins]
            keyboard.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text(f"📋 Adminlar ro'yxati ({len(admins)} ta):", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            query.edit_message_text("ℹ️ Adminlar yo'q.", reply_markup=back_button())

    # Super Admin - Admin o'chirish
    elif data == 'remove_admin' and user_id == SUPER_ADMIN_ID:
        admins = db.get_all_admins()
        if admins:
            keyboard = [[InlineKeyboardButton(f"🗑 {u}", callback_data=f'rmadm_{i}')] for i, u in admins]
            keyboard.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text("🗑 O'chirish uchun adminni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            query.edit_message_text("ℹ️ Adminlar yo'q.", reply_markup=back_button())

    elif data.startswith('rmadm_') and user_id == SUPER_ADMIN_ID:
        admin_id = int(data.split('_')[1])
        db.remove_admin(admin_id)
        query.edit_message_text("✅ Admin o'chirildi!", reply_markup=back_button())

    # Super Admin - Admin xonasiga kirish
    elif data == 'enter_admin_room' and user_id == SUPER_ADMIN_ID:
        admins = db.get_all_admins()
        if admins:
            keyboard = [[InlineKeyboardButton(f"🚪 {u}", callback_data=f'enter_{i}')] for i, u in admins]
            keyboard.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text("🚪 Adminni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            query.edit_message_text("ℹ️ Adminlar yo'q.", reply_markup=back_button())

    elif data.startswith('enter_') and user_id == SUPER_ADMIN_ID:
        admin_id = int(data.split('_')[1])
        context.user_data['viewing_admin'] = admin_id
        query.edit_message_text(f"🏠 Admin xonasi (ID: {admin_id}):", reply_markup=admin_keyboard())

    # Kalit so'z qo'shish
    elif data == 'add_keyword':
        context.user_data['waiting'] = 'keyword'
        query.edit_message_text("📝 Kalit so'zni kiriting:", reply_markup=back_button())

    # Kalit so'zlarni ko'rish
    elif data == 'view_keywords':
        admin_id = context.user_data.get('viewing_admin', user_id)
        kws = db.get_keywords(admin_id)
        if kws:
            text = "📋 Kalit so'zlar:\n\n" + "\n".join([f"{i}. {k}" for i, (_, k) in enumerate(kws, 1)]) + f"\n\n💾 Jami: {len(kws)} ta"
            query.edit_message_text(text, reply_markup=back_button())
        else:
            query.edit_message_text("ℹ️ Kalit so'zlar yo'q.", reply_markup=back_button())

    # Kalit so'z o'chirish
    elif data == 'delete_keyword':
        admin_id = context.user_data.get('viewing_admin', user_id)
        kws = db.get_keywords(admin_id)
        if kws:
            keyboard = [[InlineKeyboardButton(f"🗑 {k}", callback_data=f'delkw_{i}')] for i, k in kws]
            keyboard.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text("🗑 O'chirish uchun tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            query.edit_message_text("ℹ️ Kalit so'zlar yo'q.", reply_markup=back_button())

    elif data.startswith('delkw_'):
        kid = int(data.split('_')[1])
        db.remove_keyword(kid)
        query.edit_message_text("✅ Kalit so'z o'chirildi!", reply_markup=back_button())

    # Shaxsiy guruh qo'shish
    elif data == 'add_private_group':
        context.user_data['waiting'] = 'private_group'
        query.edit_message_text(
            "📝 Shaxsiy guruh ID yoki link yuboring:\n\n💡 ID olish:\n1. Botni guruhga admin qiling\n2. Guruhda /id yuboring\n3. ID yoki linkni bu yerga yuboring",
            reply_markup=back_button()
        )

    # Shaxsiy guruhni ko'rish
    elif data == 'view_private_group':
        admin_id = context.user_data.get('viewing_admin', user_id)
        gname = db.get_private_group_name(admin_id)
        if gname:
            query.edit_message_text(f"📢 Shaxsiy guruh: {gname}", reply_markup=back_button())
        else:
            query.edit_message_text("ℹ️ Shaxsiy guruh yo'q.", reply_markup=back_button())

    # Shaxsiy guruhni o'chirish
    elif data == 'delete_private_group':
        admin_id = context.user_data.get('viewing_admin', user_id)
        gname = db.get_private_group_name(admin_id)
        if gname:
            keyboard = [[InlineKeyboardButton(f"🗑 {gname}", callback_data=f'delpr_{admin_id}')]]
            keyboard.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text("🗑 O'chirish uchun shaxsiy guruhni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            query.edit_message_text("ℹ️ Shaxsiy guruh yo'q.", reply_markup=back_button())

    elif data.startswith('delpr_'):
        admin_id = int(data.split('_')[1])
        db.remove_private_group(admin_id)
        query.edit_message_text("✅ Shaxsiy guruh o'chirildi!", reply_markup=back_button())

    # Izlovchi guruh qo'shish
    elif data == 'add_search_group':
        admin_id = context.user_data.get('viewing_admin', user_id)
        grps = db.get_search_groups(admin_id)
        context.user_data['waiting'] = 'search_group'
        query.edit_message_text(
            f"📝 Izlovchi guruh ID yoki link yuboring:\n\n📊 Hozirda: {len(grps)}/100 ta\n\n💡 ID olish:\n1. Botni guruhga admin qiling\n2. Guruhda /id yuboring\n3. ID yoki linkni bu yerga yuboring",
            reply_markup=back_button()
        )

    # Izlovchi guruhlarni ko'rish
    elif data == 'view_search_groups':
        admin_id = context.user_data.get('viewing_admin', user_id)
        grps = db.get_search_groups(admin_id)
        if grps:
            text = "📋 Izlovchi guruhlar:\n\n"
            for i, gname in enumerate([g[1] for g in grps], 1):
                text += f"{i}. {gname}\n"
            text += f"\n💾 Jami: {len(grps)}/100 ta"
            query.edit_message_text(text, reply_markup=back_button())
        else:
            query.edit_message_text("ℹ️ Izlovchi guruhlar yo'q.", reply_markup=back_button())

    # Izlovchi guruhni o'chirish
    elif data == 'delete_search_group':
        admin_id = context.user_data.get('viewing_admin', user_id)
        grps = db.get_search_groups(admin_id)
        if grps:
            keyboard = [[InlineKeyboardButton(f"🗑 {gname}", callback_data=f'delgrp_{rowid}')] for rowid, gname in grps]
            keyboard.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text("🗑 O'chirish uchun izlovchi guruhni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            query.edit_message_text("ℹ️ Izlovchi guruhlar yo'q.", reply_markup=back_button())

    elif data.startswith('delgrp_'):
        gid_row = int(data.split('_')[1])
        db.remove_search_group(gid_row)
        query.edit_message_text("✅ Izlovchi guruh o'chirildi!", reply_markup=back_button())

    # Ortga qaytish
    elif data == 'back_to_main':
        context.user_data.pop('waiting', None)
        if user_id == SUPER_ADMIN_ID:
            context.user_data.pop('viewing_admin', None)
            query.edit_message_text("🔐 Super Admin menyusi:", reply_markup=super_admin_keyboard())
        elif db.is_admin(user_id, SUPER_ADMIN_ID):
            query.edit_message_text("🏠 Admin menyusi:", reply_markup=admin_keyboard())

def handle_text(update: Update, context: CallbackContext):
    """Matn xabarlarni handle qilish"""
    if not update.message or not update.message.text:
        return
    
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if not db.is_admin(user_id, SUPER_ADMIN_ID):
        return
    
    waiting = context.user_data.get('waiting')

    # Admin qo'shish
    if waiting == 'admin_id' and user_id == SUPER_ADMIN_ID:
        try:
            new_id = int(text)
            try:
                chat = context.bot.get_chat(new_id)
                uname = chat.username or chat.first_name or f"User_{new_id}"
            except:
                uname = f"User_{new_id}"
            
            if db.add_admin(new_id, uname):
                update.message.reply_text(f"✅ Admin qo'shildi!\n\n👤 {uname}\n🆔 {new_id}", reply_markup=back_button())
            else:
                update.message.reply_text("ℹ️ Bu admin mavjud!", reply_markup=back_button())
        except:
            update.message.reply_text("❌ Noto'g'ri ID!", reply_markup=back_button())
        context.user_data.pop('waiting', None)

    # Kalit so'z qo'shish
    elif waiting == 'keyword':
        admin_id = context.user_data.get('viewing_admin', user_id)
        db.add_keyword(admin_id, text)
        update.message.reply_text(f"✅ Kalit so'z qo'shildi: {text}", reply_markup=back_button())
        context.user_data.pop('waiting', None)

    # Shaxsiy guruh qo'shish
    elif waiting == 'private_group':
        admin_id = context.user_data.get('viewing_admin', user_id)
        if text.startswith("http"):
            db.add_private_group(admin_id, group_link=text, group_name="Link orqali guruh")
            update.message.reply_text("✅ Shaxsiy guruh qo'shildi: Link orqali guruh", reply_markup=back_button())
        else:
            try:
                gid = int(text)
                try:
                    chat = context.bot.get_chat(gid)
                    gname = chat.title or f"Guruh {gid}"
                except:
                    gname = f"Guruh {gid}"
                db.add_private_group(admin_id, group_id=gid, group_name=gname)
                update.message.reply_text(f"✅ Shaxsiy guruh qo'shildi: {gname}", reply_markup=back_button())
            except:
                update.message.reply_text("❌ Noto'g'ri ID yoki link!", reply_markup=back_button())
        context.user_data.pop('waiting', None)

    # Izlovchi guruh qo'shish
    elif waiting == 'search_group':
        admin_id = context.user_data.get('viewing_admin', user_id)
