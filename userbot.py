import logging
import asyncio
from datetime import datetime, time, timedelta
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import database as db

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8332172370:AAHpj0H_6sss-bMoGizp1ulUFQkmkEdC_PA"
API_ID = 36799342
API_HASH = "fcdf748b56fb519c6900d02e25ae2d62"
PHONE = "+998931317231"
# This session string should be generated once and stored
SESSION_STRING = "1ApWapzMBu7tofZMURMSzo89mVMr9xLotyNvtPCmERdQUHiz6JYT-4lRg2Q9BIXhZ4vQKg91VtU5AuCcz6mA7Okorwah803VPKW9G_uJ2T6wbhW3_UARwiT0xQO-NmNzhYV3Y65AeH4qAhYPEZ8ytw7FbrEO0r9h4cVB7z2gfUsS6bd7a8xuwNpt5Glwb3VOB-RXFMd1Mhv5EF3pV-rnejmRPGr27VhZml9ATMiCwUJwd4OqAA5ygn-fs8C6HH_UriS6K2T5ASR6ACLXSU8WeGCjBloyJM632L0coc1ik4ZduUxmnX3tQGRo8MCu26-QfwKG6Uqi2_lI6rHcTQYjE-G-DDC3qHcs="

bot_instance = Bot(token=BOT_TOKEN)

async def send_notification(private_group_id, group_name, username, user_id, keyword, msg_text):
    try:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 Profilga o'tish", url=f"tg://user?id={user_id}")]
        ])
        
        if len(msg_text) > 500:
            msg_text = msg_text[:500] + "..."
        
        message_text = (
            f"🔍 Kalit so'z topildi!\n\n"
            f"📢 Guruh: {group_name}\n"
            f"👤 Kimdan: {username}\n"
            f"🆔 User ID: {user_id}\n"
            f"🔑 Kalit so'z: {keyword}\n\n"
            f"💬 Xabar:\n{msg_text}"
        )
        
        await asyncio.to_thread(
            bot_instance.send_message,
            chat_id=private_group_id,
            text=message_text,
            reply_markup=keyboard
        )
        logger.info(f"✅ Xabar yuborildi: {group_name} -> {keyword}")
    except Exception as e:
        logger.error(f"❌ Xabar yuborishda xato: {e}")

async def message_handler(event):
    try:
        if not event.message or not event.message.text:
            return
        
        chat = await event.get_chat()
        group_id = event.chat_id
        msg_text = event.message.text
        group_name = getattr(chat, 'title', 'Noma\'lum guruh')
        
        sender = await event.get_sender()
        if not sender:
            return
        
        user_id = sender.id
        username = getattr(sender, 'username', None) or getattr(sender, 'first_name', 'Noma\'lum')
        
        # Check database for matches
        matches = db.check_keywords_in_message(group_id, msg_text)
        
        for match in matches:
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
        logger.error(f"❌ Message handler xatosi: {e}")

async def run_userbot():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    
    @client.on(events.NewMessage())
    async def handler(event):
        await message_handler(event)
    
    await client.start(phone=PHONE)
    logger.info("✅ Userbot ishga tushdi!")
    await client.run_until_disconnected()

async def main():
    db.init_db()
    
    while True:
        try:
            schedule_enabled = db.get_setting('userbot_schedule_enabled', 'true')
            
            if schedule_enabled != 'true':
                logger.info("⏰ Rejali restart o'chirilgan. 24/7 ishlamoqda...")
                await run_userbot()
                continue
            
            stop_time_str = db.get_setting('userbot_stop_time', '00:00')
            start_time_str = db.get_setting('userbot_start_time', '02:00')
            
            now = datetime.now()
            stop_h, stop_m = map(int, stop_time_str.split(':'))
            start_h, start_m = map(int, start_time_str.split(':'))
            
            stop_time = now.replace(hour=stop_h, minute=stop_m, second=0, microsecond=0)
            if now >= stop_time:
                stop_time += timedelta(days=1)
            
            seconds_until_stop = (stop_time - now).total_seconds()
            logger.info(f"⏰ Userbot {stop_time_str} gacha ishlaydi ({int(seconds_until_stop/3600)} soat)")
            
            try:
                await asyncio.wait_for(run_userbot(), timeout=seconds_until_stop)
            except asyncio.TimeoutError:
                logger.info(f"🌙 Soat {stop_time_str} - Userbot to'xtatilmoqda...")
            
            # Wait until start time
            now = datetime.now()
            start_time = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
            if now >= start_time:
                start_time += timedelta(days=1)
            
            sleep_seconds = (start_time - now).total_seconds()
            logger.info(f"💤 {int(sleep_seconds/3600)} soat kutish ({stop_time_str} - {start_time_str})...")
            await asyncio.sleep(sleep_seconds)
            
        except Exception as e:
            logger.error(f"❌ Userbotda xato: {e}")
            await asyncio.sleep(60) # Wait before retry

if __name__ == '__main__':
    asyncio.run(main())
