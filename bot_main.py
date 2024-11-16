#!/usr/bin/env python3

import yt_dlp
import discord
from discord.ext import commands
import logging
import os


# LOGGING
logdir = os.getenv("LOGDIR", "./logs")
os.makedirs(logdir, exist_ok=True)
log_file_path = os.path.join(logdir, "DISCORD.MUSIC.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path, encoding="utf-8"),
        logging.StreamHandler(),  # Логи также выводятся в консоль
    ],
)
# -------------------------------------------

# LOGGERS
bot_logger = logging.getLogger("bot")
discord_logger = logging.getLogger("discord")
discord_logger.setLevel(logging.DEBUG)
# -------------------------------------------

# TOKEN
script_directory = os.path.dirname(os.path.abspath(__file__))
token_file_path = os.path.join(script_directory, "token.txt")

with open(token_file_path, "r") as file:
    key = file.read().strip()
# -------------------------------------------

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

song_queue = []
current_song = None


@bot.event
async def on_ready():
    bot_logger.info("Bot is ready")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Music"))


@bot.command(name="play")
async def play(ctx, *, query):
    bot_logger.info(f"Play command invoked by {ctx.author.name} with query: {query}")
    if not ctx.author.voice:
        await ctx.send("You need to be in a voice channel to use this command!")
        return

    voice_channel = ctx.author.voice.channel

    if not ctx.voice_client:
        await voice_channel.connect()

    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "verbose": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)

            if "entries" in info:
                # Playlist
                entries = info["entries"]
                playlist_title = info["title"]
                playlist_songs = [(entry["url"], entry["title"]) for entry in entries]
                song_queue.extend(playlist_songs)
                await ctx.send(f"Added playlist: {playlist_title}")
                bot_logger.info(f"Added playlist: {playlist_title} with {len(entries)} songs")
                if not ctx.voice_client.is_playing():
                    await play_next_song(ctx)
            else:
                # Individual video
                url = info["url"]
                title = info["title"]
                source = await discord.FFmpegOpusAudio.from_probe(
                    url,
                    before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel verbose",
                )
                if ctx.voice_client.is_playing() or song_queue:
                    song_queue.append((url, title))
                    await ctx.send(f"Added to queue: {title}")
                    bot_logger.info(f"Added to queue: {title}")
                else:
                    ctx.voice_client.play(source)
                    global current_song
                    current_song = title
                    await ctx.send(f"Now playing: {title}")
                    bot_logger.info(f"Now playing: {title}")
    except Exception as e:
        bot_logger.error(f"Error while processing play command: {e}")
        await ctx.send("An error occurred while trying to play the song.")


@bot.command(name="stop")
async def stop(ctx):
    bot_logger.info("Stop command invoked")
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Music stopped")
        song_queue.clear()
        bot_logger.info("Music stopped and queue cleared")
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        bot_logger.info("Disconnected from voice channel")


@bot.command(name="skip")
async def skip(ctx):
    bot_logger.info("Skip command invoked")
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipped current song")
        bot_logger.info("Skipped current song")
    if song_queue:
        await play_next_song(ctx)
    else:
        global current_song
        current_song = None
        await ctx.send("No more songs in the queue")
        bot_logger.info("No more songs in the queue")


@bot.command(name="list")
async def list_command(ctx):
    bot_logger.info("List command invoked")
    if current_song:
        song_list_message = f"Now playing: {current_song}\n\n"
    else:
        song_list_message = ""

    if song_queue:
        song_list_message += "Queue:\n"
        song_list_message += "\n".join([title for _, title in song_queue])
    else:
        song_list_message += "No more songs in the queue."

    await ctx.send(song_list_message)


async def play_next_song(ctx):
    global current_song
    if song_queue:
        next_song_url, next_song_title = song_queue.pop(0)
        bot_logger.info(f"Playing next song: {next_song_title}")
        try:
            source = await discord.FFmpegOpusAudio.from_probe(
                next_song_url,
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel verbose",
            )
            ctx.voice_client.play(source)
            current_song = next_song_title
            await ctx.send(f"Now playing: {current_song}")
            bot_logger.info(f"Now playing: {current_song}")
        except Exception as e:
            bot_logger.error(f"Error while playing next song: {e}")
            await ctx.send("An error occurred while trying to play the next song.")
    else:
        current_song = None
        await ctx.send("No more songs in the queue")
        bot_logger.info("No more songs in the queue")


if __name__ == "__main__":
    bot_logger.info("Starting bot...")
    bot.run(key)
