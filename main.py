import voice as voice
import discord
import threading
from PyQt5.QtCore import Qt, QTimer
import time
import asyncio
from async_timeout import timeout
from discord.ext import commands
from discord.ext import tasks, commands
import youtube_dl
#from cogs.utils.clip import *

TOKEN = 'token'

players = {}


# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options,
                   executable="C:/Users/User/PycharmProjects/RACHKO_BOT/ffmpeg/bin/ffmpeg.exe"), data=data)

class MyContext(commands.Context):

    async def tick(self, value):
        # reacts to the message with an emoji
        # depending on whether value is True or False
        # if its True, it'll add a green check mark
        # otherwise, it'll add a red cross mark
        emoji = '\N{WHITE HEAVY CHECK MARK}' if value else '\N{CROSS MARK}'
        try:
            # this will react to the command author's message
            await self.message.add_reaction(emoji)
        except discord.HTTPException:
            # sometimes errors occur during this, for example
            # maybe you dont have permission to do that
            # we dont mind, so we can just ignore them
            pass


class MyBot(commands.Bot):
    vc = "0"
    last_ctx = None
    #vc = discord.VoiceClient
    queue = []
    queue_size = 0

    async def get_context(self, message, *, cls=MyContext):
        # when you override this method, you pass your new Context
        # subclass to the super() method, which tells the bot to
        # use the new MyContext class
        return await super().get_context(message, cls=cls)


#bot = commands.Bot(command_prefix='!', description="description")
bot = MyBot(command_prefix='!', description="RACHKO-BOT")
queue_async = asyncio.Queue()
#ctx.bot.loop.create_task(self.player_loop())



class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.index = 0
        self.player.start()


    def cog_unload(self):
        print("cog_unload")
        self.player.cancel()
        #self.printer.stop()


    @tasks.loop(seconds=5.0)
    async def player(self):
        playing = None
        paused = None

        print("is_closed - "+str(bot.is_closed()))
        if not bot.is_closed():
            #check if playing track and connected
            playing = bot.vc.is_playing()
            paused = bot.vc.is_paused()
            print("vc.is_connected() - " + str(bot.vc.is_connected()))
            print("vc.is_playing()) - " + str(playing))
            print("Status: ", end="")
            if playing or paused:
                print("playing...")
            else:
                print("not playing")
                #check if we have next track
                if have_next():
                    print("play next song")
                    print("getting ctx..." )
                    ctx = bot.last_ctx
                    print("got ctx " + str(ctx))
                    await next(ctx)
                else:
                    print("No next song")
        print("-----------------------------------------")


    @player.before_loop
    async def before_printer(self):
        #time.sleep(5)
        print('waiting... for bot ready')
        await self.bot.wait_until_ready()
        #time.sleep(5)


def have_next():
    if queue_async.qsize() > 0:
        return True
    else:
        return False

async def setup():
    print("setup")
    bot.add_cog(MyCog(bot))


@bot.command(pass_context=True)
async def help_bot(ctx):
    await ctx.send("!help       - помощь")
    await ctx.send("!play       - стрим аудио из вк или yt, если уже что-то играет то трек добавляется в очередь ")
    await ctx.send("!disconnect - отключиться из голосового канала")
    await ctx.send("!stop       - остановить воспроизведение аудио")
    await ctx.send("!pause      - поставить на паузу аудио")
    await ctx.send("!resume     - продолжить воспроизведение")
    await ctx.send("!next       - следующий трек в очереди")


@bot.command(pass_context=True)
async def join(ctx):  # создаем асинхронную фунцию бота
    channel = ctx.author.voice.channel
    bot.vc = await channel.connect()
    await ctx.send("RACHKO-BOT в этом чатике")


@bot.command(pass_context=True)
async def disconnect(ctx):  # создаем асинхронную фунцию бота
    #await disconnect(*, force=False)
    await bot.vc.disconnect()
    #await ctx.send("Disconnect")
    await ctx.send("Понял. Ушел...")


@bot.command(pass_context=True)
async def play_test(ctx):  # создаем асинхронную фунцию бота
    bot.vc.play(discord.FFmpegPCMAudio(executable="C:/Users/User/PycharmProjects/RACHKO_BOT/ffmpeg/bin/ffmpeg.exe",
                                    source="testing.mp3"))
    await ctx.send("Playing")


@bot.command(pass_context=True)
async def queue(ctx):  # создаем асинхронную фунцию бота
    if bot.queue_size == 0:
        await ctx.send("Ало!!! где треки?")
        return
    await ctx.send("======================== Наш текущий плейлист ========================")
    i = 0
    for item in bot.queue:
        if i==0:
            await ctx.send(">>" + " " + str(item))
        else:
            await ctx.send(str(i) + " - " + str(item))
        i += 1

    await ctx.send("======================================================================")


@bot.command(pass_context=True)
async def next(ctx):  # создаем асинхронную фунцию бота
    bot.last_ctx = ctx
    await stop(ctx)
    #await ctx.send("Стоп Размер очереди - " + str(bot.queue_size))
    if queue_async.qsize() > 0:
        print("get next track (next)")
        bot.queue.pop(0)
        bot.queue_size -= 1
        url = await queue_async.get()
        #await play(ctx=ctx, url=bot.queue[0])
        print("start playing " + str(url))
        await play(ctx=ctx, url=url)
    else:
        print("no more tracks")
        #time.sleep(2)
        #await ctx.send("Ожидаю трек")
    #await queue(ctx)


@bot.command(pass_context=True)
async def play(ctx, *, url):
    #f = open('music_base.txt', 'w')
    f = open('music_base.txt', 'a')
    f.write(url+ '\n')
    f.close()
    bot.last_ctx = ctx
    add_task = False
    # async with ctx.typing():
    if bot.vc == "0":
        print("бот не был подключен, подключаюсь")
        await join(ctx)
        bot.queue_size += 1
        bot.queue.append(url)
        #await queue_async.put(url)
        add_task = True
    if bot.vc.is_playing():
        await ctx.send("Добавляю в очередь ")  # url
        print("Добавляю в очередь " + str(url))
        bot.queue.append(url)
        bot.queue_size += 1
        await queue_async.put(url)
    else:
        print("Воспроизведение " + str(url))
        player = await YTDLSource.from_url(url, loop=bot.loop) #, stream=True
        bot.vc.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
        # await ctx.send("Поток пошел")
        print("Поток пошел")
        if add_task:
            await setup()
            #ctx.bot.loop.create_task(player_loop(ctx))



@bot.command(pass_context=True)
async def test(ctx):
    bot.last_ctx = ctx
    print("start")
    bot.add_cog(MyCog(bot))
    print("end")


@bot.command(pass_context=True)
async def pause(ctx):  # создаем асинхронную фунцию бота
    bot.last_ctx = ctx
    bot.vc.pause()
    await ctx.send("Ожидаю")


@bot.command(pass_context=True)
async def stop(ctx):  # создаем асинхронную фунцию бота
    bot.last_ctx = ctx
    bot.vc.stop()
    print("stop")
    #await ctx.send("Стоп машина")


@bot.command(pass_context=True)
async def resume(ctx):  # создаем асинхронную фунцию бота
    bot.last_ctx = ctx
    bot.vc.resume()
    await ctx.send("Продолжаем")


bot.run(TOKEN)