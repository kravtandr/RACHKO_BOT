"""
The MIT License (MIT)

Copyright (c) 2020 kravtandr

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
import random
import discord
import asyncio
from discord.ext import tasks, commands
import youtube_dl

#read cfg.txt
f = open('cfg.txt', 'r')
i = 0
for line in f:
    if i==0:
        line = line.split()
        TOKEN = line[2]
    i+=1
f.close()
#TOKEN = 'token'


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
    vc = "0" # очень больно так делать
    #vc = discord.VoiceClient
    last_ctx = None # и так тоже
    is_looped = False
    curr_track = None
    queue = []  # фальшивая очередь для вывода
    queue_size = 0

    async def get_context(self, message, *, cls=MyContext):
        # when you override this method, you pass your new Context
        # subclass to the super() method, which tells the bot to
        # use the new MyContext class
        return await super().get_context(message, cls=cls)


#bot = commands.Bot(command_prefix='!', description="description")
bot = MyBot(command_prefix='!', description="RACHKO-BOT")
queue_async = asyncio.Queue()
bot.remove_command('help')
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


    @tasks.loop(seconds=5.0) # main loop
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
                if bot.is_looped:
                    await play(ctx= bot.last_ctx, url=bot.curr_track)
                    #print("repeating " +str(bot.queue[0]))
                    print("repeating " + str(bot.curr_track))
                else:
                    print("not playing")
                    # check if we have next track
                    if have_next():
                        print("play next song")
                        print("getting ctx...")
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
async def music(ctx, num = 3):  # делает плейлист из уже игравших треков
    i = 0
    count = 0
    all_found = False
    nLines = count_lines("music_base.txt")
    print("LINES = ", nLines)

    while not all_found:
        f = open('music_base.txt', 'r')
        rand = random.randint(0, nLines)
        start = random.randint(0, rand)
        for line in f: #line.rstrip() for line in l
            line = line.strip()
            print("i= " + str(i), "count = " + str(count), start, rand)
            if line.isspace():
                print("seek 0")
                f.seek(0)
            if i >= start and i == rand:
                if count < int(num):
                    bot.queue.append(line)
                    await queue_async.put(line)
                    print("+ in q " + str(line))
                    bot.queue_size += 1
                    count += 1
                    rand = random.randint(0, nLines)
                    start = random.randint(0, rand)
                    i = 0
                else:
                    print("all found")
                    # bot.queue.reverse()
                    line = await queue_async.get()
                    await play(ctx=ctx, url=line)
                    await queue(ctx)
                    all_found = True
                    return
            # print(line)
            else:
                print("i < start and i != rand")
                if i<start or i>nLines:
                    i=start
            print("i = ", i," count = ", count)
            print("start = ", start, " rand = ", rand)
            i+=1
        i = 0
        f.close()



    #await ctx.send(bot.queue_size)



@bot.command(pass_context=True)
async def help(ctx):
    '''
    await ctx.send("!help - помощь")
    await ctx.send("!play - аудио из вк или yt, если уже что-то играет то трек добавляется в очередь. \n"
                   "         (стримы не работают, тк все файлы перед воспроизведением скачиваются) ")
    await ctx.send("!music <число треков> - создает плейлист из треков, которые уже играли, по умолчанию размер плейлиста = 3")
    await ctx.send("!queue - выводит в текстовый канал текущий плейлист")
    await ctx.send("!pause - поставить на паузу аудио")
    await ctx.send("!resume - продолжить воспроизведение")
    await ctx.send("!next - следующий трек в очереди")
    await ctx.send("!cur - текущий трек")
    await ctx.send("!disconnect - отключиться из голосового канала")
    await ctx.send("!stop - остановить воспроизведение аудио")
    '''
    await ctx.send("```!help                 -  помощь\n"
                   "!play                 -  аудио из вк или yt, если уже что-то играет, то трек добавляется в очередь. \n "
                   "                        (стримы не работают, тк все файлы перед воспроизведением скачиваются)\n"
                   "!music <число треков> - создает плейлист из треков, которые уже играли, по умолчанию размер плейлиста = 3\n"
                   "!loop                 -  вкл/выкл повтор\n"
                   "!queue                -  выводит в текстовый канал текущий плейлист\n"
                   "!pause                -  поставить на паузу аудио\n"
                   "!resume               -  продолжить воспроизведение\n"
                   "!next                 -  следующий трек в очереди\n"
                   "!cur                  -  текущий трек\n"
                   "!clear                -  очищает плейлист\n"
                   "!disconnect           -  отключиться из голосового канала\n"
                   "!stop                 -  остановить воспроизведение аудио\n"
                   "=======================================dev================================================================\n"
                   "!format_music_base     -  удаляет одинаковые треки из базы```")


@bot.command(pass_context=True)
async def loop(ctx):  # создаем асинхронную фунцию бота
    bot.is_looped = not bot.is_looped
    await ctx.send("Повтор: "+str(bot.is_looped))


@bot.command(pass_context=True)
async def cur(ctx):  # создаем асинхронную фунцию бота
    await ctx.send("Сейчас играет: " + str(bot.curr_track))


@bot.command(pass_context=True)
async def clear(ctx):  # очищаем очередь
    await bot.wait_until_ready()
    while have_next():
        if queue_async.qsize() > 0:
            bot.queue.pop(0)
            bot.queue_size -= 1
            url = await queue_async.get()
    bot.queue = []  # фальшивая очередь для вывода
    bot.queue_size = 0
    await ctx.send("Произошло глубинное очищение")


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
async def play_test(ctx):  # играет любой mp3 из папки где находится
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
    if bot.is_looped:
        await play(ctx=ctx, url=bot.curr_track)
        await ctx.send("Повтор")
    else:
        if queue_async.qsize() > 0:
            print("get next track (next)")
            bot.queue.pop(0)
            bot.queue_size -= 1
            url = await queue_async.get()
            # await play(ctx=ctx, url=bot.queue[0])
            print("start playing " + str(url))
            await play(ctx=ctx, url=url)
            await ctx.send("Следующий трек")
        else:
            print("no more tracks")
            # time.sleep(2)
            await ctx.send("Ало!!! где треки?")


@bot.command(pass_context=True)
async def play(ctx, *, url):
    #f = open('music_base.txt', 'w')
    f = open('music_base.txt', 'a')
    f.write(str(url) + '\n')
    print(str(url) + '\n')
    f.close()
    bot.last_ctx = ctx
    add_task = False
    # async with ctx.typing():
    if bot.vc == "0":
        print("бот не был подключен, подключаюсь")
        await join(ctx)
        bot.queue_size += 1
        bot.queue.append(url)
        print("+ in q " + str(url))
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
        bot.curr_track = url
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


def count_lines(filename, chunk_size=1<<13):
    with open(filename) as file:
        return sum(chunk.count('\n')
                   for chunk in iter(lambda: file.read(chunk_size), ''))

@bot.command(pass_context=True)
async def format_music_base(ctx):
    nlines=count_lines("music_base.txt")
    dnlines=nlines
    input = open('music_base.txt', 'r')
    source = open('music_base_tmp.txt', 'w')
    data=[]
    for line in input:
        if line not in data:
            data.append(line)
            source.write(line)
        else:
            dnlines -= 1
    if nlines == dnlines:
        await ctx.send("В базе нет одинаковых треков")
    else:
        input.close()
        source.close()
        source = open('music_base_tmp.txt', 'r')
        output = open('music_base.txt', 'w')
        for line in source:
            output.write(line)
        source.close()
        output.close()
        print("format music base", nlines, dnlines)
        await ctx.send("music_base from " + str(nlines) + " to " + str(dnlines))


bot.run(TOKEN)