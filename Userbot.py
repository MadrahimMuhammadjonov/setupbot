# ============================================
# userbot.py - Telegram Userbot (To'liq versiya)
# ============================================

import logging
import asyncio
from datetime import datetime, time, timedelta
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
import database as db

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('userbot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8332172370:AAHpj0H_6sss-bMoGizp1ulUFQkmkEdC_PA"
SUPER_ADMIN_ID = 7740552653
PHONE = "+998931317231"
API_ID = 36799342
API_HASH = "fcdf748b56fb519c6900d02e25ae2d62"
SESSION_STRING = "1ApWapzMBu7tofZMURMSzo89mVMr9xLotyNvtPCmERdQUHiz6JYT-4lRg2Q9BIXhZ4vQKg91VtU5AuCcz6mA7Okorwah803VPKW9G_uJ2T6wbhW3_UARwiT0xQO-NmNzhYV3Y65AeH4qAhYPEZ8ytw7FbrEO0r9h4cVB7z2gfUsS6bd7a8xuwNpt5Glwb3VOB-RXFMd1Mhv5EF3pV-rnejmRPGr27VhZml9ATMiCwUJwd4OqAA5ygn-fs8C6HH_UriS6K2T5ASR6ACLXSU8WeGCjBloyJM632L0coc1ik4ZduUxmnX3tQGRo8MCu26-QfwKG6Uqi2_lI6rHcTQYjE-G-DDC3qHcs="

bot_instance = None

# ==================== XABAR YUBORISH ====================
async def send_notification(private_group_id, group_name, username, user_id, keyword, msg_text):
    """Kalit so'z topilganda shaxsiy guruhga xabar yuborish"""
    global bot_instance
    
    try:
        if not bot_instance:
            bot_instance = Bot(token=BOT_TOKEN)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 Profil", url=f"tg://user?id={user_id}")]
        ])
        
        if len(msg_text) > 500:
            msg_text = msg_text[:500] + "..."
        
        message_text = (
            f"🔍 Kalit so'z topildi! (Userbot)\n\n"
            f"📢 Guruh: {group_name}\n"
            f"👤 Foydalanuvchi: {username}\n"
            f"🆔 User ID: {user_id}\n"
            f"🔑 Kalit so'z: {keyword}\n\n"
            f"💬 Xabar:\n{msg_text}"
        )
        
        await bot_instance.send_message(
            chat_id=private_group_id,
            text=message_text,
            reply_markup=keyboard
        )
        
        logger.info(f"✅ Xabar yuborildi: Guruh={group_name}, Keyword={keyword}")
        
    except TelegramError as e:
        logger.error(f"❌ Telegram xato: {e}")
    except Exception as e:
        logger.error(f"❌ Xabar yuborishda xato: {e}")

# ==================== USERBOT HANDLER ====================
async def message_handler(event):
    """Barcha xabarlarni handle qilish"""
    try:
        if not event.message or not event.message.text:
            return
        
        chat = await event.get_chat()
        
        if not hasattr(chat, 'megagroup'):
            return
        
        if not chat.megagroup:
            return
        
        group_id = event.chat_id
        msg_text = event.message.text
        group_name = getattr(chat, 'title', 'Unknown')
        
        sender = await event.get_sender()
        if not sender:
            return
        
        user_id = sender.id
        username = sender.username if sender.username else (sender.first_name if sender.first_name else "Unknown")
        
        logger.info(f"📨 Xabar: Guruh={group_name} (ID: {group_id}), User={username}")
        
        matches = db.check_keywords_in_message(group_id, msg_text)
        
        if matches:
            logger.info(f"🔍 {len(matches)} ta kalit so'z topildi!")
            
            for match in matches:
                try:
                    if match['private_group_id']:
                        await send_notification(
                            match['private_group_id'],
                            group_name,
                            username,
                            user_id,
                            match['keyword'],
                            msg_text
                        )
                except Exception as e:
                    logger.error(f"❌ Match handle qilishda xato: {e}")
        
    except Exception as e:
        logger.error(f"❌ Message handler xatosi: {e}")

