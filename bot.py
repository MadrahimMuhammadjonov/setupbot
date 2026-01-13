import logging
import asyncio
import threading
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import database as db
from telethon import TelegramClient
from telethon.sessions import StringSession

# Logging configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = "8332172370:AAHpj0H_6sss-bMoGizp1ulUFQkmkEdC_PA"
SUPER_ADMIN_ID = 7740552653

pending_auth = {}

def super_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Admin qo'shish", callback_data='add_admin')],
        [InlineKeyboardButton("📋 Adminlar", callback_data='list_admins')],
        [InlineKeyboardButton("🗑 Admin o'chirish", callback_data='remove_admin')],
        [InlineKeyboardButton("🚪 Admin xonasi", callback_data='enter_admin_room')],
        [InlineKeyboardButton("🤖 Userbot qo'shish", callback_data='add_userbot')],
        [InlineKeyboardButton("📋 Userbotlar", callback_data='list_apis')],
        [InlineKeyboardButton("📊 Status", callback_data='check_userbot')]
    ])

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kalit so'z", callback_data='add_keyword'),
         InlineKeyboardButton("📋 Ko'rish", callback_data='view_keywords')],
        [InlineKeyboardButton("🗑 O'chirish", callback_data='delete_keyword')],
        [InlineKeyboardButton("➕ Shaxsiy guruh", callback_data='add_private_group')],
        [InlineKeyboardButton("👁 Ko'rish", callback_data='view_private_group'),
         InlineKeyboardButton("🗑 O'chirish", callback_data='delete_private_group')],
        [InlineKeyboardButton("➕ Izlovchi guruh", callback_data='add_search_group')],
        [InlineKeyboardButton("📋 Ko'rish", callback_data='view_search_groups'),
         InlineKeyboardButton("🗑 O'chirish", callback_data='delete_search_group')]
    ])

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')]])

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    if user_id == SUPER_ADMIN_ID:
        update.message.reply_text("🔐 Super Admin paneliga xush kelibsiz!", reply_markup=super_admin_keyboard())
    elif db.is_admin(user_id, SUPER_ADMIN_ID):
        update.message.reply_text(f"👋 Assalomu alaykum, {username}!", reply_markup=admin_keyboard())
    else:
        welcome_text = (
            f"👋 Assalomu alaykum, {username}!\n\n"
            "🤖 <b>Bot haqida:</b>\n"
            "Bu bot Telegram guruhlarida kalit so'zlarni kuzatib borish uchun mo'ljallangan.\n\n"
            "⚠️ <b>E'tibor:</b>\n"
            "Bu bot faqat adminlar uchun mo'ljallangan."
        )
        keyboard = [[InlineKeyboardButton("👤 Admin bilan bog'lanish", url=f"tg://user?id={SUPER_ADMIN_ID}")]]
        update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

