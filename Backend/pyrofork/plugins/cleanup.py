from asyncio import sleep as asleep
from pyrogram import filters, Client
from pyrogram.types import Message
from pyrogram.enums.parse_mode import ParseMode

from Backend.helper.custom_filter import CustomFilters
from Backend.logger import LOGGER
from Backend import db


@Client.on_message(filters.command('cleanup') & filters.private & CustomFilters.owner, group=10)
async def cleanup_broken_links(client: Client, message: Message):
    """
    Scans database for broken video links (messages that no longer exist in Telegram)
    and reports them. Does NOT delete automatically - only reports.
    Usage: 
        /cleanup - Check first 100 entries in all channels
        /cleanup [limit] - Check first [limit] entries in all channels
        /cleanup <channel_id> - Check all entries in specific channel (max 1000)
        /cleanup <channel_id> [limit] - Check [limit] entries in specific channel
    Examples:
        /cleanup 500 - Check first 500 entries in all channels
        /cleanup -1003261695898 - Check first 1000 in specific channel
        /cleanup -1003261695898 5000 - Check first 5000 in specific channel
    """
    try:
        from Backend.config import Telegram
        
        # Parse arguments
        args = message.text.split()
        specific_channel = None
        limit = 100  # Default limit
        
        if len(args) == 1:
            # /cleanup - default 100 in all channels
            limit = 100
        elif len(args) == 2:
            # Could be: /cleanup 500 OR /cleanup -1003261695898
            if args[1].startswith('-'):
                # /cleanup -1003261695898 - specific channel, max 1000
                specific_channel = args[1]
                limit = 1000
            else:
                # /cleanup 500 - all channels, limit 500
                limit = int(args[1])
        elif len(args) >= 3:
            # /cleanup -1003261695898 5000 - specific channel with limit
            if args[1].startswith('-'):
                specific_channel = args[1]
                limit = int(args[2])
            else:
                await message.reply_text(
                    "⚠️ Invalid usage!\n\n"
                    "**Usage:**\n"
                    "`/cleanup` - Check first 100 entries in all channels\n"
                    "`/cleanup 500` - Check first 500 entries in all channels\n"
                    "`/cleanup -1003261695898` - Check first 1000 in specific channel\n"
                    "`/cleanup -1003261695898 5000` - Check first 5000 in specific channel",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        
        # Validate limit
        if limit < 1 or limit > 100000:
            await message.reply_text("⚠️ Limit must be between 1 and 100,000")
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
        
        channel_info = f"specific channel `{specific_channel}`" if specific_channel else f"**all channels**"
        
        status_msg = await message.reply_text(
            f"🔍 Starting cleanup scan...\n"
            f"📺 Channels: {channel_info}\n"
            f"📊 Limit: {limit} entries max\n"
            f"⏳ This may take a while...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        broken_entries = []
        checked = 0
        total_movies = 0
        total_tv = 0
        entries_checked_count = 0  # Track actual entries checked against limit
        
        # Check all storage databases
        total_storage_dbs = len(db.dbs) - 1
        for db_index in range(1, total_storage_dbs + 1):
            if entries_checked_count >= limit:
                break
                
            db_key = f"storage_{db_index}"
            
            # Check movies
            LOGGER.info(f"Checking movies in {db_key}...")
            movies = await db.dbs[db_key]["movie"].find({}).to_list(None)
            total_movies += len(movies)
            
            for movie in movies:
                if entries_checked_count >= limit:
                    break
                    
                for quality in movie.get("telegram", []):
                    if entries_checked_count >= limit:
                        break
                        
                    checked += 1
                    try:
                        from Backend.helper.encrypt import decode_string
                        decoded = await decode_string(quality["id"])
                        chat_id = int(f"-100{decoded['chat_id']}")
                        msg_id = int(decoded["msg_id"])
                        
                        # Skip if specific channel is set and this isn't it
                        if specific_channel and str(chat_id) != specific_channel:
                            continue
                        
                        entries_checked_count += 1
                        
                        # Try to fetch the message
                        msg = await client.get_messages(chat_id, msg_id)
                        
                        if not msg or not (msg.video or msg.document):
                            broken_entries.append({
                                "type": "movie",
                                "title": movie.get("title"),
                                "quality": quality.get("quality"),
                                "chat_id": chat_id,
                                "msg_id": msg_id,
                                "tmdb_id": movie.get("tmdb_id"),
                                "db_index": movie.get("db_index")
                            })
                            LOGGER.warning(f"Broken link found: {movie.get('title')} - {quality.get('quality')}")
                    except Exception as e:
                        broken_entries.append({
                            "type": "movie",
                            "title": movie.get("title"),
                            "quality": quality.get("quality"),
                            "error": str(e),
                            "tmdb_id": movie.get("tmdb_id"),
                            "db_index": movie.get("db_index")
                        })
                        LOGGER.error(f"Error checking movie {movie.get('title')}: {e}")
                    
                    if entries_checked_count % 10 == 0:
                        await status_msg.edit_text(
                            f"🔍 Scanning database...\n"
                            f"� Channel: {channel_info}\n"
                            f"📊 Progress: {entries_checked_count}/{limit}\n"
                            f"❌ Broken: {len(broken_entries)}",
                            parse_mode=ParseMode.MARKDOWN
                        )
                    
                    await asleep(0.1)  # Small delay to avoid rate limits
            
            # Check TV shows
            if entries_checked_count >= limit:
                break
                
            LOGGER.info(f"Checking TV shows in {db_key}...")
            tv_shows = await db.dbs[db_key]["tv"].find({}).to_list(None)
            total_tv += len(tv_shows)
            
            for show in tv_shows:
                if entries_checked_count >= limit:
                    break
                    
                for season in show.get("seasons", []):
                    if entries_checked_count >= limit:
                        break
                        
                    for episode in season.get("episodes", []):
                        if entries_checked_count >= limit:
                            break
                            
                        for quality in episode.get("telegram", []):
                            if entries_checked_count >= limit:
                                break
                                
                            checked += 1
                            try:
                                from Backend.helper.encrypt import decode_string
                                decoded = await decode_string(quality["id"])
                                chat_id = int(f"-100{decoded['chat_id']}")
                                msg_id = int(decoded["msg_id"])
                                
                                # Skip if specific channel is set and this isn't it
                                if specific_channel and str(chat_id) != specific_channel:
                                    continue
                                
                                entries_checked_count += 1
                                
                                # Try to fetch the message
                                msg = await client.get_messages(chat_id, msg_id)
                                
                                if not msg or not (msg.video or msg.document):
                                    broken_entries.append({
                                        "type": "tv",
                                        "title": show.get("title"),
                                        "season": season.get("season_number"),
                                        "episode": episode.get("episode_number"),
                                        "quality": quality.get("quality"),
                                        "chat_id": chat_id,
                                        "msg_id": msg_id,
                                        "tmdb_id": show.get("tmdb_id"),
                                        "db_index": show.get("db_index")
                                    })
                                    LOGGER.warning(f"Broken link found: {show.get('title')} S{season.get('season_number')}E{episode.get('episode_number')} - {quality.get('quality')}")
                            except Exception as e:
                                broken_entries.append({
                                    "type": "tv",
                                    "title": show.get("title"),
                                    "season": season.get("season_number"),
                                    "episode": episode.get("episode_number"),
                                    "quality": quality.get("quality"),
                                    "error": str(e),
                                    "tmdb_id": show.get("tmdb_id"),
                                    "db_index": show.get("db_index")
                                })
                                LOGGER.error(f"Error checking TV show {show.get('title')}: {e}")
                            
                            if entries_checked_count % 10 == 0:
                                await status_msg.edit_text(
                                    f"🔍 Scanning database...\n"
                                    f"� Channel: {channel_info}\n"
                                    f"📊 Progress: {entries_checked_count}/{limit}\n"
                                    f"❌ Broken: {len(broken_entries)}",
                                    parse_mode=ParseMode.MARKDOWN
                                )
                            
                            await asleep(0.1)
        
        # Final report
        channel_summary = f"Channel: `{specific_channel}`" if specific_channel else "Channels: All"
        
        if broken_entries:
            report = "⚠️ **Broken Links Found!**\n\n"
            report += f"{channel_summary}\n"
            report += f"Entries Checked: {entries_checked_count}\n"
            report += f"Broken Links: {len(broken_entries)}\n\n"
            report += "**First 10 broken entries:**\n"
            
            for i, entry in enumerate(broken_entries[:10]):
                if entry["type"] == "movie":
                    report += f"{i+1}. {entry['title']} ({entry.get('quality', 'N/A')})\n"
                else:
                    report += f"{i+1}. {entry['title']} S{entry.get('season')}E{entry.get('episode')} ({entry.get('quality', 'N/A')})\n"
            
            if len(broken_entries) > 10:
                report += f"\n...and {len(broken_entries) - 10} more\n"
            
            report += "\n💡 Check log.txt for full list"
            
            await status_msg.edit_text(report, parse_mode=ParseMode.MARKDOWN)
            
            # Log all broken entries
            LOGGER.info("=" * 50)
            LOGGER.info("BROKEN LINKS REPORT")
            LOGGER.info("=" * 50)
            for entry in broken_entries:
                LOGGER.info(f"Broken: {entry}")
        else:
            await status_msg.edit_text(
                f"✅ **Cleanup Complete!**\n\n"
                f"{channel_summary}\n"
                f"� Entries Checked: {entries_checked_count}\n"
                f"✨ No broken links found!",
                parse_mode=ParseMode.MARKDOWN
            )
        
    except Exception as e:
        LOGGER.error(f"Error in cleanup command: {e}")
        await message.reply_text(f"❌ Error: {e}")
