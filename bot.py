import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import database as db
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import threading

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# DIQQAT: Token va ID laringizni xavfsiz saqlang
TOKEN = "8332172370:AAHpj0H_6sss-bMoGizp1ulUFQkmkEdC_PA"
SUPER_ADMIN_ID = 7740552653

pending_auth = {}

def super_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Admin qo'shish", callback_data='add_admin')],
        [InlineKeyboardButton("📋 Adminlar", callback_data='list_admins')],
        [InlineKeyboardButton("🗑 Admin o'chirish", callback_data='remove_admin')],
        [InlineKeyboardButton("🚪 Admin xonasi", callback_data='enter_admin_room')],
        [InlineKeyboardButton("🤖 API boshqaruvi", callback_data='userbot_api_menu')],
        [InlineKeyboardButton("🔧 Sozlamalar", callback_data='userbot_settings')],
        [InlineKeyboardButton("📊 Status", callback_data='check_userbot')]
    ])

def userbot_api_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ API qo'shish", callback_data='add_api')],
        [InlineKeyboardButton("📋 API ro'yxati", callback_data='list_apis')],
        [InlineKeyboardButton("🗑 API o'chirish", callback_data='remove_api')],
        [InlineKeyboardButton("🔍 Tekshirish", callback_data='check_api')],
        [InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')]
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
            "Bu bot Telegram guruhlarida kalit so'zlarni kuzatib borish va xabarnomalar yuborish uchun mo'ljallangan.\n\n"
            "📋 <b>Imkoniyatlar:</b>\n"
            "• Telegram guruhlarida kalit so'zlarni izlash\n"
            "• Topilgan xabarlarni shaxsiy guruhingizga yo'naltirish\n"
            "• Ko'plab guruhlarni bir vaqtning o'zida kuzatish\n"
            "• Real vaqt rejimida xabarnomalar olish\n\n"
            "⚠️ <b>E'tibor:</b>\n"
            "Bu bot faqat adminlar uchun mo'ljallangan. Agar siz botdan foydalanmoqchi bo'lsangiz, iltimos admin bilan bog'laning.\n\n"
            "📞 Savol-javoblar uchun adminimizga murojaat qiling:"
        )
        keyboard = [[InlineKeyboardButton("👤 Admin bilan bog'lanish", url=f"tg://user?id={SUPER_ADMIN_ID}")]]
        update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

def get_chat_id(update: Update, context: CallbackContext):
    update.message.reply_text(f"📊 ID: {update.effective_chat.id}")

async def create_telegram_session(api_id, api_hash, phone_number):
    try:
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.send_code_request(phone_number)
            return client, None
        
        session_string = client.session.save()
        await client.disconnect()
        return None, session_string
        
    except Exception as e:
        logger.error(f"Session yaratishda xato: {e}")
        return None, None

async def verify_telegram_code(client, phone_number, code):
    try:
        await client.sign_in(phone_number, code)
        session_string = client.session.save()
        await client.disconnect()
        return session_string
    except Exception as e:
        logger.error(f"Kod tasdiqlashda xato: {e}")
        return None