def handle_text(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    waiting = context.user_data.get('waiting')

    if not waiting:
        return

    if waiting == 'admin_id' and user_id == SUPER_ADMIN_ID:
        try:
            new_admin_id = int(text)
            db.add_admin(new_admin_id, f"Admin_{new_admin_id}")
            update.message.reply_text(f"✅ Admin qo'shildi: {new_admin_id}", reply_markup=back_button())
            context.user_data.pop('waiting')
        except ValueError:
            update.message.reply_text("❌ Noto'g'ri ID! Faqat raqam kiriting.")

    # Step 1: Phone Number
    elif waiting == 'userbot_phone' and user_id == SUPER_ADMIN_ID:
        if not text.startswith('+'):
            update.message.reply_text("❌ Telefon raqam + bilan boshlanishi kerak (masalan: +998901234567)")
            return
        context.user_data['temp_phone'] = text
        context.user_data['waiting'] = 'userbot_api_id'
        update.message.reply_text(f"📱 Raqam: `{text}`\n\nEndi ushbu raqam uchun **API ID** ni yuboring:", reply_markup=back_button(), parse_mode='Markdown')

    # Step 2: API ID
    elif waiting == 'userbot_api_id' and user_id == SUPER_ADMIN_ID:
        try:
            api_id = int(text)
            context.user_data['temp_api_id'] = api_id
            context.user_data['waiting'] = 'userbot_api_hash'
            update.message.reply_text(f"🆔 API ID: `{api_id}`\n\nEndi ushbu raqam uchun **API Hash** ni yuboring:", reply_markup=back_button(), parse_mode='Markdown')
        except ValueError:
            update.message.reply_text("❌ API ID faqat raqamlardan iborat bo'lishi kerak!")

    # Step 3: API Hash
    elif waiting == 'userbot_api_hash' and user_id == SUPER_ADMIN_ID:
        api_hash = text
        phone = context.user_data.get('temp_phone')
        api_id = context.user_data.get('temp_api_id')
        
        context.user_data['temp_api_hash'] = api_hash
        update.message.reply_text(f"🔑 API Hash: `{api_hash}`\n\n⏳ Telegram'dan kod so'ralmoqda...", parse_mode='Markdown')
        
        def start_client_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            client = TelegramClient(StringSession(), api_id, api_hash)
            try:
                loop.run_until_complete(client.connect())
                send_code = loop.run_until_complete(client.send_code_request(phone))
                
                pending_auth[user_id] = {
                    'client': client,
                    'phone': phone,
                    'phone_code_hash': send_code.phone_code_hash,
                    'loop': loop,
                    'api_id': api_id,
                    'api_hash': api_hash
                }
                
                context.user_data['waiting'] = 'userbot_code'
                update.message.reply_text(f"📩 `{phone}` raqamiga yuborilgan kodni kiriting:", reply_markup=back_button(), parse_mode='Markdown')
            except Exception as e:
                update.message.reply_text(f"❌ Xatolik: {str(e)}\n\nKiritilgan API ID yoki API Hash noto'g'ri bo'lishi mumkin. Qaytadan boshlang.")
                context.user_data.pop('waiting', None)
                loop.run_until_complete(client.disconnect())
                loop.close()

        threading.Thread(target=start_client_thread).start()

    # Step 4: Verification Code
    elif waiting == 'userbot_code' and user_id == SUPER_ADMIN_ID:
        auth_data = pending_auth.get(user_id)
        if not auth_data:
            update.message.reply_text("❌ Sessiya topilmadi. Qaytadan boshlang.")
            return

        code = text
        update.message.reply_text("⏳ Tasdiqlanmoqda...")

        def verify_code_thread():
            client = auth_data['client']
            loop = auth_data['loop']
            try:
                loop.run_until_complete(client.sign_in(auth_data['phone'], code, phone_code_hash=auth_data['phone_code_hash']))
                session_str = client.session.save()
                
                db.add_api(auth_data['api_id'], auth_data['api_hash'], auth_data['phone'], session_str)
                
                update.message.reply_text(f"✅ Userbot muvaffaqiyatli qo'shildi!\n📱 Raqam: {auth_data['phone']}", reply_markup=back_button())
                pending_auth.pop(user_id)
                context.user_data.pop('waiting')
                context.user_data.pop('temp_phone', None)
                context.user_data.pop('temp_api_id', None)
                context.user_data.pop('temp_api_hash', None)
            except Exception as e:
                update.message.reply_text(f"❌ Xatolik: {str(e)}")
            finally:
                loop.run_until_complete(client.disconnect())
                loop.close()

        threading.Thread(target=verify_code_thread).start()

    elif waiting == 'keyword':
        aid = context.user_data.get('viewing_admin', user_id)
        db.add_keyword(aid, text)
        update.message.reply_text(f"✅ Kalit so'z qo'shildi: {text}", reply_markup=back_button())
        context.user_data.pop('waiting')

    elif waiting == 'private_group':
        aid = context.user_data.get('viewing_admin', user_id)
        try:
            gid = int(text)
            db.add_private_group(aid, group_id=gid, group_name=f"Guruh {gid}")
            update.message.reply_text(f"✅ Shaxsiy guruh ID saqlandi: {gid}", reply_markup=back_button())
            context.user_data.pop('waiting')
        except ValueError:
            update.message.reply_text("❌ Noto'g'ri ID!")

    elif waiting == 'search_group':
        aid = context.user_data.get('viewing_admin', user_id)
        try:
            gid = int(text)
            db.add_search_group(aid, SUPER_ADMIN_ID, group_id=gid, group_name=f"Guruh {gid}")
            update.message.reply_text(f"✅ Izlovchi guruh qo'shildi: {gid}", reply_markup=back_button())
            context.user_data.pop('waiting')
        except ValueError:
            update.message.reply_text("❌ Noto'g'ri ID!")

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == 'back_to_main':
        context.user_data.pop('waiting', None)
        context.user_data.pop('viewing_admin', None)
        if user_id == SUPER_ADMIN_ID:
            query.edit_message_text("🔐 Super Admin paneli:", reply_markup=super_admin_keyboard())
        else:
            query.edit_message_text("🏠 Admin paneli:", reply_markup=admin_keyboard())

    elif data == 'add_admin' and user_id == SUPER_ADMIN_ID:
        context.user_data['waiting'] = 'admin_id'
        query.edit_message_text("📝 Yangi admin ID sini yuboring:", reply_markup=back_button())

    elif data == 'add_userbot' and user_id == SUPER_ADMIN_ID:
        context.user_data['waiting'] = 'userbot_phone'
        query.edit_message_text("📱 Userbot uchun telefon raqamni yuboring (+998...):", reply_markup=back_button())

    elif data == 'list_apis' and user_id == SUPER_ADMIN_ID:
        apis = db.get_all_apis()
        text = "📋 Userbotlar:\n"
        for a in apis:
            text += f"• {a['phone_number']} (ID: {a['api_id']}) - {'✅' if a['is_active'] else '❌'}\n"
        query.edit_message_text(text or "ℹ️ Userbotlar yo'q", reply_markup=back_button())

    # Admin actions
    elif data == 'add_keyword':
        context.user_data['waiting'] = 'keyword'
        query.edit_message_text("📝 Kalit so'zni yuboring:", reply_markup=back_button())

    elif data == 'view_keywords':
        aid = context.user_data.get('viewing_admin', user_id)
        keywords = db.get_keywords(aid)
        text = "📋 Kalit so'zlaringiz:\n" + "\n".join([f"• {k}" for i, k in keywords]) if keywords else "ℹ️ Kalit so'zlar yo'q"
        query.edit_message_text(text, reply_markup=back_button())

    elif data == 'add_private_group':
        context.user_data['waiting'] = 'private_group'
        query.edit_message_text("📝 Shaxsiy guruh ID sini yuboring:", reply_markup=back_button())

    elif data == 'add_search_group':
        context.user_data['waiting'] = 'search_group'
        query.edit_message_text("📝 Izlovchi guruh ID sini yuboring:", reply_markup=back_button())

    elif data == 'enter_admin_room' and user_id == SUPER_ADMIN_ID:
        admins = db.get_all_admins()
        if not admins:
            query.edit_message_text("ℹ️ Adminlar yo'q", reply_markup=back_button())
            return
        kb = [[InlineKeyboardButton(f"🚪 {u}", callback_data=f'view_{i}')] for i, u in admins]
        kb.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
        query.edit_message_text("🚪 Admin tanlang:", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith('view_') and user_id == SUPER_ADMIN_ID:
        aid = int(data.split('_')[1])
        context.user_data['viewing_admin'] = aid
        query.edit_message_text(f"🏠 Admin xonasi ({aid}):", reply_markup=admin_keyboard())

def main():
    db.init_db()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_callback))
    dp.add_handler(MessageHandler(Filters.text & Filters.private, handle_text))
    
    logger.info("🚀 Bot ishga tushdi...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
