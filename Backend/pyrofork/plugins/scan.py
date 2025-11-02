from asyncio import sleep as asleep
from pyrogram import filters, Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pyrogram.enums.parse_mode import ParseMode

import Backend
from Backend.helper.custom_filter import CustomFilters
from Backend.logger import LOGGER
from Backend.config import Telegram
from Backend.helper.pyro import clean_filename, get_readable_file_size, remove_urls
from Backend.helper.metadata import metadata
from Backend import db


@Client.on_message(filters.command('scan') & filters.private & CustomFilters.owner, group=10)
async def scan_channel(client: Client, message: Message):
    """
    Scans AUTH_CHANNEL for existing video files and adds them to the database.
    Usage: /scan [limit]
    Example: /scan 100 (scans last 100 messages)
    """
    try:
        # Parse limit argument
        args = message.text.split()
        limit = int(args[1]) if len(args) > 1 else 100
        
        if limit < 1 or limit > 10000:
            await message.reply_text("⚠️ Limit must be between 1 and 10000")
            return
        
        status_msg = await message.reply_text(
            f"🔍 Starting scan of AUTH_CHANNEL...\n"
            f"📊 Scanning last {limit} messages",
            parse_mode=ParseMode.MARKDOWN
        )
        
        processed = 0
        added = 0
        skipped = 0
        errors = 0
        
        for channel_id in Telegram.AUTH_CHANNEL:
            try:
                chat_id = int(channel_id)
                LOGGER.info(f"Scanning channel: {chat_id}")
                
                await status_msg.edit_text(
                    f"🔍 Scanning channel: `{channel_id}`\n"
                    f"📊 Limit: {limit} messages\n"
                    f"⏳ Please wait...",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                async for msg in client.get_chat_history(chat_id, limit=limit):
                    try:
                        # Check if message has video or document
                        if not (msg.video or (msg.document and msg.document.mime_type and msg.document.mime_type.startswith("video/"))):
                            continue
                        
                        file = msg.video or msg.document
                        title = msg.caption or file.file_name
                        msg_id = msg.id
                        size = get_readable_file_size(file.file_size)
                        channel = str(chat_id).replace("-100", "")
                        
                        # Check if already exists in database
                        existing = await check_existing_file(int(channel), msg_id)
                        if existing:
                            skipped += 1
                            LOGGER.info(f"Skipping existing file: {title} (ID: {msg_id})")
                            continue
                        
                        # Extract metadata
                        metadata_info = await metadata(clean_filename(title), int(channel), msg_id)
                        if metadata_info is None:
                            LOGGER.warning(f"Metadata failed for file: {title} (ID: {msg_id})")
                            errors += 1
                            continue
                        
                        # Format title
                        title = remove_urls(title)
                        if not title.endswith(('.mkv', '.mp4')):
                            title += '.mkv'
                        
                        # Insert to database
                        updated_id = await db.insert_media(metadata_info, channel=int(channel), msg_id=msg_id, size=size, name=title)
                        
                        if updated_id:
                            added += 1
                            LOGGER.info(f"✅ Added: {title} (ID: {msg_id})")
                        else:
                            errors += 1
                            LOGGER.warning(f"❌ Failed to add: {title} (ID: {msg_id})")
                        
                        processed += 1
                        
                        # Update status every 10 files
                        if processed % 10 == 0:
                            await status_msg.edit_text(
                                f"🔍 Scanning channel: `{channel_id}`\n"
                                f"📊 Processed: {processed}\n"
                                f"✅ Added: {added}\n"
                                f"⏭️ Skipped: {skipped}\n"
                                f"❌ Errors: {errors}",
                                parse_mode=ParseMode.MARKDOWN
                            )
                        
                        # Small delay to avoid rate limits
                        await asleep(0.5)
                        
                    except FloodWait as e:
                        LOGGER.warning(f"FloodWait: {e.value}s")
                        await asleep(e.value)
                    except Exception as e:
                        LOGGER.error(f"Error processing message {msg.id}: {e}")
                        errors += 1
                        continue
                
            except Exception as e:
                LOGGER.error(f"Error scanning channel {channel_id}: {e}")
                await message.reply_text(f"❌ Error scanning channel {channel_id}: {e}")
                continue
        
        # Final status
        await status_msg.edit_text(
            f"✅ **Scan Complete!**\n\n"
            f"📊 Total Processed: {processed}\n"
            f"✅ Added: {added}\n"
            f"⏭️ Skipped (already exist): {skipped}\n"
            f"❌ Errors: {errors}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        LOGGER.info(f"Scan complete: Processed={processed}, Added={added}, Skipped={skipped}, Errors={errors}")
        
    except ValueError:
        await message.reply_text("⚠️ Invalid limit. Usage: `/scan [limit]`\nExample: `/scan 100`", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        LOGGER.error(f"Error in scan command: {e}")
        await message.reply_text(f"❌ Error: {e}")


async def check_existing_file(channel: int, msg_id: int) -> bool:
    """
    Check if a file already exists in the database by checking all storage DBs.
    Returns True if found, False otherwise.
    """
    try:
        from Backend.helper.encrypt import encode_string
        
        # Generate the encoded string for this file
        data = {"chat_id": channel, "msg_id": msg_id}
        encoded_id = await encode_string(data)
        
        # Search in all storage databases
        total_storage_dbs = len(db.dbs) - 1
        for db_index in range(1, total_storage_dbs + 1):
            db_key = f"storage_{db_index}"
            
            # Check movies collection
            movie = await db.dbs[db_key]["movie"].find_one(
                {"telegram.id": encoded_id}
            )
            if movie:
                return True
            
            # Check TV shows collection
            tv = await db.dbs[db_key]["tv"].find_one(
                {"seasons.episodes.telegram.id": encoded_id}
            )
            if tv:
                return True
        
        return False
        
    except Exception as e:
        LOGGER.error(f"Error checking existing file: {e}")
        return False
