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
    Usage: 
        /scan [limit] - Scans messages from 1 to limit in ALL channels
        /scan <start> <end> - Scans messages from start to end in ALL channels
        /scan <channel_id> <start> <end> - Scans specific channel only
    Examples: 
        /scan 100 - Scans messages 1-100 in all channels
        /scan 101 500 - Scans messages 101-500 in all channels
        /scan -1003261695898 1 3500 - Scans messages 1-3500 in specific channel only
    """
    try:
        # Parse arguments
        args = message.text.split()
        specific_channel = None
        
        if len(args) == 1:
            # /scan (no arguments) - default to 100
            start_id = 1
            end_id = 100
        elif len(args) == 2:
            # /scan 100 (single argument) - scan from 1 to limit
            start_id = 1
            end_id = int(args[1])
        elif len(args) == 3:
            # Could be: /scan 100 500 OR /scan -1003261695898 100
            # Check if first arg is a channel ID (starts with -)
            if args[1].startswith('-'):
                # /scan -1003261695898 500 - specific channel, messages 1 to limit
                specific_channel = args[1]
                start_id = 1
                end_id = int(args[2])
            else:
                # /scan 100 500 - all channels, messages 100-500
                start_id = int(args[1])
                end_id = int(args[2])
        elif len(args) >= 4:
            # /scan -1003261695898 100 500 - specific channel, messages 100-500
            if args[1].startswith('-'):
                specific_channel = args[1]
                start_id = int(args[2])
                end_id = int(args[3])
            else:
                await message.reply_text(
                    "⚠️ Invalid usage!\n\n"
                    "**Usage:**\n"
                    "`/scan` - Scan messages 1-100 in all channels\n"
                    "`/scan 500` - Scan messages 1-500 in all channels\n"
                    "`/scan 100 500` - Scan messages 100-500 in all channels\n"
                    "`/scan -1003261695898 1 3500` - Scan specific channel only",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        else:
            await message.reply_text(
                "⚠️ Invalid usage!\n\n"
                "**Usage:**\n"
                "`/scan` - Scan messages 1-100 in all channels\n"
                "`/scan 500` - Scan messages 1-500 in all channels\n"
                "`/scan 100 500` - Scan messages 100-500 in all channels\n"
                "`/scan -1003261695898 1 3500` - Scan specific channel only",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Validate range
        if start_id < 1:
            await message.reply_text("⚠️ Start ID must be at least 1")
            return
        
        if end_id < start_id:
            await message.reply_text("⚠️ End ID must be greater than or equal to Start ID")
            return
            
        if end_id - start_id > 10000:
            await message.reply_text("⚠️ Range too large! Maximum 10,000 messages per scan.\nTry breaking it into smaller batches.")
            return
        
        # Validate specific channel if provided
        if specific_channel and specific_channel not in Telegram.AUTH_CHANNEL:
            await message.reply_text(
                f"⚠️ Channel `{specific_channel}` is not in AUTH_CHANNEL list!\n\n"
                f"**Available channels:**\n" + 
                "\n".join([f"`{ch}`" for ch in Telegram.AUTH_CHANNEL]),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        total_range = end_id - start_id + 1
        
        # Determine which channels to scan
        channels_to_scan = [specific_channel] if specific_channel else Telegram.AUTH_CHANNEL
        
        channel_info = f"specific channel `{specific_channel}`" if specific_channel else f"**{len(channels_to_scan)} channel(s)**"
        
        status_msg = await message.reply_text(
            f"🔍 Starting scan...\n"
            f"� Channels: {channel_info}\n"
            f"📊 Range: messages {start_id} to {end_id} ({total_range} messages)",
            parse_mode=ParseMode.MARKDOWN
        )
        
        processed = 0
        added = 0
        skipped = 0
        errors = 0
        
        for channel_id in channels_to_scan:
            try:
                chat_id = int(channel_id)
                LOGGER.info(f"Scanning channel: {chat_id}")
                
                await status_msg.edit_text(
                    f"🔍 Scanning channel: `{channel_id}`\n"
                    f"📊 Fetching messages {start_id} to {end_id}...\n"
                    f"⏳ Please wait...",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Scan messages in the specified range
                try:
                    LOGGER.info(f"Scanning {total_range} messages from ID {start_id} to {end_id}...")
                    
                    # Scan from message ID start_id to end_id
                    # This ensures we scan the actual messages in the channel
                    msg_ids_to_scan = list(range(start_id, end_id + 1))
                    
                    LOGGER.info(f"Fetching message IDs {start_id} to {end_id}...")
                    messages_to_scan = await client.get_messages(chat_id, msg_ids_to_scan)
                    
                    if not isinstance(messages_to_scan, list):
                        messages_to_scan = [messages_to_scan]
                    
                    # Filter out None messages
                    messages_to_scan = [msg for msg in messages_to_scan if msg is not None]
                        
                    LOGGER.info(f"Fetched {len(messages_to_scan)} valid messages to scan")
                    
                    await status_msg.edit_text(
                        f"🔍 Scanning channel: `{channel_id}`\n"
                        f"📊 Found {len(messages_to_scan)} messages\n"
                        f"⏳ Processing...",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                except Exception as e:
                    LOGGER.error(f"Failed to get channel messages: {e}")
                    await status_msg.edit_text(
                        f"❌ Error scanning channel: `{channel_id}`\n"
                        f"Error: {str(e)}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    continue
                
                # Process each message
                for msg in messages_to_scan:
                    try:
                        # Skip None messages or invalid messages
                        if not msg:
                            continue
                        
                        # Skip if message doesn't exist or is not a video
                        if not msg:
                            continue
                            
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
                        await asleep(0.3)
                        
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
        channel_summary = f"Channel: `{specific_channel}`" if specific_channel else f"Channels: {len(channels_to_scan)} scanned"
        
        await status_msg.edit_text(
            f"✅ **Scan Complete!**\n\n"
            f"📺 {channel_summary}\n"
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
