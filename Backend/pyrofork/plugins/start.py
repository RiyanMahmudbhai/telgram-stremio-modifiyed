from pyrogram import filters, Client, enums
from Backend.helper.custom_filter import CustomFilters
from pyrogram.types import Message
from Backend.config import Telegram

@Client.on_message(filters.command('start') & filters.private & CustomFilters.owner, group=10)
async def send_start_message(client: Client, message: Message):
    try:
        base_url = Telegram.BASE_URL
        addon_url = f"{base_url}/stremio/manifest.json"

        await message.reply_text(
            '<b>Welcome to the main Telegram Stremio bot!</b>\n\n'
            'To install the Stremio addon, copy the URL below and add it in the Stremio addons:\n\n'
            f'<b>Your Addon URL:</b>\n<code>{addon_url}</code>',
            quote=True,
            parse_mode=enums.ParseMode.HTML
        )

    except Exception as e:
        await message.reply_text(f"⚠️ Error: {e}")
        print(f"Error in /start handler: {e}")