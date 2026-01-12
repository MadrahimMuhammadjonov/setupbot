# ============================================
# userbot.py - Telegram Userbot
# ============================================

import logging
import asyncio
from datetime import datetime, time
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telegram import Bot
from telegram.error import TelegramError
import database as db

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8332172370:AAHpj0H_6sss-bMoGizp1ulUFQkmkEdC_PA"
SUPER_ADMIN_ID = 7740552653
PHONE = "+998931317231"
API_ID = 36799342
API_HASH = "fcdf748b56fb519c6900d02e25ae2d62"
SESSION_STRING = "1ApWapzMBu7tofZMURMSzo89mVMr9xLotyNvtPCmERdQUHiz6JYT-4lRg2Q9BIXhZ4vQKg91VtU5AuCcz6mA7Okorwah803VPKW9G_uJ2T6wbhW3_UARwiT0xQO-NmNzhYV3Y65AeH4qAhYPEZ8ytw7FbrEO0r9h4cVB7z2gfUsS6bd7a8xuwNpt5Glwb3VOB-RXFMd1Mhv5EF3pV-rnejmRPGr27VhZml9ATMiCwUJwd4OqAA5ygn-fs8C6HH_UriS6K2T5ASR6ACLXSU8WeGCjBloyJM632L0coc1ik4ZduUxmnX3tQGRo8MCu26-QfwKG6Uqi2_lI6rHcTQYjE-G-DDC3qHcs="

# Bot instance xabar yuborish uchun
bot = None

# ==================== USERBOT ====================
async def init_userbot():
    """Userbot ishga tushirish"""
    global bot
    
    try:
        # Bot instanceni yaratish
        bot = Bot(token=BOT_TOKEN)
        
        # Userbot clientni yaratish
        client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
        await client.start(phone=PHONE)
        logger.info("✅ Userbot ishga tushdi")

        @client.on(events.NewMessage())
        async def userbot_message_handler(event):
            """Userbot xabar handler"""
            try:
                if not event.message or not event.message.text:
                    return
                
                # Chat turini tekshirish
                chat = await event.get_chat()
                if not getattr(chat, 'megagroup', False):
                    return
                
                group_id = event.chat_id
                msg_text = event.message.text
                
                # Yuboruvchi ma'lumotlari
                sender = await event.get_sender()
                user_id = sender.id
                username = sender.username or getattr(sender, 'first_name', None) or "Unknown"
                group_name = getattr(chat, 'title', 'Unknown group')
                
                # Kalit so'zlarni tekshirish
                matches = db.check_keywords_in_message(group_id, msg_text)
                
                for match in matches:
                    try:
                        if bot and match['private_group_id']:
                            # Xabarni shaxsiy guruhga yuborish
                            await bot.send_message(
                                chat_id=match['private_group_id'],
                                text=(f"🔍 Kalit so'z topildi! (Userbot)\n\n"
                                      f"📢 Guruh: {group_name}\n"
                                      f"👤 Foydalanuvchi: {username}\n"
                                      f"🆔 User ID: {user_id}\n"
                                      f"🔑 Kalit so'z: {match['keyword']}\n\n"
                                      f"💬 Xabar:\n{msg_text}"),
                                reply_markup={
                                    'inline_keyboard': [[{
                                        'text': '👤 Profil',
                                        'url': f'tg://user?id={user_id}'
                                    }]]
                                }
                            )
                        else:
                            logger.error("Bot instance yoki private_group_id mavjud emas")
                    except TelegramError as e:
                        logger.error(f"Userbot xabar yuborishda xato: {e}")
                    except Exception as e:
                        logger.error(f"Userbot xabar yuborishda umumiy xato: {e}")
                        
            except Exception as e:
                logger.error(f"Userbot handler xatosi: {e}")

        logger.info("✅ Userbot handler qo'shildi")
        return client
        
    except Exception as e:
        logger.error(f"Userbot ishga tushirishda xato: {e}")
        return None

async def schedule_userbot_restart(client):
    """Userbot kundalik to'xtatish va qayta ishga tushirish"""
    while True:
        now = datetime.now()
        
        # Soat 00:00 da to'xtatish
        midnight = datetime.combine(now.date(), time(0, 0))
        if now >= midnight:
            midnight = datetime.combine(now.date(), time(0, 0)) + timedelta(days=1)
        
        seconds_until_midnight = (midnight - now).total_seconds()
        
        logger.info(f"⏰ Userbot soat 00:00 da to'xtatiladi ({int(seconds_until_midnight/3600)} soatdan keyin)")
        
        # Soat 00:00 gacha kutish
        await asyncio.sleep(seconds_until_midnight)
        
        logger.info("🌙 Soat 00:00 - Userbot to'xtatilmoqda...")
        await client.disconnect()
        
        # Soat 02:00 gacha kutish (2 soat)
        await asyncio.sleep(2 * 3600)
        
        logger.info("🌅 Soat 02:00 - Userbot qayta ishga tushmoqda...")
        await client.connect()
        logger.info("✅ Userbot qayta ishga tushdi")

# ==================== MAIN ====================
async def main():
    """Userbotni ishga tushirish"""
    db.init_db()
    
    logger.info("🚀 Userbot ishga tushmoqda...")
    
    client = await init_userbot()
    
    if client:
        logger.info("✅ Userbot tayyor!")
        
        # Kundalik restart schedulerni ishga tushirish
        # asyncio.create_task(schedule_userbot_restart(client))
        # ESLATMA: Kundalik restart kerak bo'lsa yuqoridagi qatorni uncomment qiling
        
        # Userbot doim ishlab turishi
        await client.run_until_disconnected()
    else:
        logger.error("❌ Userbot ishga tushmadi!")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⛔ Userbot to'xtatildi")
    except Exception as e:
        logger.error(f"❌ Xato: {e}")
