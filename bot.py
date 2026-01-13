# bot.py - Telegram Bot
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import database as db

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8332172370:AAHpj0H_6sss-bMoGizp1ulUFQkmkEdC_PA"
SUPER_ADMIN_ID = 7740552653

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
        update.message.reply_text("🔐 Super Admin!", reply_markup=super_admin_keyboard())
    elif db.is_admin(user_id, SUPER_ADMIN_ID):
        update.message.reply_text(f"👋 {username}!", reply_markup=admin_keyboard())
    else:
        keyboard = [[InlineKeyboardButton("👤 Admin", url=f"tg://user?id={SUPER_ADMIN_ID}")]]
        update.message.reply_text(f"👋 {username}!\n\n⚠️ Faqat adminlar!", reply_markup=InlineKeyboardMarkup(keyboard))

def get_chat_id(update: Update, context: CallbackContext):
    update.message.reply_text(f"📊 ID: {update.effective_chat.id}")

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == 'add_admin' and user_id == SUPER_ADMIN_ID:
        context.user_data['waiting'] = 'admin_id'
        query.edit_message_text("📝 Admin ID:", reply_markup=back_button())
    elif data == 'list_admins' and user_id == SUPER_ADMIN_ID:
        admins = db.get_all_admins()
        if admins:
            kb = [[InlineKeyboardButton(f"{u} ({i})", url=f"tg://user?id={i}")] for i, u in admins]
            kb.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text(f"📋 Adminlar ({len(admins)}):", reply_markup=InlineKeyboardMarkup(kb))
        else:
            query.edit_message_text("ℹ️ Yo'q", reply_markup=back_button())
    elif data == 'remove_admin' and user_id == SUPER_ADMIN_ID:
        admins = db.get_all_admins()
        if admins:
            kb = [[InlineKeyboardButton(f"🗑 {u}", callback_data=f'rmadm_{i}')] for i, u in admins]
            kb.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text("🗑 Tanlang:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            query.edit_message_text("ℹ️ Yo'q", reply_markup=back_button())
    elif data.startswith('rmadm_') and user_id == SUPER_ADMIN_ID:
        db.remove_admin(int(data.split('_')[1]))
        query.edit_message_text("✅ O'chirildi!", reply_markup=back_button())
    elif data == 'enter_admin_room' and user_id == SUPER_ADMIN_ID:
        admins = db.get_all_admins()
        if admins:
            kb = [[InlineKeyboardButton(f"🚪 {u}", callback_data=f'enter_{i}')] for i, u in admins]
            kb.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text("🚪 Tanlang:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            query.edit_message_text("ℹ️ Yo'q", reply_markup=back_button())
    elif data.startswith('enter_') and user_id == SUPER_ADMIN_ID:
        admin_id = int(data.split('_')[1])
        context.user_data['viewing_admin'] = admin_id
        context.user_data['is_super_admin_viewing'] = True
        query.edit_message_text(f"🏠 Admin ({admin_id}):", reply_markup=admin_keyboard())
    elif data == 'userbot_api_menu' and user_id == SUPER_ADMIN_ID:
        query.edit_message_text("🤖 API:", reply_markup=userbot_api_keyboard())
    elif data == 'add_api' and user_id == SUPER_ADMIN_ID:
        context.user_data['waiting'] = 'api_credentials'
        query.edit_message_text("📝 Format:\n<code>API_ID:API_HASH:PHONE</code>\n\nMisol:\n<code>12345678:abc123:+998901234567</code>", reply_markup=back_button(), parse_mode='HTML')
    elif data == 'list_apis' and user_id == SUPER_ADMIN_ID:
        apis = db.get_all_apis()
        if apis:
            text = "📋 API ro'yxati:\n\n"
            for i, api in enumerate(apis, 1):
                st = "✅" if api['is_active'] else "❌"
                text += f"{i}. {st} {api['phone_number']}\n   ID: {api['api_id']}\n   Hash: {api['api_hash'][:10]}...\n"
                if api['session_string']:
                    text += "   ✅ Session\n"
                text += "\n"
            query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data='userbot_api_menu')]]))
        else:
            query.edit_message_text("ℹ️ Yo'q", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data='userbot_api_menu')]]))
    elif data == 'remove_api' and user_id == SUPER_ADMIN_ID:
        apis = db.get_all_apis()
        if apis:
            kb = [[InlineKeyboardButton(f"🗑 {a['phone_number']}", callback_data=f'rmapi_{a["id"]}')] for a in apis]
            kb.append([InlineKeyboardButton("⬅️ Ortga", callback_data='userbot_api_menu')])
            query.edit_message_text("🗑 Tanlang:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            query.edit_message_text("ℹ️ Yo'q", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data='userbot_api_menu')]]))
    elif data.startswith('rmapi_') and user_id == SUPER_ADMIN_ID:
        db.remove_api(int(data.split('_')[1]))
        query.edit_message_text("✅ O'chirildi!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data='userbot_api_menu')]]))
    elif data == 'check_api' and user_id == SUPER_ADMIN_ID:
        apis = db.get_all_apis()
        if apis:
            text = "🔍 API:\n\n"
            for api in apis:
                text += f"📱 {api['phone_number']}:\n"
                if api['is_active'] and api['session_string']:
                    text += "   ✅ Aktiv\n"
                elif api['session_string']:
                    text += "   ⚠️ Session mavjud\n"
                else:
                    text += "   ❌ Yo'q\n"
                text += "\n"
            kb = [[InlineKeyboardButton("🔄 Yangilash", callback_data='check_api')], [InlineKeyboardButton("⬅️ Ortga", callback_data='userbot_api_menu')]]
            query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
        else:
            query.edit_message_text("ℹ️ Yo'q", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data='userbot_api_menu')]]))
    elif data == 'userbot_settings' and user_id == SUPER_ADMIN_ID:
        stop = db.get_setting('userbot_stop_time', '00:00')
        start = db.get_setting('userbot_start_time', '02:00')
        enabled = db.get_setting('userbot_schedule_enabled', 'true')
        st = "✅" if enabled == 'true' else "❌"
        text = f"⚙️ Sozlamalar:\n\n⏰ To'xtatish: {st}\n"
        if enabled == 'true':
            text += f"🌙 Stop: {stop}\n🌅 Start: {start}\n\n"
        text += "Format: <code>00:00:02:00</code>\nO'chirish: <code>off</code>"
        kb = [[InlineKeyboardButton("❌ O'chirish", callback_data='userbot_disable_schedule')], [InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')]]
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        context.user_data['waiting'] = 'userbot_time'
    elif data == 'userbot_disable_schedule' and user_id == SUPER_ADMIN_ID:
        db.set_setting('userbot_schedule_enabled', 'false')
        query.edit_message_text("✅ O'chirildi! 24/7", reply_markup=back_button())
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
            text = f"🤖 Status:\n\n👥 Adminlar: {adm}\n🔑 Kalit: {kw}\n🔍 Izlovchi: {sg}\n📢 Shaxsiy: {pg}\n🤖 API: {act}/{tot}\n\n💡 Tekshiring!"
            kb = [[InlineKeyboardButton("🔄 Yangilash", callback_data='check_userbot')], [InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')]]
            query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            query.edit_message_text(f"❌ {e}", reply_markup=back_button())
    elif data == 'add_keyword':
        context.user_data['waiting'] = 'keyword'
        query.edit_message_text("📝 Kalit so'z:", reply_markup=back_button())
    elif data == 'view_keywords':
        aid = context.user_data.get('viewing_admin', user_id)
        kws = db.get_keywords(aid)
        if kws:
            text = "📋 Kalit so'zlar:\n\n" + "\n".join([f"{i}. {k}" for i, (_, k) in enumerate(kws, 1)]) + f"\n\n💾 {len(kws)}"
            query.edit_message_text(text, reply_markup=back_button())
        else:
            query.edit_message_text("ℹ️ Yo'q", reply_markup=back_button())
    elif data == 'delete_keyword':
        aid = context.user_data.get('viewing_admin', user_id)
        kws = db.get_keywords(aid)
        if kws:
            kb = [[InlineKeyboardButton(f"🗑 {k}", callback_data=f'delkw_{i}')] for i, k in kws]
            kb.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text("🗑 Tanlang:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            query.edit_message_text("ℹ️ Yo'q", reply_markup=back_button())
    elif data.startswith('delkw_'):
        db.remove_keyword(int(data.split('_')[1]))
        query.edit_message_text("✅ O'chirildi!", reply_markup=back_button())
    elif data == 'add_private_group':
        context.user_data['waiting'] = 'private_group'
        query.edit_message_text("📝 Guruh ID/link:", reply_markup=back_button())
    elif data == 'view_private_group':
        aid = context.user_data.get('viewing_admin', user_id)
        gn = db.get_private_group_name(aid)
        query.edit_message_text(f"📢 {gn if gn else 'Yo\'q'}", reply_markup=back_button())
    elif data == 'delete_private_group':
        aid = context.user_data.get('viewing_admin', user_id)
        gn = db.get_private_group_name(aid)
        if gn:
            kb = [[InlineKeyboardButton(f"🗑 {gn}", callback_data=f'delpr_{aid}')], [InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')]]
            query.edit_message_text("🗑 O'chirish:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            query.edit_message_text("ℹ️ Yo'q", reply_markup=back_button())
    elif data.startswith('delpr_'):
        db.remove_private_group(int(data.split('_')[1]))
        query.edit_message_text("✅ O'chirildi!", reply_markup=back_button())
    elif data == 'add_search_group':
        aid = context.user_data.get('viewing_admin', user_id)
        grps = db.get_search_groups(aid)
        context.user_data['waiting'] = 'search_group'
        lim = f"{len(grps)}" if context.user_data.get('is_super_admin_viewing') else f"{len(grps)}/100"
        query.edit_message_text(f"📝 ID/link:\n\n📊 {lim}", reply_markup=back_button())
    elif data == 'view_search_groups':
        aid = context.user_data.get('viewing_admin', user_id)
        grps = db.get_search_groups(aid)
        if grps:
            text = "📋 Izlovchi:\n\n" + "\n".join([f"{i}. {g[1]}" for i, g in enumerate(grps, 1)])
            lim = f"{len(grps)}" if context.user_data.get('is_super_admin_viewing') else f"{len(grps)}/100"
            text += f"\n\n💾 {lim}"
            query.edit_message_text(text, reply_markup=back_button())
        else:
            query.edit_message_text("ℹ️ Yo'q", reply_markup=back_button())
    elif data == 'delete_search_group':
        aid = context.user_data.get('viewing_admin', user_id)
        grps = db.get_search_groups(aid)
        if grps:
            kb = [[InlineKeyboardButton(f"🗑 {g[1]}", callback_data=f'delgrp_{g[0]}')] for g in grps]
            kb.append([InlineKeyboardButton("⬅️ Ortga", callback_data='back_to_main')])
            query.edit_message_text("🗑 Tanlang:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            query.edit_message_text("ℹ️ Yo'q", reply_markup=back_button())
    elif data.startswith('delgrp_'):
        db.remove_search_group(int(data.split('_')[1]))
        query.edit_message_text("✅ O'chirildi!", reply_markup=back_button())
    elif data == 'back_to_main':
        context.user_data.pop('waiting', None)
        if user_id == SUPER_ADMIN_ID:
            context.user_data.pop('viewing_admin', None)
            context.user_data.pop('is_super_admin_viewing', None)
            query.edit_message_text("🔐 Super Admin:", reply_markup=super_admin_keyboard())
        elif db.is_admin(user_id, SUPER_ADMIN_ID):
            query.edit_message_text("🏠 Admin:", reply_markup=admin_keyboard())

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
                update.message.reply_text(f"✅ Qo'shildi!\n\n{un}\n🆔 {nid}", reply_markup=back_button())
            else:
                update.message.reply_text("ℹ️ Mavjud!", reply_markup=back_button())
        except:
            update.message.reply_text("❌ Xato ID!", reply_markup=back_button())
        context.user_data.pop('waiting', None)
    elif waiting == 'api_credentials' and user_id == SUPER_ADMIN_ID:
        try:
            parts = text.split(':')
            if len(parts) == 3:
                aid = int(parts[0].strip())
                ahash = parts[1].strip()
                phone = parts[2].strip()
                context.user_data['temp_api_id'] = aid
                context.user_data['temp_api_hash'] = ahash
                context.user_data['temp_phone'] = phone
                context.user_data['waiting'] = 'telegram_code'
                update.message.reply_text(f"📱 Qabul!\n\n📞 {phone}\n🆔 {aid}\n\n📝 Telegram kodi:", reply_markup=back_button())
            else:
                update.message.reply_text("❌ Format: <code>ID:HASH:PHONE</code>", reply_markup=back_button(), parse_mode='HTML')
        except:
            update.message.reply_text("❌ Xato!", reply_markup=back_button())
    elif waiting == 'telegram_code' and user_id == SUPER_ADMIN_ID:
        code = text.strip()
        if not code.isdigit() or len(code) not in [5, 6]:
            update.message.reply_text("❌ 5-6 raqam!", reply_markup=back_button())
            return
        aid = context.user_data.get('temp_api_id')
        ahash = context.user_data.get('temp_api_hash')
        phone = context.user_data.get('temp_phone')
        if db.add_api(aid, ahash, phone, code):
            update.message.reply_text(f"✅ API qo'shildi!\n\n📱 {phone}\n🆔 {aid}\n\n🔄 Userbot qayta ishga tushiring!", reply_markup=back_button())
        else:
            update.message.reply_text("❌ Xato! Qayta urinib ko'ring.", reply_markup=back_button())
        context.user_data.pop('temp_api_id', None)
        context.user_data.pop('temp_api_hash', None)
        context.user_data.pop('temp_phone', None)
        context.user_data.pop('waiting', None)
    elif waiting == 'userbot_time' and user_id == SUPER_ADMIN_ID:
        if text.lower() == 'off':
            db.set_setting('userbot_schedule_enabled', 'false')
            update.message.reply_text("✅ O'chirildi! 24/7", reply_markup=back_button())
        else:
            try:
                times = text.split(':')
                if len(times) == 4:
                    stop = f"{times[0].zfill(2)}:{times[1].zfill(2)}"
                    start = f"{times[2].zfill(2)}:{times[3].zfill(2)}"
                    db.set_setting('userbot_stop_time', stop)
                    db.set_setting('userbot_start_time', start)
                    db.set_setting('userbot_schedule_enabled', 'true')
                    update.message.reply_text(f"✅ Sozlandi!\n\n🌙 {stop}\n🌅 {start}", reply_markup=back_button())
                else:
                    update.message.reply_text("❌ Format: 00:00:02:00", reply_markup=back_button())
            except:
                update.message.reply_text("❌ Xato!", reply_markup=back_button())
        context.user_data.pop('waiting', None)
    elif waiting == 'keyword':
        aid = context.user_data.get('viewing_admin', user_id)
        db.add_keyword(aid, text)
        update.message.reply_text(f"✅ {text}", reply_markup=back_button())
        context.user_data.pop('waiting', None)
    elif waiting == 'private_group':
        aid = context.user_data.get('viewing_admin', user_id)
        if text.startswith("http"):
            db.add_private_group(aid, group_link=text, group_name="Link")
            update.message.reply_text("✅ Qo'shildi!", reply_markup=back_button())
        else:
            try:
                gid = int(text)
                try:
                    chat = context.bot.get_chat(gid)
                    gn = chat.title or f"Guruh {gid}"
                except:
                    gn = f"Guruh {gid}"
                db.add_private_group(aid, group_id=gid, group_name=gn)
                update.message.reply_text(f"✅ {gn}", reply_markup=back_button())
            except:
                update.message.reply_text("❌ Xato!", reply_markup=back_button())
        context.user_data.pop('waiting', None)
    elif waiting == 'search_group':
        aid = context.user_data.get('viewing_admin', user_id)
        sup = context.user_data.get('is_super_admin_viewing', False)
        if text.startswith("http"):
            suc, msg = db.add_search_group(aid, SUPER_ADMIN_ID, group_link=text, group_name="Link", bypass_limit=sup)
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
                update.message.reply_text("❌ Xato!", reply_markup=back_button())
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
                    text=f"🔍 Topildi! (Bot)\n\n📢 {gn}\n👤 {un}\n🆔 {uid}\n🔑 {m['keyword']}\n\n💬 {msg[:200]}",
                    reply_markup=InlineKeyboardMarkup(kb)
                )
        except Exception as e:
            logger.error(f"Xato: {e}")

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
        logger.info("✅ Bot ishga tushdi!")
        updater.idle()
    except KeyboardInterrupt:
        logger.info("⛔ Bot to'xtatildi")
    except Exception as e:
        logger.error(f"❌ Xato: {e}")

if __name__ == '__main__':
    main()
