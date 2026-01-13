import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import database as db

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== SOZLAMALAR ====================
TOKEN = "8332172370:AAHpj0H_6sss-bMoGizp1ulUFQkmkEdC_PA"
SUPER_ADMIN_ID = 7740552653

# ==================== KEYBOARDS ====================

def super_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Yangi admin qo'shish", callback_data='add_admin')],
        [InlineKeyboardButton("📋 Adminlar ro'yxati", callback_data='list_admins')],
        [InlineKeyboardButton("🗑 Admin o'chirish", callback_data='remove_admin')],
        [InlineKeyboardButton("🚪 Admin xonasiga o'tish", callback_data='enter_admin_room')],
        [InlineKeyboardButton("🔧 Userbot sozlamalari", callback_data='userbot_settings')],
        [InlineKeyboardButton("🤖 Userbotni tekshirish", callback_data='check_userbot')]
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
         InlineKeyboardButton("🗑 O'chirish", callback_data='delete_search_group')],
        [InlineKeyboardButton("⬅️ Asosiy menyu", callback_data='back_to_main')]
    ])

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')]])

# ==================== HANDLERS ====================

def start(update: Update, context: CallbackContext):
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

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    data = query.data

    # Check if user is authorized
    if user_id != SUPER_ADMIN_ID and not db.is_admin(user_id, SUPER_ADMIN_ID):
        return

    # ========== SUPER ADMIN FUNKSIYALARI ==========
    if user_id == SUPER_ADMIN_ID:
        if data == 'add_admin':
            context.user_data['waiting'] = 'admin_id'
            query.edit_message_text("📝 Yangi admin ID raqamini yuboring:", reply_markup=back_button())
        
        elif data == 'list_admins':
            admins = db.get_all_admins()
            if admins:
                keyboard = [[InlineKeyboardButton(f"👤 {u} (ID: {i})", url=f"tg://user?id={i}")] for i, u in admins]
                keyboard.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
                query.edit_message_text(f"📋 Adminlar ro'yxati ({len(admins)} ta):", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                query.edit_message_text("ℹ️ Adminlar yo'q.", reply_markup=back_button())
        
        elif data == 'remove_admin':
            admins = db.get_all_admins()
            if admins:
                keyboard = [[InlineKeyboardButton(f"🗑 {u}", callback_data=f'rmadm_{i}')] for i, u in admins]
                keyboard.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
                query.edit_message_text("🗑 O'chirish uchun adminni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                query.edit_message_text("ℹ️ Adminlar yo'q.", reply_markup=back_button())
        
        elif data.startswith('rmadm_'):
            admin_id = int(data.split('_')[1])
            db.remove_admin(admin_id)
            query.edit_message_text("✅ Admin o'chirildi!", reply_markup=back_button())
        
        elif data == 'enter_admin_room':
            admins = db.get_all_admins()
            if admins:
                keyboard = [[InlineKeyboardButton(f"🚪 {u}", callback_data=f'enter_{i}')] for i, u in admins]
                keyboard.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
                query.edit_message_text("🚪 Adminni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                query.edit_message_text("ℹ️ Adminlar yo'q.", reply_markup=back_button())
        
        elif data.startswith('enter_'):
            target_admin_id = int(data.split('_')[1])
            context.user_data['acting_as'] = target_admin_id
            query.edit_message_text(f"🚪 Admin (ID: {target_admin_id}) xonasidasiz:", reply_markup=admin_keyboard())
            
        elif data == 'userbot_settings':
            status = db.get_setting('userbot_schedule_enabled', 'true')
            stop_t = db.get_setting('userbot_stop_time', '00:00')
            start_t = db.get_setting('userbot_start_time', '02:00')
            
            text = (f"🔧 Userbot sozlamalari:\n\n"
                    f"⏰ Rejali restart: {'Yoqilgan' if status == 'true' else 'Ochirilgan'}\n"
                    f"🌙 To'xtash vaqti: {stop_t}\n"
                    f"🌅 Ishga tushish vaqti: {start_t}")
            
            keyboard = [
                [InlineKeyboardButton("🔴 O'chirish" if status == 'true' else "🟢 Yoqish", callback_data='toggle_schedule')],
                [InlineKeyboardButton("⏰ To'xtash vaqtini o'zgartirish", callback_data='set_stop_time')],
                [InlineKeyboardButton("🌅 Boshlash vaqtini o'zgartirish", callback_data='set_start_time')],
                [InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')]
            ]
            query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            
        elif data == 'toggle_schedule':
            current = db.get_setting('userbot_schedule_enabled', 'true')
            new_val = 'false' if current == 'true' else 'true'
            db.set_setting('userbot_schedule_enabled', new_val)
            button_callback(update, context) # Refresh
            
        elif data == 'set_stop_time':
            context.user_data['waiting'] = 'stop_time'
            query.edit_message_text("📝 To'xtash vaqtini kiriting (masalan, 00:00):", reply_markup=back_button())
            
        elif data == 'set_start_time':
            context.user_data['waiting'] = 'start_time'
            query.edit_message_text("📝 Boshlash vaqtini kiriting (masalan, 02:00):", reply_markup=back_button())

    # ========== ADMIN FUNKSIYALARI ==========
    current_admin_id = context.user_data.get('acting_as', user_id)
    
    if data == 'add_keyword':
        context.user_data['waiting'] = 'keyword'
        query.edit_message_text("📝 Yangi kalit so'zni kiriting:", reply_markup=back_button())
        
    elif data == 'view_keywords':
        keywords = db.get_keywords(current_admin_id)
        if keywords:
            text = "📋 Kalit so'zlar ro'yxati:\n\n" + "\n".join([f"• {k}" for _, k in keywords])
            query.edit_message_text(text, reply_markup=admin_keyboard())
        else:
            query.edit_message_text("ℹ️ Kalit so'zlar yo'q.", reply_markup=admin_keyboard())
            
    elif data == 'delete_keyword':
        keywords = db.get_keywords(current_admin_id)
        if keywords:
            keyboard = [[InlineKeyboardButton(f"🗑 {k}", callback_data=f'delkey_{i}')] for i, k in keywords]
            keyboard.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text("🗑 O'chirish uchun kalit so'zni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            query.edit_message_text("ℹ️ Kalit so'zlar yo'q.", reply_markup=back_button())
            
    elif data.startswith('delkey_'):
        key_id = int(data.split('_')[1])
        db.remove_keyword(key_id)
        query.edit_message_text("✅ Kalit so'z o'chirildi!", reply_markup=back_button())
        
    elif data == 'add_private_group':
        context.user_data['waiting'] = 'private_group'
        query.edit_message_text("📝 Shaxsiy guruh ID raqamini yoki linkini yuboring:", reply_markup=back_button())
        
    elif data == 'view_private_group':
        group = db.get_private_group(current_admin_id)
        if group:
            query.edit_message_text(f"👁 Shaxsiy guruh: {group['group_name']} (ID: {group['group_id']})", reply_markup=admin_keyboard())
        else:
            query.edit_message_text("ℹ️ Shaxsiy guruh belgilanmagan.", reply_markup=admin_keyboard())
            
    elif data == 'delete_private_group':
        db.remove_private_group(current_admin_id)
        query.edit_message_text("✅ Shaxsiy guruh o'chirildi!", reply_markup=back_button())
        
    elif data == 'add_search_group':
        # Rate limit check for normal admins
        if user_id != SUPER_ADMIN_ID:
            last_time = db.get_last_search_group_time(user_id)
            if last_time and datetime.now() - last_time < timedelta(hours=1):
                diff = timedelta(hours=1) - (datetime.now() - last_time)
                minutes = int(diff.total_seconds() / 60)
                query.edit_message_text(f"⚠️ Siz soatiga faqat 1 ta guruh qo'sha olasiz. Iltimos, {minutes} daqiqa kuting.", reply_markup=back_button())
                return
        
        context.user_data['waiting'] = 'search_group'
        query.edit_message_text("📝 Izlovchi guruh ID raqamini yoki linkini yuboring:", reply_markup=back_button())
        
    elif data == 'view_search_groups':
        groups = db.get_search_groups(current_admin_id)
        if groups:
            text = "📋 Izlovchi guruhlar ro'yxati:\n\n" + "\n".join([f"• {name} (ID: {gid})" for _, gid, name in groups])
            query.edit_message_text(text, reply_markup=admin_keyboard())
        else:
            query.edit_message_text("ℹ️ Izlovchi guruhlar yo'q.", reply_markup=admin_keyboard())
            
    elif data == 'delete_search_group':
        groups = db.get_search_groups(current_admin_id)
        if groups:
            keyboard = [[InlineKeyboardButton(f"🗑 {name}", callback_data=f'delsg_{i}')] for i, gid, name in groups]
            keyboard.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text("🗑 O'chirish uchun guruhni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            query.edit_message_text("ℹ️ Izlovchi guruhlar yo'q.", reply_markup=back_button())
            
    elif data.startswith('delsg_'):
        sg_id = int(data.split('_')[1])
        db.remove_search_group(sg_id)
        query.edit_message_text("✅ Izlovchi guruh o'chirildi!", reply_markup=back_button())
        
    elif data == 'back_to_main':
        context.user_data.pop('waiting', None)
        context.user_data.pop('acting_as', None)
        if user_id == SUPER_ADMIN_ID:
            query.edit_message_text("🔐 Super Admin menyusi:", reply_markup=super_admin_keyboard())
        else:
            query.edit_message_text("🏠 Shaxsiy xonangiz:", reply_markup=admin_keyboard())

def handle_text(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text
    waiting = context.user_data.get('waiting')
    current_admin_id = context.user_data.get('acting_as', user_id)

    if not waiting:
        return

    if waiting == 'admin_id' and user_id == SUPER_ADMIN_ID:
        try:
            new_admin_id = int(text)
            db.add_admin(new_admin_id, f"Admin_{new_admin_id}")
            update.message.reply_text(f"✅ Admin qo'shildi! ID: {new_admin_id}", reply_markup=back_button())
        except ValueError:
            update.message.reply_text("❌ Iltimos, faqat raqamli ID yuboring.")
            
    elif waiting == 'keyword':
        db.add_keyword(current_admin_id, text)
        update.message.reply_text(f"✅ Kalit so'z qo'shildi: {text}", reply_markup=back_button())
        
    elif waiting == 'private_group':
        try:
            # Simple validation, in real case we might need to check if bot is in group
            group_id = int(text) if text.lstrip('-').isdigit() else text
            db.set_private_group(current_admin_id, group_id, f"Guruh_{group_id}")
            update.message.reply_text(f"✅ Shaxsiy guruh saqlandi: {group_id}", reply_markup=back_button())
        except:
            update.message.reply_text("❌ Xato! ID yoki linkni tekshiring.")
            
    elif waiting == 'search_group':
        try:
            group_id = int(text) if text.lstrip('-').isdigit() else text
            db.add_search_group(current_admin_id, group_id, f"Guruh_{group_id}")
            update.message.reply_text(f"✅ Izlovchi guruh qo'shildi: {group_id}", reply_markup=back_button())
        except:
            update.message.reply_text("❌ Xato! ID yoki linkni tekshiring.")
            
    elif waiting == 'stop_time' and user_id == SUPER_ADMIN_ID:
        db.set_setting('userbot_stop_time', text)
        update.message.reply_text(f"✅ To'xtash vaqti {text} ga o'zgartirildi.", reply_markup=back_button())
        
    elif waiting == 'start_time' and user_id == SUPER_ADMIN_ID:
        db.set_setting('userbot_start_time', text)
        update.message.reply_text(f"✅ Boshlash vaqti {text} ga o'zgartirildi.", reply_markup=back_button())

    context.user_data.pop('waiting', None)

def main():
    db.init_db()
    
    # Default settings
    if not db.get_setting('userbot_stop_time'):
        db.set_setting('userbot_stop_time', '00:00')
    if not db.get_setting('userbot_start_time'):
        db.set_setting('userbot_start_time', '02:00')
    if not db.get_setting('userbot_schedule_enabled'):
        db.set_setting('userbot_schedule_enabled', 'true')
    
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_callback))
    dp.add_handler(MessageHandler(Filters.text & Filters.private, handle_text))

    logger.info("🚀 Bot ishga tushmoqda...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
