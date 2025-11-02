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
    Usage: /cleanup
    """
    try:
        status_msg = await message.reply_text(
            "🔍 Starting cleanup scan...\n"
            "📊 Checking all database entries for broken links...\n"
            "⏳ This may take a while...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        broken_entries = []
        checked = 0
        total_movies = 0
        total_tv = 0
        
        # Check all storage databases
        total_storage_dbs = len(db.dbs) - 1
        for db_index in range(1, total_storage_dbs + 1):
            db_key = f"storage_{db_index}"
            
            # Check movies
            LOGGER.info(f"Checking movies in {db_key}...")
            movies = await db.dbs[db_key]["movie"].find({}).to_list(None)
            total_movies += len(movies)
            
            for movie in movies:
                for quality in movie.get("telegram", []):
                    checked += 1
                    try:
                        from Backend.helper.encrypt import decode_string
                        decoded = await decode_string(quality["id"])
                        chat_id = int(f"-100{decoded['chat_id']}")
                        msg_id = int(decoded["msg_id"])
                        
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
                    
                    if checked % 10 == 0:
                        await status_msg.edit_text(
                            f"🔍 Scanning database...\n"
                            f"📊 Checked: {checked} entries\n"
                            f"❌ Broken: {len(broken_entries)}\n"
                            f"📽️ Movies: {total_movies}\n"
                            f"📺 TV Shows: {total_tv}",
                            parse_mode=ParseMode.MARKDOWN
                        )
                    
                    await asleep(0.1)  # Small delay to avoid rate limits
            
            # Check TV shows
            LOGGER.info(f"Checking TV shows in {db_key}...")
            tv_shows = await db.dbs[db_key]["tv"].find({}).to_list(None)
            total_tv += len(tv_shows)
            
            for show in tv_shows:
                for season in show.get("seasons", []):
                    for episode in season.get("episodes", []):
                        for quality in episode.get("telegram", []):
                            checked += 1
                            try:
                                from Backend.helper.encrypt import decode_string
                                decoded = await decode_string(quality["id"])
                                chat_id = int(f"-100{decoded['chat_id']}")
                                msg_id = int(decoded["msg_id"])
                                
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
                            
                            if checked % 10 == 0:
                                await status_msg.edit_text(
                                    f"🔍 Scanning database...\n"
                                    f"📊 Checked: {checked} entries\n"
                                    f"❌ Broken: {len(broken_entries)}\n"
                                    f"📽️ Movies: {total_movies}\n"
                                    f"📺 TV Shows: {total_tv}",
                                    parse_mode=ParseMode.MARKDOWN
                                )
                            
                            await asleep(0.1)
        
        # Final report
        if broken_entries:
            report = "⚠️ **Broken Links Found!**\n\n"
            report += f"Total Checked: {checked}\n"
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
                f"📊 Total Checked: {checked} entries\n"
                f"✨ No broken links found!\n"
                f"📽️ Movies: {total_movies}\n"
                f"📺 TV Shows: {total_tv}",
                parse_mode=ParseMode.MARKDOWN
            )
        
    except Exception as e:
        LOGGER.error(f"Error in cleanup command: {e}")
        await message.reply_text(f"❌ Error: {e}")
