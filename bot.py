import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import asyncio
import random
import re
from dotenv import load_dotenv 
import os

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

import messages

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID,
                                                                             client_secret=SPOTIFY_CLIENT_SECRET))

music_queue = {}

def search_youtube(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'default_search': 'ytsearch',
        'quiet': True
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(query, download=False)
            if 'entries' in result:
                result = result['entries'][0]
            
            return {'source': result['url'], 'title': result['title']}
        
        except Exception as e:
            print(f"Erro ao buscar no YouTube: {str(e)}")
            return None

def search_spotify(query):
    result = spotify.search(q=query, type='track', limit=1)
    if result['tracks']['items']:
        track = result['tracks']['items'][0]
        return {'title': track['name'], 'url': track['external_urls']['spotify']}
    return None

def get_spotify_track(url):
    try:
        track_id = url.split('/')[-1].split('?')[0]
        track = spotify.track(track_id)
        return {'title': track['name'], 'url': track['external_urls']['spotify']}
    except Exception as e:
        print(f"Erro ao extrair URL do Spotify: {str(e)}")
        return None

async def play_next_song(ctx):
    guild_id = ctx.guild.id
    if guild_id in music_queue and music_queue[guild_id]:
        song = music_queue[guild_id].pop(0)

        if 'source' not in song:
            await ctx.send("Erro: Não foi possível obter o link de áudio.")
            return

        voice_channel = ctx.author.voice.channel
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)

        source = discord.FFmpegPCMAudio(song['source'])
        voice.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(ctx), bot.loop))
        
        await ctx.send(f"Tocando agora: **{song['title']}**")
    else:
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice and voice.is_connected():
            await voice.disconnect()


@bot.command(name="play")
async def play(ctx, *, query=None):
    if query is None:
        await ctx.send(messages.ERROR_NO_QUERY)
        return

    song = None

  
    spotify_pattern = r"(https?://open\.spotify\.com/track/[\w\d]+)"
    if re.match(spotify_pattern, query):
        song = get_spotify_track(query)
    else:
      
        song = search_youtube(query)
        if not song:
            await ctx.send(messages.ERROR_MUSIC_NOT_FOUND_YOUTUBE)
            song = search_spotify(query)

    if song:
        guild_id = ctx.guild.id

        if guild_id not in music_queue:
            music_queue[guild_id] = []

        music_queue[guild_id].append(song)

      
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if not voice or not voice.is_playing():
            voice_channel = ctx.author.voice.channel
            if voice_channel:
                voice = await voice_channel.connect()
                await play_next_song(ctx)
            else:
                await ctx.send(messages.ERROR_NO_VOICE_CHANNEL)
        else:
            await ctx.send(messages.MESSAGE_ADDED_TO_QUEUE.format(title=song['title']))
    else:
        await ctx.send(messages.ERROR_NO_MUSIC_FOUND)

@bot.command(name="pause")
async def pause(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.pause()
        await ctx.send(messages.MESSAGE_PAUSED)
    else:
        await ctx.send(messages.ERROR_NO_MUSIC_PLAYING)

@bot.command(name="resume")
async def resume(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_paused():
        voice.resume()
        await ctx.send(messages.MESSAGE_RESUMED)
    else:
        await ctx.send(messages.ERROR_MUSIC_NOT_PAUSED)

@bot.command(name="skip")
async def skip(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.stop()
        await ctx.send(messages.MESSAGE_SKIPPED)
        await play_next_song(ctx)
    else:
        await ctx.send(messages.ERROR_NO_MUSIC_PLAYING)

@bot.command(name="shuffle")
async def shuffle(ctx):
    guild_id = ctx.guild.id
    if guild_id in music_queue and len(music_queue[guild_id]) > 1:
        random.shuffle(music_queue[guild_id])
        await ctx.send(messages.MESSAGE_QUEUE_SHUFFLED)
    else:
        await ctx.send(messages.ERROR_NO_MUSIC_FOUND)

@bot.command(name="queue")
async def queue(ctx):
    guild_id = ctx.guild.id
    if guild_id in music_queue and music_queue[guild_id]:
        queue_list = "\n".join([f"{index + 1}. {song['title']}" for index, song in enumerate(music_queue[guild_id])])
        await ctx.send(messages.MESSAGE_CURRENT_QUEUE.format(queue=queue_list))
    else:
        await ctx.send(messages.MESSAGE_QUEUE_EMPTY)

@bot.command(name="remove")
async def remove(ctx, position: int):
    guild_id = ctx.guild.id
    if guild_id in music_queue and len(music_queue[guild_id]) >= position > 0:
        removed_song = music_queue[guild_id].pop(position - 1)
        await ctx.send(messages.MESSAGE_REMOVED_SONG.format(title=removed_song['title']))
    else:
        await ctx.send(messages.ERROR_INVALID_POSITION)

@bot.event
async def on_ready():
    print(messages.MESSAGE_BOT_READY.format(bot_user=bot.user))

bot.run(DISCORD_TOKEN)