def run_async(coroutine):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == 'add_admin' and user_id == SUPER_ADMIN_ID:
        context.user_data['waiting'] = 'admin_id'
        query.edit_message_text("📝 Admin ID yuboring:", reply_markup=back_button())
        
    elif data == 'list_admins' and user_id == SUPER_ADMIN_ID:
        admins = db.get_all_admins()
        if admins:
            kb = [[InlineKeyboardButton(f"{u} ({i})", url=f"tg://user?id={i}")] for i, u in admins]
            kb.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text(f"📋 Adminlar ro'yxati ({len(admins)}):", reply_markup=InlineKeyboardMarkup(kb))
        else:
            query.edit_message_text("ℹ️ Adminlar yo'q", reply_markup=back_button())
            
    elif data == 'remove_admin' and user_id == SUPER_ADMIN_ID:
        admins = db.get_all_admins()
        if admins:
            kb = [[InlineKeyboardButton(f"🗑 {u}", callback_data=f'rmadm_{i}')] for i, u in admins]
            kb.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text("🗑 O'chirish uchun tanlang:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            query.edit_message_text("ℹ️ Adminlar yo'q", reply_markup=back_button())
            
    elif data.startswith('rmadm_') and user_id == SUPER_ADMIN_ID:
        db.remove_admin(int(data.split('_')[1]))
        query.edit_message_text("✅ Admin o'chirildi!", reply_markup=back_button())
        
    elif data == 'enter_admin_room' and user_id == SUPER_ADMIN_ID:
        admins = db.get_all_admins()
        if admins:
            kb = [[InlineKeyboardButton(f"🚪 {u}", callback_data=f'enter_{i}')] for i, u in admins]
            kb.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text("🚪 Admin tanlang:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            query.edit_message_text("ℹ️ Adminlar yo'q", reply_markup=back_button())
            
    elif data.startswith('enter_') and user_id == SUPER_ADMIN_ID:
        admin_id = int(data.split('_')[1])
        context.user_data['viewing_admin'] = admin_id
        context.user_data['is_super_admin_viewing'] = True
        query.edit_message_text(f"🏠 Admin xonasi ({admin_id}):", reply_markup=admin_keyboard())
        
    elif data == 'userbot_api_menu' and user_id == SUPER_ADMIN_ID:
        query.edit_message_text("🤖 API boshqaruvi:", reply_markup=userbot_api_keyboard())
        
    elif data == 'add_api' and user_id == SUPER_ADMIN_ID:
        context.user_data['waiting'] = 'api_phone'
        query.edit_message_text(
            "📱 Telefon raqamni yuboring:\n\n"
            "Format: +998901234567\n\n"
            "⚠️ Raqam to'g'ri formatda bo'lishi kerak!",
            reply_markup=back_button()
        )
        
    elif data == 'list_apis' and user_id == SUPER_ADMIN_ID:
        apis = db.get_all_apis()
        if apis:
            text = "📋 API ro'yxati:\n\n"
            for i, api in enumerate(apis, 1):
                st = "✅" if api['is_active'] else "❌"
                text += f"{i}. {st} {api['phone_number']}\n"
                text += f"   🆔 API ID: {api['api_id']}\n"
                text += f"   🔑 Hash: {api['api_hash'][:10]}...\n"
                if api['session_string']:
                    text += "   ✅ Session mavjud\n"
                else:
                    text += "   ❌ Session yo'q\n"
                text += "\n"
            query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data='userbot_api_menu')]]))
        else:
            query.edit_message_text("ℹ️ API yo'q", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data='userbot_api_menu')]]))
            
    elif data == 'remove_api' and user_id == SUPER_ADMIN_ID:
        apis = db.get_all_apis()
        if apis:
            kb = [[InlineKeyboardButton(f"🗑 {a['phone_number']}", callback_data=f'rmapi_{a["id"]}')] for a in apis]
            kb.append([InlineKeyboardButton("⬅️ Ortga", callback_data='userbot_api_menu')])
            query.edit_message_text("🗑 O'chirish uchun tanlang:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            query.edit_message_text("ℹ️ API yo'q", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data='userbot_api_menu')]]))
            
    elif data.startswith('rmapi_') and user_id == SUPER_ADMIN_ID:
        db.remove_api(int(data.split('_')[1]))
        query.edit_message_text("✅ API o'chirildi!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data='userbot_api_menu')]]))
        
    elif data == 'check_api' and user_id == SUPER_ADMIN_ID:
        apis = db.get_all_apis()
        if apis:
            text = "🔍 API holati:\n\n"
            for api in apis:
                text += f"📱 {api['phone_number']}:\n"
                if api['is_active'] and api['session_string']:
                    text += "   ✅ Aktiv va ishlayapti\n"
                elif api['session_string']:
                    text += "   ⚠️ Session mavjud, lekin faol emas\n"
                else:
                    text += "   ❌ Session yo'q\n"
                text += "\n"
            kb = [[InlineKeyboardButton("🔄 Yangilash", callback_data='check_api')], [InlineKeyboardButton("⬅️ Ortga", callback_data='userbot_api_menu')]]
            query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
        else:
            query.edit_message_text("ℹ️ API yo'q", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data='userbot_api_menu')]]))
            
    elif data == 'userbot_settings' and user_id == SUPER_ADMIN_ID:
        stop = db.get_setting('userbot_stop_time', '00:00')
        start = db.get_setting('userbot_start_time', '02:00')
        enabled = db.get_setting('userbot_schedule_enabled', 'true')
        st = "✅ Yoqilgan" if enabled == 'true' else "❌ O'chirilgan"
        text = f"⚙️ Userbot sozlamalari:\n\n⏰ Vaqt rejimi: {st}\n"
        if enabled == 'true':
            text += f"🌙 To'xtatish vaqti: {stop}\n🌅 Ishga tushirish vaqti: {start}\n\n"
        text += "📝 Yangi vaqtlarni kiriting:\nFormat: <code>00:00:02:00</code>\n\nYoki o'chirish uchun: <code>off</code>"
        kb = [[InlineKeyboardButton("❌ Vaqt rejimini o'chirish", callback_data='userbot_disable_schedule')], [InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')]]
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        context.user_data['waiting'] = 'userbot_time'
        
    elif data == 'userbot_disable_schedule' and user_id == SUPER_ADMIN_ID:
        db.set_setting('userbot_schedule_enabled', 'false')
        query.edit_message_text("✅ Vaqt rejimi o'chirildi! Bot 24/7 ishlaydi.", reply_markup=back_button())
        context.user_data.pop('waiting', None)
        
    elif data == 'check_userbot' and user_id == SUPER_ADMIN_ID:
        try:
            conn = db.get_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) as cnt FROM admins")
            adm = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM keywords")
            kw = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM search_groups")
            sg = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM private_groups")
            pg = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM userbot_apis WHERE is_active = 1")
            act = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM userbot_apis")
            tot = c.fetchone()['cnt']
            conn.close()
            
            text = f"🤖 Bot statistikasi:\n\n👥 Adminlar: {adm}\n🔑 Kalit so'zlar: {kw}\n🔍 Izlovchi guruhlar: {sg}\n📢 Shaxsiy guruhlar: {pg}\n🤖 Aktiv API: {act}/{tot}\n\n💡 Hamma narsa ishlayapti!"
            kb = [[InlineKeyboardButton("🔄 Yangilash", callback_data='check_userbot')], [InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')]]
            query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            query.edit_message_text(f"❌ Xatolik: {e}", reply_markup=back_button())
            
    elif data == 'add_keyword':
        context.user_data['waiting'] = 'keyword'
        query.edit_message_text("📝 Kalit so'z yuboring:", reply_markup=back_button())
        
    elif data == 'view_keywords':
        aid = context.user_data.get('viewing_admin', user_id)
        kws = db.get_keywords(aid)
        if kws:
            text = "📋 Kalit so'zlar ro'yxati:\n\n" + "\n".join([f"{i}. {k}" for i, (_, k) in enumerate(kws, 1)]) + f"\n\n💾 Jami: {len(kws)}"
            query.edit_message_text(text, reply_markup=back_button())
        else:
            query.edit_message_text("ℹ️ Kalit so'zlar yo'q", reply_markup=back_button())
            
    elif data == 'delete_keyword':
        aid = context.user_data.get('viewing_admin', user_id)
        kws = db.get_keywords(aid)
        if kws:
            kb = [[InlineKeyboardButton(f"🗑 {k}", callback_data=f'delkw_{i}')] for i, k in kws]
            kb.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text("🗑 O'chirish uchun tanlang:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            query.edit_message_text("ℹ️ Kalit so'zlar yo'q", reply_markup=back_button())
            
    elif data.startswith('delkw_'):
        # TUZATILGAN QATOR (Indentation fixed)
        db.remove_keyword(int(data.split('_')[1]))
        query.edit_message_text("✅ Kalit so'z o'chirildi!", reply_markup=back_button())
        
    elif data == 'add_private_group':
        context.user_data['waiting'] = 'private_group'
        query.edit_message_text("📝 Shaxsiy guruh ID yoki link yuboring:", reply_markup=back_button())
        
    elif data == 'view_private_group':
        aid = context.user_data.get('viewing_admin', user_id)
        gn = db.get_private_group_name(aid)
        msg_text = f"📢 Shaxsiy guruh: {gn}" if gn else "📢 Shaxsiy guruh yo'q"
        query.edit_message_text(msg_text, reply_markup=back_button())
        
    elif data == 'delete_private_group':
        aid = context.user_data.get('viewing_admin', user_id)
        gn = db.get_private_group_name(aid)
        if gn:
            kb = [[InlineKeyboardButton(f"🗑 {gn}", callback_data=f'delpr_{aid}')], [InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')]]
            query.edit_message_text("🗑 O'chirish:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            query.edit_message_text("ℹ️ Shaxsiy guruh yo'q", reply_markup=back_button())
            
    elif data.startswith('delpr_'):
        db.remove_private_group(int(data.split('_')[1]))
        query.edit_message_text("✅ Shaxsiy guruh o'chirildi!", reply_markup=back_button())
        
    elif data == 'add_search_group':
        aid = context.user_data.get('viewing_admin', user_id)
        grps = db.get_search_groups(aid)
        context.user_data['waiting'] = 'search_group'
        lim = f"{len(grps)}" if context.user_data.get('is_super_admin_viewing') else f"{len(grps)}/100"
        query.edit_message_text(f"📝 Izlovchi guruh ID yoki link yuboring:\n\n📊 Hozirgi: {lim}", reply_markup=back_button())
        
    elif data == 'view_search_groups':
        aid = context.user_data.get('viewing_admin', user_id)
        grps = db.get_search_groups(aid)
        if grps:
            text = "📋 Izlovchi guruhlar:\n\n" + "\n".join([f"{i}. {g[1]}" for i, g in enumerate(grps, 1)])
            lim = f"{len(grps)}" if context.user_data.get('is_super_admin_viewing') else f"{len(grps)}/100"
            text += f"\n\n💾 Jami: {lim}"
            query.edit_message_text(text, reply_markup=back_button())
        else:
            query.edit_message_text("ℹ️ Izlovchi guruhlar yo'q", reply_markup=back_button())
            
    elif data == 'delete_search_group':
        aid = context.user_data.get('viewing_admin', user_id)
        grps = db.get_search_groups(aid)
        if grps:
            kb = [[InlineKeyboardButton(f"🗑 {g[1]}", callback_data=f'delgrp_{g[0]}')] for g in grps]
            kb.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text("🗑 O'chirish uchun tanlang:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            query.edit_message_text("ℹ️ Izlovchi guruhlar yo'q", reply_markup=back_button())
            
    elif data.startswith('delgrp_'):
        db.remove_search_group(int(data.split('_')[1]))
        query.edit_message_text("✅ Izlovchi guruh o'chirildi!", reply_markup=back_button())
        
    elif data == 'back_to_main':
        context.user_data.pop('waiting', None)
        if user_id == SUPER_ADMIN_ID:
            context.user_data.pop('viewing_admin', None)
            context.user_data.pop('is_super_admin_viewing', None)
            query.edit_message_text("🔐 Super Admin paneli:", reply_markup=super_admin_keyboard())
        elif db.is_admin(user_id, SUPER_ADMIN_ID):
            query.edit_message_text("🏠 Admin paneli:", reply_markup=admin_keyboard())

def handle_text(update: Update, context: CallbackContext):
    if not update.message or not update.message.text:
        return
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if not db.is_admin(user_id, SUPER_ADMIN_ID):
        return
    
    waiting = context.user_data.get('waiting')

    if waiting == 'admin_id' and user_id == SUPER_ADMIN_ID:
        try:
            nid = int(text)
            try:
                chat = context.bot.get_chat(nid)
                un = chat.username or chat.first_name or f"User_{nid}"
            except:
                un = f"User_{nid}"
            if db.add_admin(nid, un):
                update.message.reply_text(f"✅ Admin qo'shildi!\n\n👤 {un}\n🆔 {nid}", reply_markup=back_button())
            else:
                update.message.reply_text("ℹ️ Bu admin allaqachon mavjud!", reply_markup=back_button())
        except:
            update.message.reply_text("❌ Noto'g'ri ID format!", reply_markup=back_button())
        context.user_data.pop('waiting', None)
        
    elif waiting == 'api_phone' and user_id == SUPER_ADMIN_ID:
        phone = text.strip()
        if not phone.startswith('+'):
            update.message.reply_text("❌ Telefon raqam '+' bilan boshlanishi kerak!\n\nMisol: +998901234567", reply_markup=back_button())
            return
        
        context.user_data['temp_phone'] = phone
        context.user_data['waiting'] = 'api_id'
        update.message.reply_text(
            f"✅ Telefon raqam qabul qilindi: {phone}\n\n"
            "📝 Endi API ID yuboring:\n\n"
            "API ID va API Hash olish uchun:\n"
            "👉 https://my.telegram.org\n"
            "- Login qiling\n"
            "- API development tools\n"
            "- Create new application",
            reply_markup=back_button()
        )
        
    elif waiting == 'api_id' and user_id == SUPER_ADMIN_ID:
        try:
            api_id = int(text.strip())
            context.user_data['temp_api_id'] = api_id
            context.user_data['waiting'] = 'api_hash'
            update.message.reply_text(
                f"✅ API ID qabul qilindi: {api_id}\n\n"
                "📝 Endi API Hash yuboring:",
                reply_markup=back_button()
            )
        except:
            update.message.reply_text("❌ API ID raqam bo'lishi kerak!", reply_markup=back_button())
            
    elif waiting == 'api_hash' and user_id == SUPER_ADMIN_ID:
        api_hash = text.strip()
        api_id = context.user_data.get('temp_api_id')
        phone = context.user_data.get('temp_phone')
        
        if not api_id or not phone:
            update.message.reply_text("❌ Xatolik! Qaytadan boshlang.", reply_markup=back_button())
            context.user_data.pop('waiting', None)
            return
        
        update.message.reply_text("⏳ Telegram'ga ulanish va kod yuborish...\n\nBiroz kuting...")
        
        def auth_thread():
            try:
                client, session = run_async(create_telegram_session(api_id, api_hash, phone))
                
                if client:
                    pending_auth[user_id] = {
                        'client': client,
                        'phone': phone,
                        'api_id': api_id,
                        'api_hash': api_hash
                    }
                    context.user_data['waiting'] = 'telegram_code'
                    update.message.reply_text(
                        f"✅ Telegram'dan kod yuborildi!\n\n"
                        f"📱 {phone} raqamiga kelgan kodni yuboring:\n\n"
                        f"⚠️ Kod 5 yoki 6 raqamdan iborat",
                        reply_markup=back_button()
                    )
                elif session:
                    new_api_id = db.add_api(api_id, api_hash, phone, session)
                    update.message.reply_text(
                        f"✅ API muvaffaqiyatli qo'shildi!\n\n"
                        f"📱 {phone}\n"
                        f"🆔 {api_id}\n\n"
                        f"🔄 Userbot'ni qayta ishga tushiring!",
                        reply_markup=back_button()
                    )
                    context.user_data.pop('waiting', None)
                    context.user_data.pop('temp_phone', None)
                    context.user_data.pop('temp_api_id', None)
                else:
                    update.message.reply_text("❌ Ulanishda xatolik! Ma'lumotlarni tekshiring.", reply_markup=back_button())
                    context.user_data.pop('waiting', None)
                    
            except Exception as e:
                logger.error(f"Auth xato: {e}")
                update.message.reply_text(f"❌ Xatolik: {str(e)}", reply_markup=back_button())
                context.user_data.pop('waiting', None)
        
        thread = threading.Thread(target=auth_thread)
        thread.start()
        
    elif waiting == 'telegram_code' and user_id == SUPER_ADMIN_ID:
        code = text.strip()
        
        if not code.isdigit() or len(code) not in [5, 6]:
            update.message.reply_text("❌ Kod 5 yoki 6 raqamdan iborat bo'lishi kerak!", reply_markup=back_button())
            return
        
        auth_data = pending_auth.get(user_id)
        if not auth_data:
            update.message.reply_text("❌ Session muddati tugagan! Qaytadan boshlang.", reply_markup=back_button())
            context.user_data.pop('waiting', None)
            return
        
        update.message.reply_text("⏳ Kod tekshirilmoqda...\n\nBiroz kuting...")
        
        def verify_thread():
            try:
                session_string = run_async(verify_telegram_code(
                    auth_data['client'],
                    auth_data['phone'],
                    code
                ))
                
                if session_string:
                    new_api_id = db.add_api(
                        auth_data['api_id'],
                        auth_data['api_hash'],
                        auth_data['phone'],
                        session_string
                    )
                    update.message.reply_text(
                        f"✅ API muvaffaqiyatli qo'shildi!\n\n"
                        f"📱 {auth_data['phone']}\n"
                        f"🆔 {auth_data['api_id']}\n\n"
                        f"🔄 Userbot'ni qayta ishga tushiring!",
                        reply_markup=back_button()
                    )
                    pending_auth.pop(user_id, None)
                    context.user_data.pop('waiting', None)
                    context.user_data.pop('temp_phone', None)
                    context.user_data.pop('temp_api_id', None)
                else:
                    update.message.reply_text("❌ Noto'g'ri kod! Qaytadan urinib ko'ring.", reply_markup=back_button())
                    
            except Exception as e:
                logger.error(f"Verify xato: {e}")
                update.message.reply_text(f"❌ Xatolik: {str(e)}\n\nQaytadan urinib ko'ring.", reply_markup=back_button())
        
        thread = threading.Thread(target=verify_thread)
        thread.start()
        
    elif waiting == 'userbot_time' and user_id == SUPER_ADMIN_ID:
        if text.lower() == 'off':
            db.set_setting('userbot_schedule_enabled', 'false')
            update.message.reply_text("✅ Vaqt rejimi o'chirildi! Bot 24/7 ishlaydi.", reply_markup=back_button())
        else:
            try:
                times = text.split(':')
                if len(times) == 4:
                    stop = f"{times[0].zfill(2)}:{times[1].zfill(2)}"
                    start = f"{times[2].zfill(2)}:{times[3].zfill(2)}"
                    db.set_setting('userbot_stop_time', stop)
                    db.set_setting('userbot_start_time', start)
                    db.set_setting('userbot_schedule_enabled', 'true')
                    update.message.reply_text(
                        f"✅ Vaqt sozlamalari o'rnatildi!\n\n"
                        f"🌙 To'xtatish: {stop}\n"
                        f"🌅 Ishga tushirish: {start}",
                        reply_markup=back_button()
                    )
                else:
                    update.message.reply_text("❌ Noto'g'ri format! To'g'ri format: 00:00:02:00", reply_markup=back_button())
            except:
                update.message.reply_text("❌ Xatolik! To'g'ri format: 00:00:02:00", reply_markup=back_button())
        context.user_data.pop('waiting', None)
        
    elif waiting == 'keyword':
        aid = context.user_data.get('viewing_admin', user_id)
        db.add_keyword(aid, text)
        update.message.reply_text(f"✅ Kalit so'z qo'shildi: {text}", reply_markup=back_button())
        context.user_data.pop('waiting', None)
        
    elif waiting == 'private_group':
        aid = context.user_data.get('viewing_admin', user_id)
        if text.startswith("http"):
            db.add_private_group(aid, group_link=text, group_name="Link orqali qo'shilgan")
            update.message.reply_text("✅ Shaxsiy guruh qo'shildi!", reply_markup=back_button())
        else:
            try:
                gid = int(text)
                try:
                    chat = context.bot.get_chat(gid)
                    gn = chat.title or f"Guruh {gid}"
                except:
                    gn = f"Guruh {gid}"
                db.add_private_group(aid, group_id=gid, group_name=gn)
                update.message.reply_text(f"✅ Shaxsiy guruh qo'shildi: {gn}", reply_markup=back_button())
            except:
                update.message.reply_text("❌ Noto'g'ri ID format!", reply_markup=back_button())
        context.user_data.pop('waiting', None)
        
    elif waiting == 'search_group':
        aid = context.user_data.get('viewing_admin', user_id)
        sup = context.user_data.get('is_super_admin_viewing', False)
        if text.startswith("http"):
            suc, msg = db.add_search_group(aid, SUPER_ADMIN_ID, group_link=text, group_name="Link orqali qo'shilgan", bypass_limit=sup)
            update.message.reply_text(f"{'✅' if suc else '❌'} {msg}", reply_markup=back_button())
        else:
            try:
                gid = int(text)
                try:
                    chat = context.bot.get_chat(gid)
                    gn = chat.title or f"Guruh {gid}"
                except:
                    gn = f"Guruh {gid}"
                suc, msg = db.add_search_group(aid, SUPER_ADMIN_ID, group_id=gid, group_name=gn, bypass_limit=sup)
                update.message.reply_text(f"{'✅' if suc else '❌'} {msg}: {gn}", reply_markup=back_button())
            except:
                update.message.reply_text("❌ Noto'g'ri ID format!", reply_markup=back_button())
        context.user_data.pop('waiting', None)

def check_group_message(update: Update, context: CallbackContext):
    if not update.message or not update.message.text:
        return
    if update.message.chat.type not in ['group', 'supergroup']:
        return
    
    msg = update.message.text
    gid = update.message.chat.id
    uid = update.message.from_user.id
    un = update.message.from_user.username or update.message.from_user.first_name or "Unknown"
    gn = update.message.chat.title or "Unknown"
    
    matches = db.check_keywords_in_message(gid, msg)
    
    for m in matches:
        try:
            kb = [[InlineKeyboardButton("👤 Profil", url=f"tg://user?id={uid}")]]
            if m['private_group_id']:
                context.bot.send_message(
                    chat_id=m['private_group_id'],
                    text=f"🔍 Kalit so'z topildi! (Bot)\n\n📢 Guruh: {gn}\n👤 User: {un}\n🆔 ID: {uid}\n🔑 Kalit so'z: {m['keyword']}\n\n💬 Xabar:\n{msg[:200]}",
                    reply_markup=InlineKeyboardMarkup(kb)
                )
        except Exception as e:
            logger.error(f"Xabar yuborishda xato: {e}")

def main():
    db.init_db()
    
    if not db.get_setting('userbot_stop_time'):
        db.set_setting('userbot_stop_time', '00:00')
    if not db.get_setting('userbot_start_time'):
        db.set_setting('userbot_start_time', '02:00')
    if not db.get_setting('userbot_schedule_enabled'):
        db.set_setting('userbot_schedule_enabled', 'true')

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("id", get_chat_id))
    dp.add_handler(CallbackQueryHandler(button_callback))
    dp.add_handler(MessageHandler(Filters.text & Filters.private, handle_text))
    dp.add_handler(MessageHandler(Filters.text & Filters.group, check_group_message))

    logger.info("🚀 Bot ishga tushmoqda...")
    try:
        updater.start_polling()
        logger.info("✅ Bot muvaffaqiyatli ishga tushdi!")
        updater.idle()
    except KeyboardInterrupt:
        logger.info("⛔ Bot to'xtatildi (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Fatal xato: {e}")

if __name__ == '__main__':
    main()
