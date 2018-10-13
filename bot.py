from cogs.utils.creds import discordtoken, webhookid, webhooktoken
import discord
from discord.ext import commands
import logging
import sys
import datetime
import traceback
import sqlite3
from collections import Counter, deque
import contextlib
import aiosqlite
import os

db_path = os.path.join(os.getcwd(), 'cogs', 'utils', 'database.db')
conn = sqlite3.connect(db_path)
# conn is for routine db entries/fetch (ie get prefix)
c = conn.cursor()
webhook = discord.Webhook.partial(id=webhookid, token=webhooktoken, adapter=discord.RequestsWebhookAdapter())
# webhook for logging command errors
TOKEN = discordtoken
initial_extensions = ['cogs.JokesCommands',
                      'cogs.GamesCommands',
                      'cogs.StatsCommands',
                      'cogs.Hangman',
                      'cogs.tools',
                      'cogs.admin']

# cogs to load


@contextlib.contextmanager
def setup_logging():
    try:
        # __enter__
        # haven't set this up yet. might've maybe copied a bit of it
        logging.getLogger('discord').setLevel(logging.INFO)
        logging.getLogger('discord.http').setLevel(logging.WARNING)

        log = logging.getLogger()
        log.setLevel(logging.INFO)
        handler = logging.FileHandler(filename='mathsbot.log', encoding='utf-8', mode='w')
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter('[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')
        handler.setFormatter(fmt)
        log.addHandler(handler)

        yield
    finally:
        # __exit__
        handlers = log.handlers[:]
        for hdlr in handlers:
            hdlr.close()
            log.removeHandler(hdlr)


def run_bot():
    log = logging.getLogger()
    bot = MathsBot()
    bot.run()
    # run bot


def find_prefix(bot, msg):
    # callable prefix
    bot_id = bot.user.id
    # bot user id
    prefixes = [f'<@{bot_id}> ', f'<@!{bot_id}> ']
    # @mathsbot is always going to be a prefix
    if msg.guild is None:
        prefixes.append('!')
        # prefix is ! in dms
    else:
        c.execute("SELECT prefix FROM guildinfo WHERE guildid = :id",
                  {'id': msg.guild.id})
        dump = c.fetchall()
        # get prefix from db for guildid
        if len(dump) == 0:
            # if no prefix in db/set prefixes are ! ?
            prefixes.extend(['!', '?'])
        else:
            # otherwise add prefix in db to the prefixes (mentions)
            prefixes.extend([n[0] for n in dump])
    return prefixes


class MathsBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=find_prefix, case_insensitive=True)
        # setup bot
        self.remove_command(name='help')
        # we have our own help formatter
        self._prev_events = deque(maxlen=10)
        # idk what this does but it works
        self.webhook = webhook
        # assign error log webhook to bot, make it easy to call elsewhere

        for extension in initial_extensions:
            # load cogs
            try:
                self.load_extension(extension)
            except Exception as e:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                print(e)

    async def on_ready(self):
        if not hasattr(self, 'uptime'):
            # add attribute when script started to bot
            self.uptime = datetime.datetime.utcnow()
        # tell us bot is online
        print(f'Ready: {self.user} (ID: {self.user.id})')
        print(self.uptime)

    async def on_socket_response(self, msg):
        # whenever we get a socket response (ie. typing start, any message, reaction, most basic events
        self._prev_events.append(msg)

    async def on_message(self, message):
        # on any message
        if message.author.bot:
            # ignore command if author is a bot
            return
        # send rest of messages through (to look for prefix, command etc.)
        await self.process_commands(message)

    async def on_command(self, ctx):
        await ctx.message.channel.trigger_typing()

    async def on_command_error(self, ctx, error):
        # we dont want logs for this stuff which isnt our problem
        ignored = (commands.NoPrivateMessage, commands.DisabledCommand, commands.CheckFailure,
                   commands.CommandNotFound, commands.UserInputError, discord.Forbidden)
        error = getattr(error, 'original', error)
        # filter errors we dont want
        if isinstance(error, ignored):
            return
        # send error to log channel
        e = discord.Embed(title='Command Error', colour=0xcc3366)
        e.add_field(name='Name', value=ctx.command.qualified_name)
        e.add_field(name='Author', value=f'{ctx.author} (ID: {ctx.author.id})')

        fmt = f'Channel: {ctx.channel} (ID: {ctx.channel.id})'
        if ctx.guild:
            fmt = f'{fmt}\nGuild: {ctx.guild} (ID: {ctx.guild.id})'

        e.add_field(name='Location', value=fmt, inline=False)
        # format legible traceback
        exc = ''.join(traceback.format_exception(type(error), error, error.__traceback__, chain=False))
        e.description = f'```py\n{exc}\n```'
        e.timestamp = datetime.datetime.utcnow()
        # send to log channel with webhook attribute assigned to bot earlier
        self.webhook.send(embed=e)

    def get_prefixes(self, msg):
        # gonna use later to find prefix of guild/msg etc.
        return find_prefix(self, msg)

    async def set_guild_prefixes(self, msg, prefix):
        # update a prefix for a guild
        if len(prefix) == 0:
            # raise bad argument (no prefix)
            raise commands.BadArgument("Please give me a prefix to set!")

        async with aiosqlite.connect(db_path) as db:
            # override current prefix in db with new one
            await db.execute("UPDATE guildinfo SET prefix = :pref WHERE guildid = :id",
                             {'pref': prefix[0], 'id': msg.guild.id})
            # save changes
            await db.commit()


    def send_guild_stats(self, e, guild):
        # when bot joins a server I want to know about it. Sends info about the server
        e.add_field(name='Name', value=guild.name)
        e.add_field(name='ID', value=guild.id)
        e.add_field(name='Owner', value=f'{guild.owner} (ID: {guild.owner.id})')
        # gives me stats about how many/percentage of bots
        bots = sum(m.bot for m in guild.members)
        total = guild.member_count
        online = sum(m.status is discord.Status.online for m in guild.members)
        e.add_field(name='Members', value=str(total))
        e.add_field(name='Bots', value=f'{bots} ({bots/total:.2%})')
        e.add_field(name='Online', value=f'{online} ({online/total:.2%})')

        if guild.icon:
            e.set_thumbnail(url=guild.icon_url)

        if guild.me:
            e.timestamp = guild.me.joined_at
        # send to error log channel with same webhook assigned to bot
        self.webhook.send(embed=e)

    async def on_guild_join(self, guild):
        # when I join a guild send message to error log channel that I've joined a guild
        e = discord.Embed(colour=0x53dda4, title='New Guild')  # green colour
        self.send_guild_stats(e, guild)
        sys_channel = guild.system_channel
        if sys_channel:
            # if there is a 'default' channel (ie. where default discord welcome msg pops up) send message there
            await sys_channel.send('Hello, thanks for adding me! \N{UPSIDE-DOWN FACE} '
                                   'You can find my help with `!help` and change my prefix with '
                                   '`!changeprefix [new prefix]`')
        else:
            # otherwise just get all text channels in guild
            for channel in guild.text_channels:
                try:
                    # send message to first one that pops up
                    await channel.send("Hello, thanks for adding me! \N{UPSIDE-DOWN FACE}. I couldn't find"
                                       "a default channel so came here. "
                                       "You can find my help with `!help` and change my prefix with "
                                       "`!changeprefix [new prefix]`")
                    return
                except discord.Forbidden:
                    # I dont have permissions to send messages in this channel, continue to next one
                    pass
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT * FROM action_log_config WHERE guildid = :id",
                                 {'id': guild.id})
            dump = await c.fetchall()
            if len(dump) == 0:
                await db.execute("INSERT INTO action_log_config VALUES ('0000000000000000000000',"
                                 " :id, '', '', '', '', '')",
                                 {'id': guild.id})
                await db.execute("INSERT INTO guildinfo VALUES (:id, '', 0)",
                                 {'id': guild.id})

    async def on_guild_remove(self, guild):
        # when bot leaves a guild send msg to error log channel
        e = discord.Embed(colour=0xdd5f53, title='Left Guild')  # red colour
        self.send_guild_stats(e, guild)

    def find_command(self, bot, command):
        """Finds a command (be it parent or sub command) based on string given"""
        # idk why this is still here from old help message maker I made
        cmd = None

        for part in command.split():
            try:
                if cmd is None:
                    cmd = bot.get_command(part)
                else:
                    cmd = cmd.get_command(part)
            except AttributeError:
                cmd = None
                break

        return cmd

    def run(self):
        # run it or tell me why it won't work
        try:
            super().run(TOKEN)
        except Exception as e:
            print(e)

    @property
    def config(self):
        return __import__('config')


if __name__ == '__main__':
    with setup_logging():
        # run bot with logging which I'm yet to set up
        run_bot()
