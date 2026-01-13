# userbot.py - Telegram Userbot
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

BOT_TOKEN = "8332172370:AAHpj0H_6sss-bMoGizp1ulUFQkmkEdC_PA"
SUPER_ADMIN_ID = 7740552653

bot_instance = None
active_clients = []

async def send_notification(private_group_id, group_name, username, user_id, keyword, msg_text):
    global bot_instance
    try:
        if not bot_instance:
            bot_instance = Bot(token=BOT_TOKEN)
        
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("👤 Profil", url=f"tg://user?id={user_id}")]])
        
        if len(msg_text) > 500:
            msg_text = msg_text[:500] + "..."
        
        message_text = (
            f"🔍 Kalit so'z topildi! (Userbot)\n\n"
            f"📢 Guruh: {group_name}\n"
            f"👤 User: {username}\n"
            f"🆔 ID: {user_id}\n"
            f"🔑 Kalit: {keyword}\n\n"
            f"💬 Xabar:\n{msg_text}"
        )
        
        await bot_instance.send_message(
            chat_id=private_group_id,
            text=message_text,
            reply_markup=keyboard
        )
        
        logger.info(f"✅ Xabar yuborildi: {group_name}, {keyword}")
        
    except TelegramError as e:
        logger.error(f"❌ Telegram xato: {e}")
    except Exception as e:
        logger.error(f"❌ Xato: {e}")

async def message_handler(event):
    try:
        if not event.message or not event.message.text:
            return
        
        chat = await event.get_chat()
        
        if not hasattr(chat, 'megagroup') or not chat.megagroup:
            return
        
        group_id = event.chat_id
        msg_text = event.message.text
        group_name = getattr(chat, 'title', 'Unknown')
        
        sender = await event.get_sender()
        if not sender:
            return
        
        user_id = sender.id
        username = sender.username if sender.username else (sender.first_name if sender.first_name else "Unknown")
        
        logger.info(f"📨 Xabar: {group_name} ({group_id}), {username}")
        
        matches = db.check_keywords_in_message(group_id, msg_text)
        
        if matches:
            logger.info(f"🔍 {len(matches)} ta topildi!")
            
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
                    logger.error(f"❌ Xato: {e}")
        
    except Exception as e:
        logger.error(f"❌ Handler xato: {e}")

async def start_userbot_with_apis():
    global active_clients
    try:
        db.init_db()
        logger.info("✅ Database initialized")
        
        apis = db.get_active_apis()
        
        if not apis:
            logger.warning("⚠️ Aktiv API yo'q!")
            await asyncio.sleep(60)
            return
        
        logger.info(f"🤖 {len(apis)} ta API topildi")
        
        for api in apis:
            try:
                client = TelegramClient(
                    StringSession(api['session_string']),
                    api['api_id'],
                    api['api_hash']
                )
                
                await client.start(phone=api['phone_number'])
                logger.info(f"✅ Ulanildi: {api['phone_number']}")
                
                me = await client.get_me()
                logger.info(f"✅ {me.first_name} (@{me.username})")
                
                @client.on(events.NewMessage())
                async def handler(event):
                    await message_handler(event)
                
                active_clients.append(client)
                
            except Exception as e:
                logger.error(f"❌ API xato ({api['phone_number']}): {e}")
                db.update_api_status(api['id'], 0)
        
        if not active_clients:
            logger.error("❌ Hech qanday client ishga tushmadi!")
            return
        
        logger.info(f"🎯 {len(active_clients)} ta userbot ishlayapti...")
        
        await asyncio.gather(*[client.run_until_disconnected() for client in active_clients])
        
    except Exception as e:
        logger.error(f"❌ Userbot xato: {e}")
        raise
    finally:
        for client in active_clients:
            try:
                await client.disconnect()
            except:
                pass
        active_clients = []

async def start_with_schedule():
    while True:
        try:
            logger.info("🚀 Userbot ishga tushmoqda...")
            
            schedule_enabled = db.get_setting('userbot_schedule_enabled', 'true')
            
            if schedule_enabled != 'true':
                logger.info("⏰ 24/7 rejim")
                await start_userbot_with_apis()
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
            
            logger.info(f"⏰ {stop_time_str} da to'xtatiladi ({int(seconds_until_stop/3600)}:{int((seconds_until_stop%3600)/60)})")
            
            try:
                await asyncio.wait_for(start_userbot_with_apis(), timeout=seconds_until_stop)
            except asyncio.TimeoutError:
                logger.info(f"🌙 {stop_time_str} - To'xtatilmoqda...")
            
            start_tomorrow = datetime.combine(now.date() + timedelta(days=1), time(start_h, start_m))
            sleep_seconds = (start_tomorrow - datetime.now()).total_seconds()
            
            logger.info(f"💤 {int(sleep_seconds/3600)}:{int((sleep_seconds%3600)/60)} kutish...")
            await asyncio.sleep(sleep_seconds)
            
            logger.info(f"🌅 {start_time_str} - Qayta ishga tushirish...")
            
        except Exception as e:
            logger.error(f"❌ Xato: {e}")
            logger.info("⏳ 5 daqiqa kutish...")
            await asyncio.sleep(300)

async def main():
    logger.info("=" * 60)
    logger.info("🤖 USERBOT ISHGA TUSHMOQDA")
    logger.info("=" * 60)
    
    db.init_db()
    
    schedule_enabled = db.get_setting('userbot_schedule_enabled', 'true')
    
    if schedule_enabled == 'true':
        logger.info("⏰ Kundalik restart yoqilgan")
        await start_with_schedule()
    else:
        logger.info("⏰ 24/7 rejim")
        await start_userbot_with_apis()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⛔ To'xtatildi (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Fatal xato: {e}")
        import traceback
        traceback.print_exc()
