import voice as voice
import discord
import threading
from PyQt5.QtCore import Qt, QTimer
import time
import asyncio
from discord.ext import commands
import youtube_dl

TOKEN = 'NzMwMDE4NDcwODQ2MTM2MzY5.XwRa2g.rMUlYSjB0ysPeGcEoSoGmbR83fg'
bot = commands.Bot(command_prefix='!')

players = {}
queues = {}
channel_id = "730481955698901103"
vc = None

@bot.command(pass_context=True)  # разрешаем передавать агрументы
async def test(ctx):  # создаем асинхронную фунцию бота
    #await ctx.send(ctx.author.voice)
    channel = ctx.author.voice.channel
    vc = await channel.connect()

    #vc.play(discord.FFmpegPCMAudio('testing.mp3'), after=lambda e: print('done', e))
    vc.play(discord.FFmpegPCMAudio(executable = "C:/Users/User/PycharmProjects/RACHKO_BOT/ffmpeg/bin/ffmpeg.exe", source="testing.mp3"))
    vc.is_playing()

    #vc.pause()
    #vc.resume()
    #time.sleep(5)
    #vc.stop()
    await ctx.send("Done")
@bot.command(pass_context=True)
async def hi(ctx):  # создаем асинхронную фунцию бота
    await ctx.send("Hello world")  # отправляем обратно аргумент

@bot.command()
async def stop(ctx):
    channel = ctx.author.voice.channel
    #vc = await channel.connect()
    #hannel.stop()

    await ctx.send("Stoped")
    # await ctx.voice_client.disconnect(channel)

bot.run(TOKEN)