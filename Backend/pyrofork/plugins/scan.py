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
                    f"📊 Fetching last {limit} messages...\n"
                    f"⏳ Please wait...",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Get multiple messages at once (batch fetch)
                try:
                    messages_to_scan = []
                    
                    # Strategy: Search incrementally to find where messages actually exist
                    # Most channels have messages in lower ID ranges
                    search_ranges = [
                        (1, 500),           # Check 1-500
                        (500, 2000),        # Check 500-2000
                        (2000, 10000),      # Check 2000-10000
                        (10000, 50000),     # Check 10000-50000
                        (50000, 100000),    # Check 50000-100000
                        (100000, 500000),   # Check 100000-500000
                        (500000, 1000000),  # Check 500000-1000000
                    ]
                    
                    latest_msg_id = None
                    
                    # Find the actual range where messages exist
                    for start_range, end_range in search_ranges:
                        try:
                            # Test the end of this range
                            test_msg = await client.get_messages(chat_id, end_range)
                            if test_msg and not isinstance(test_msg, list):
                                # Found valid messages in this range, keep searching higher
                                latest_msg_id = test_msg.id
                                LOGGER.info(f"Found messages up to ID {latest_msg_id} in range {start_range}-{end_range}")
                                continue
                            else:
                                # No message at this ID, means we've gone too high
                                # Use the previous found latest_msg_id
                                break
                        except Exception as e:
                            # This range doesn't exist, we've gone too high
                            break
                    
                    # If we didn't find any messages, try getting from the beginning
                    if latest_msg_id is None:
                        LOGGER.info("Trying to fetch from beginning of channel...")
                        try:
                            # Try to get any message from the channel
                            for test_id in [100, 50, 20, 10, 5, 1]:
                                test_msg = await client.get_messages(chat_id, test_id)
                                if test_msg and not isinstance(test_msg, list):
                                    latest_msg_id = test_id
                                    break
                        except Exception:
                            pass
                    
                    if latest_msg_id is None:
                        LOGGER.warning(f"Could not find any messages in channel {chat_id}")
                        await status_msg.edit_text(
                            f"❌ Could not access channel: `{channel_id}`\n"
                            f"Make sure bot is admin in the channel!",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        continue
                    
                    # Now we know the approximate latest message ID
                    # Scan backwards from there
                    start_msg_id = max(1, latest_msg_id - limit + 1)
                    LOGGER.info(f"Found latest message ID: {latest_msg_id}, scanning from {start_msg_id}")
                    
                    # Fetch messages in this range
                    msg_ids = list(range(start_msg_id, latest_msg_id + 1))
                    messages_to_scan = await client.get_messages(chat_id, msg_ids)
                    if not isinstance(messages_to_scan, list):
                        messages_to_scan = [messages_to_scan]
                    
                    # Filter out None messages
                    messages_to_scan = [msg for msg in messages_to_scan if msg is not None]
                        
                    LOGGER.info(f"Fetched {len(messages_to_scan)} messages to scan")
                    
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
