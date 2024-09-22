import re
import discord
from discord.ext import commands
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp as youtube_dl
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID,
                                                                             client_secret=SPOTIFY_CLIENT_SECRET))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="-", intents=intents)

music_queue = {}

def search_spotify(query):
    try:
        result = spotify.search(q=query, type='track', limit=1)
        if result and result['tracks']['items']:
            track = result['tracks']['items'][0]
            return {'source': track['external_urls']['spotify'], 'title': track['name']}
        else:
            return None
    except Exception as e:
        print(f"Erro ao buscar no Spotify: {str(e)}")
        return None

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
        await ctx.send("Por favor, forneça uma URL ou um nome de música!")
        return

    song = None

    song = search_spotify(query)
    
    if not song:
        song = search_youtube(query)

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
                await ctx.send("Você precisa estar em um canal de voz!")
        else:
            await ctx.send(f"A música **{song['title']}** foi adicionada à fila.")
    else:
        await ctx.send("Erro: Não foi possível obter o link de áudio.")

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}!')

bot.run(DISCORD_TOKEN)
