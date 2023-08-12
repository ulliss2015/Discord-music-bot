import yt_dlp
import discord
from discord.ext import commands
import os

# token import
script_directory = os.path.dirname(os.path.abspath(__file__))
token_file_path = os.path.join(script_directory, "token.txt")

with open(token_file_path, "r") as file:
    key = file.read().strip()

# -------------------------------------------

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

song_queue = []
current_song = None


@bot.event
async def on_ready():
    print('Bot is ready')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='Music'))


@bot.command(name='play')
async def play(ctx, *, query):
    if not ctx.author.voice:
        await ctx.send('You need to be in a voice channel to use this command!')
        return

    voice_channel = ctx.author.voice.channel

    if not ctx.voice_client:
        await voice_channel.connect()

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)

        if 'entries' in info:
            # Playlist
            entries = info['entries']
            playlist_title = info['title']
            playlist_songs = [(entry['url'], entry['title'])
                              for entry in entries]
            song_queue.extend(playlist_songs)
            await ctx.send(f'Added playlist: {playlist_title}')
            if not ctx.voice_client.is_playing():
                await play_next_song(ctx)
        else:
            # Individual video
            url = info['url']
            title = info['title']
            source = await discord.FFmpegOpusAudio.from_probe(url)
            if ctx.voice_client.is_playing() or song_queue:
                song_queue.append((url, title))
                await ctx.send(f'Added to queue: {title}')
            else:
                ctx.voice_client.play(source)
                global current_song
                current_song = title
                await ctx.send(f'Now playing: {title}')


@bot.command(name='stop')
async def stop(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send('Music stopped')
        song_queue.clear()
    await ctx.voice_client.disconnect()


@bot.command(name='skip')
async def skip(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send('Skipped current song')
    if song_queue:
        await play_next_song(ctx)
    else:
        global current_song
        current_song = None
        await ctx.send('No more songs in the queue')


@bot.command(name='list')
async def list_command(ctx):
    if current_song:
        song_list_message = f'Now playing: {current_song}\n\n'
    else:
        song_list_message = ''

    if song_queue:
        song_list_message += 'Queue:\n'
        song_list_message += '\n'.join([title for _, title in song_queue])
    else:
        song_list_message += 'No more songs in the queue.'

    await ctx.send(song_list_message)


async def play_next_song(ctx):
    global current_song
    if song_queue:
        next_song_url, next_song_title = song_queue.pop(0)
        source = await discord.FFmpegOpusAudio.from_probe(next_song_url)
        ctx.voice_client.play(source)
        current_song = next_song_title
        await ctx.send(f'Now playing: {current_song}')
    else:
        current_song = None
        await ctx.send('No more songs in the queue')


if __name__ == "__main__"
bot.run(key)
