#!/usr/bin/env python3

import yt_dlp
import discord
from discord.ext import commands
from discord.ui import Button, View
import logging
import os
import asyncio

# -------------------------------------------
# LOGGING SETUP
logdir = os.getenv("LOGDIR", "./logs")
os.makedirs(logdir, exist_ok=True)
log_file_path = os.path.join(logdir, "DISCORD.MUSIC.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

bot_logger = logging.getLogger("bot")
discord_logger = logging.getLogger("discord")
discord_logger.setLevel(logging.DEBUG)
# -------------------------------------------
# TOKEN LOADING
script_directory = os.path.dirname(os.path.abspath(__file__))
token_file_path = os.path.join(script_directory, "token.txt")

with open(token_file_path, "r") as file:
    key = file.read().strip()
# -------------------------------------------
# BOT SETUP
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------------------------
# GLOBAL STATE
song_queue = []
current_song = None
is_paused = False

class MusicControlView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
        # Stylish buttons with labels
        self.play_pause_button = Button(
            style=discord.ButtonStyle.blurple,
            emoji="⏯",
            label="Play/Pause"
        )
        self.next_button = Button(
            style=discord.ButtonStyle.green,
            emoji="⏭", 
            label="Next"
        )
        self.stop_button = Button(
            style=discord.ButtonStyle.red,
            emoji="⏹",
            label="Stop"
        )

        # Set callbacks
        self.play_pause_button.callback = self.play_pause_handler
        self.next_button.callback = self.next_handler
        self.stop_button.callback = self.stop_handler

        # Add buttons to view
        self.add_item(self.play_pause_button)
        self.add_item(self.next_button)
        self.add_item(self.stop_button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.voice and interaction.user.voice.channel == interaction.guild.voice_client.channel

    async def play_pause_handler(self, interaction: discord.Interaction):
        global is_paused
        vc = interaction.guild.voice_client
        
        if not vc.is_playing() and not vc.is_paused():
            return await interaction.response.send_message("Nothing is playing", ephemeral=True)
            
        if vc.is_paused():
            vc.resume()
            self.play_pause_button.style = discord.ButtonStyle.blurple
            is_paused = False
            await interaction.response.edit_message(
                content=f"▶️ Resumed: {current_song[1]}",
                view=self
            )
        else:
            vc.pause()
            self.play_pause_button.style = discord.ButtonStyle.grey
            is_paused = True
            await interaction.response.edit_message(
                content=f"⏸ Paused: {current_song[1]}",
                view=self
            )

    async def next_handler(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc.is_playing() or vc.is_paused():
            vc.stop()
            await interaction.response.edit_message(content="⏭ Skipping...")
            await play_next_song(interaction=interaction)
        else:
            await interaction.response.send_message("Nothing to skip", ephemeral=True)

    async def stop_handler(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc.is_playing() or vc.is_paused():
            vc.stop()
            
        await vc.disconnect()
        await interaction.response.edit_message(
            content="⏹ Playback stopped", 
            view=None
        )
        self.stop()

@bot.event
async def on_ready():
    bot_logger.info("Bot is ready")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="your requests"
        )
    )

@bot.command(name="play")
async def play(ctx, *, query):
    bot_logger.info(f"Play command by {ctx.author.name}: {query}")
    
    if not ctx.author.voice:
        await ctx.send("🚫 You must be in a voice channel!")
        return

    voice_channel = ctx.author.voice.channel

    if not ctx.voice_client:
        await voice_channel.connect()

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)

            if "entries" in info:
                entries = info["entries"]
                playlist_title = info["title"]
                playlist_songs = [(entry["url"], entry["title"]) for entry in entries]
                song_queue.extend(playlist_songs)
                
                embed = discord.Embed(
                    title="🎵 Playlist Added",
                    description=f"**{playlist_title}**\n{len(entries)} tracks added to queue",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
                
                if not ctx.voice_client.is_playing():
                    await play_next_song(ctx)
            else:
                url = info["url"]
                title = info["title"]
                source = await discord.FFmpegOpusAudio.from_probe(
                    url,
                    before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                )
                
                if ctx.voice_client.is_playing() or song_queue:
                    song_queue.append((url, title))
                    embed = discord.Embed(
                        title="🎶 Added to Queue",
                        description=title,
                        color=discord.Color.blue()
                    )
                    await ctx.send(embed=embed)
                else:
                    ctx.voice_client.play(
                        source, 
                        after=lambda e: asyncio.run_coroutine_threadsafe(
                            play_next_song(ctx), 
                            bot.loop
                        )
                    )
                    global current_song
                    current_song = (url, title)
                    view = MusicControlView()
                    embed = discord.Embed(
                        title="🎵 Now Playing",
                        description=title,
                        color=discord.Color.gold()
                    )
                    await ctx.send(embed=embed, view=view)

    except Exception as e:
        bot_logger.error(f"Error: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description=str(e),
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name="stop")
async def stop(ctx):
    bot_logger.info("Stop command invoked")
    if ctx.voice_client:
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        song_queue.clear()
        embed = discord.Embed(
            title="⏹ Playback Stopped",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name="skip")
async def skip(ctx):
    bot_logger.info("Skip command invoked")
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        embed = discord.Embed(
            title="⏭ Skipped Song",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="🚫 Nothing to Skip",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name="pause")
async def pause(ctx):
    bot_logger.info("Pause command invoked")
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        embed = discord.Embed(
            title="⏸ Paused",
            description=current_song[1],
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="🚫 Nothing to Pause",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name="resume")
async def resume(ctx):
    bot_logger.info("Resume command invoked")
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        embed = discord.Embed(
            title="▶️ Resumed",
            description=current_song[1],
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="🚫 Nothing to Resume",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name="list")
async def list_command(ctx):
    bot_logger.info("List command invoked")
    
    embed = discord.Embed(
        title="🎶 Music Queue",
        color=discord.Color.purple()
    )
    
    if current_song:
        embed.add_field(
            name="Now Playing:",
            value=f"**{current_song[1]}**",
            inline=False
        )
    else:
        embed.add_field(
            name="Now Playing:",
            value="Nothing is playing",
            inline=False
        )
    
    if song_queue:
        queue_list = "\n".join(
            [f"**{i+1}.** {title}" for i, (_, title) in enumerate(song_queue[:10])]
        )
        if len(song_queue) > 10:
            queue_list += f"\n\n*...and {len(song_queue)-10} more tracks*"
        
        embed.add_field(
            name="Up Next:",
            value=queue_list,
            inline=False
        )
    else:
        embed.add_field(
            name="Queue:",
            value="The queue is empty",
            inline=False
        )
    
    embed.set_footer(
        text=f"Requested by {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url
    )
    
    await ctx.send(embed=embed)

async def play_next_song(ctx=None, interaction=None):
    global current_song
    
    target = ctx if ctx else interaction
    
    if song_queue:
        next_song_url, next_song_title = song_queue.pop(0)
        current_song = (next_song_url, next_song_title)
        
        try:
            source = await discord.FFmpegOpusAudio.from_probe(
                next_song_url,
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
            )
            
            target.voice_client.play(
                source, 
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    play_next_song(ctx=ctx), 
                    bot.loop
                )
            )
            
            view = MusicControlView()
            embed = discord.Embed(
                title="🎵 Now Playing",
                description=next_song_title,
                color=discord.Color.gold()
            )
            
            if interaction:
                await interaction.edit_original_response(embed=embed, view=view)
            else:
                await target.send(embed=embed, view=view)
                
        except Exception as e:
            bot_logger.error(f"Error: {e}")
            embed = discord.Embed(
                title="❌ Playback Error",
                description=str(e),
                color=discord.Color.red()
            )
            await target.send(embed=embed)
    else:
        current_song = None
        embed = discord.Embed(
            title="🎶 Queue Empty",
            description="No more tracks in queue",
            color=discord.Color.blue()
        )
        await target.send(embed=embed)

if __name__ == "__main__":
    bot_logger.info("Starting bot...")
    bot.run(key)