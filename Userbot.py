import logging
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import database as db

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8332172370:AAHpj0H_6sss-bMoGizp1ulUFQkmkEdC_PA"
bot_instance = Bot(token=BOT_TOKEN)

async def send_notification(private_group_id, group_name, username, user_id, keyword, msg_text):
    try:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("👤 Profil", url=f"tg://user?id={user_id}")]])
        message_text = (
            f"🔍 Kalit so'z topildi! (Userbot)\n\n"
            f"📢 Guruh: {group_name}\n"
            f"👤 User: {username}\n"
            f"🆔 ID: {user_id}\n"
            f"🔑 Kalit so'z: {keyword}\n\n"
            f"💬 Xabar:\n{msg_text[:500]}"
        )
        await bot_instance.send_message(chat_id=private_group_id, text=message_text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Notification error: {e}")

async def start_userbot(api_data):
    client = TelegramClient(StringSession(api_data['session_string']), api_data['api_id'], api_data['api_hash'])
    
    @client.on(events.NewMessage)
    async def handler(event):
        if not event.is_group or not event.message.text:
            return
        
        group_id = event.chat_id
        msg_text = event.message.text
        
        matches = db.check_keywords_in_message(group_id, msg_text)
        if matches:
            chat = await event.get_chat()
            group_name = getattr(chat, 'title', 'Unknown')
            sender = await event.get_sender()
            user_id = sender.id if sender else 0
            username = getattr(sender, 'username', 'Unknown') or getattr(sender, 'first_name', 'Unknown')
            
            for m in matches:
                if m['private_group_id']:
                    await send_notification(m['private_group_id'], group_name, username, user_id, m['keyword'], msg_text)

    try:
        await client.start()
        logger.info(f"✅ Userbot started: {api_data['phone_number']}")
        await client.run_until_disconnected()
    except Exception as e:
        logger.error(f"❌ Userbot error ({api_data['phone_number']}): {e}")
        db.update_api_status(api_data['id'], 0)

async def main():
    db.init_db()
    while True:
        active_apis = db.get_active_apis()
        tasks = []
        for api in active_apis:
            tasks.append(start_userbot(api))
        
        if tasks:
            await asyncio.gather(*tasks)
        else:
            logger.info("No active userbots. Checking again in 60s...")
            await asyncio.sleep(60)

if __name__ == '__main__':
    asyncio.run(main())