# ==================== USERBOT ISHGA TUSHIRISH ====================
async def start_userbot():
    """Userbot ishga tushirish"""
    try:
        db.init_db()
        logger.info("✅ Database initialized")
        
        client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
        
        await client.start(phone=PHONE)
        logger.info("✅ Userbot ulanmoqda...")
        
        me = await client.get_me()
        logger.info(f"✅ Userbot ishga tushdi: {me.first_name} (@{me.username})")
        
        @client.on(events.NewMessage())
        async def handler(event):
            await message_handler(event)
        
        logger.info("✅ Message handler qo'shildi")
        logger.info("🎯 Userbot barcha xabarlarni kuzatyapti...")
        
        await client.run_until_disconnected()
        
    except Exception as e:
        logger.error(f"❌ Userbot ishga tushirishda xato: {e}")
        raise

# ==================== KUNDALIK RESTART ====================
async def start_with_schedule():
    """Userbot kundalik restart bilan ishga tushirish"""
    
    while True:
        try:
            logger.info("🚀 Userbot ishga tushmoqda...")
            
            schedule_enabled = db.get_setting('userbot_schedule_enabled', 'true')
            
            if schedule_enabled != 'true':
                logger.info("⏰ Kundalik restart o'chirilgan. 24/7 ishlamoqda...")
                await start_userbot()
                continue
            
            stop_time_str = db.get_setting('userbot_stop_time', '00:00')
            start_time_str = db.get_setting('userbot_start_time', '02:00')
            
            stop_h, stop_m = map(int, stop_time_str.split(':'))
            start_h, start_m = map(int, start_time_str.split(':'))
            
            now = datetime.now()
            
            stop_today = datetime.combine(now.date(), time(stop_h, stop_m))
            if now >= stop_today:
                stop_today = datetime.combine(now.date() + timedelta(days=1), time(stop_h, stop_m))
            
            seconds_until_stop = (stop_today - now).total_seconds()
            
            logger.info(f"⏰ Userbot {stop_time_str} da to'xtatiladi ({int(seconds_until_stop/3600)} soat {int((seconds_until_stop%3600)/60)} daqiqa)")
            
            try:
                await asyncio.wait_for(start_userbot(), timeout=seconds_until_stop)
            except asyncio.TimeoutError:
                logger.info(f"🌙 Soat {stop_time_str} - Userbot to'xtatilmoqda...")
            
            start_tomorrow = datetime.combine(now.date() + timedelta(days=1), time(start_h, start_m))
            sleep_seconds = (start_tomorrow - datetime.now()).total_seconds()
            
            logger.info(f"💤 {int(sleep_seconds/3600)} soat {int((sleep_seconds%3600)/60)} daqiqa kutish ({stop_time_str} - {start_time_str})...")
            await asyncio.sleep(sleep_seconds)
            
            logger.info(f"🌅 Soat {start_time_str} - Qayta ishga tushirish...")
            
        except Exception as e:
            logger.error(f"❌ Xato: {e}")
            logger.info("⏳ 5 daqiqadan keyin qayta urinish...")
            await asyncio.sleep(300)

# ==================== MAIN ====================
async def main():
    """Asosiy funksiya"""
    logger.info("=" * 60)
    logger.info("🤖 USERBOT ISHGA TUSHMOQDA")
    logger.info("=" * 60)
    
    db.init_db()
    
    schedule_enabled = db.get_setting('userbot_schedule_enabled', 'true')
    
    if schedule_enabled == 'true':
        logger.info("⏰ Kundalik restart rejimi yoqilgan")
        await start_with_schedule()
    else:
        logger.info("⏰ Kundalik restart o'chirilgan. 24/7 ishlash rejimi")
        await start_userbot()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⛔ Userbot to'xtatildi (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Fatal xato: {e}")
        import traceback
        traceback.print_exc()
