import discord
from discord.ext import commands
import logging
import sys
import datetime
import traceback
from collections import deque
import contextlib
import os
import json
import functools

import creds
import click
import importlib
import asyncio
from cogs.utils.db import Table
from cogs.utils import context
import config


db_path = os.path.join(os.getcwd(), 'cogs', 'utils', 'database.db')
json_location = os.path.join(os.getcwd(), 'cogs', 'utils', 'mathsbot.json')

webhook = discord.Webhook.partial(id=creds.webhookid, token=creds.webhooktoken, adapter=discord.RequestsWebhookAdapter())

# webhook for logging command errors
initial_extensions = ['cogs.jokes',
                      'cogs.games',
                      'cogs.stats',
                      'cogs.hangman',
                      'cogs.mod',
                      'cogs.admin',
                      'cogs.roles',
                      'cogs.leaderboard'
                      ]

# cogs to load


def run_bot():
    loop = asyncio.get_event_loop()
    log = logging.getLogger()

    try:
        pool = loop.run_until_complete(Table.create_pool(config.postgresql, command_timeout=60))
    except Exception as e:
        click.echo('Could not set up PostgreSQL. Exiting.', file=sys.stderr)
        log.exception('Could not set up PostgreSQL. Exiting.')
        return
    bot = MathsBot()
    bot.pool = pool
    bot.run()
    # run bot


class MathsBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=self.find_prefix, case_insensitive=True)
        # setup bot
        self.remove_command(name='help')
        # we have our own help formatter
        self._prev_events = deque(maxlen=10)
        self.webhook = webhook
        # # assign error log webhook to bot, make it easy to call elsewhere
        self.extns = initial_extensions

        with open(json_location) as guildinfo:
            self.loaded = json.load(guildinfo)

        for e in initial_extensions:
            # load cogs
            try:
                self.load_extension(e)
            except Exception as e:
                print(f'Failed to load extension {e}.', file=sys.stderr)
                print(e)

    def get_guild_prefix(self, guildid):
        pref = []
        for prefixes in self.loaded['prefixes']:
            if prefixes['guildid'] == guildid:
                pref.append(prefixes['prefix'])
        return pref

    def get_ignored(self, guildid, cid='all'):
        ignored = []
        for users_channels in self.loaded['ignored']:
            if cid == 'all':
                if users_channels['guildid'] == guildid:
                    ignored.append(users_channels['id'])
            else:
                if (users_channels['id'] == cid) and (users_channels['guildid'] == guildid):
                    ignored.append(users_channels['id'])
        return ignored

    def get_global_ignored(self, id):
        ignored = []
        for users_channels in self.loaded['global_ignored']:
            if id == 'all':
                ignored.append(users_channels['id'])
            else:
                if users_channels['id'] == id:
                    ignored.append(users_channels['id'])
        return ignored

    def get_blacklisted(self, id):
        for guildids in self.loaded['blacklisted_guilds']:
            return guildids['id'] == id

    def get_colours(self, guildid, colour):
        roles = []
        for role in self.loaded['colour_roles']:
            if (role['colour'] == colour) and (role['guildid'] == guildid):
                roles.append(role)
            if (colour == 'all') and (role['guildid'] == guildid):
                roles.append(role)
        return roles

    def get_config(self, guildid, config, *, userid):
        for role in self.loaded['config']:
            if role['guildid'] == guildid:
                return role[config]
        return False

    def get_admin(self, guildid, userid):
        for admin in self.loaded['admin']:
            if (admin['guildid'] == guildid) and (admin['userid'] == userid):
                return True
        return False

    def get_mod(self, guildid, userid):
        for mod in self.loaded['mod']:
            if (mod['guildid'] == guildid) and (mod['userid'] == userid):
                return True
        return False

    def find_prefix(self, bot, msg):
        # callable prefix
        bot_id = bot.user.id
        # bot user id

        prefixes = [f'<@{bot_id}> ', f'<@!{bot_id}> ']
        # @mathsbot is always going to be a prefix

        if msg.guild is None:
            prefixes.append('!')
            # prefix is ! in dms

        else:
            try:
                prefix = self.get_guild_prefix(msg.guild.id)
                prefixes.extend(prefix)
                if not prefix:
                    prefixes.append('!')
            except KeyError:
                prefixes.extend(['!', '?'])

        return prefixes

    def save_to_json(self):
        """
        Save json to the file.
        """

        with open(json_location, 'w') as outfile:
            json.dump(self.loaded, outfile)

    async def save_json(self):
        thing = functools.partial(self.save_to_json)

        await self.loop.run_in_executor(None, thing)

    async def on_message(self, message):
        # on any message
        if message.author.bot:
            # ignore command if author is a bot
            return
        # if message.author.id != 230214242618441728:
        #     return

        # ignored = self.get_ignored(message.guild.id, cid='all')
        # ignored.extend(self.get_global_ignored('all'))
        # if message.guild.id in ignored:
        #     return
        # if message.channel.id in ignored:
        #     return
        # if message.author.id in ignored:
        #     return
        # send rest of messages through (to look for prefix, command etc.)
        await self.process_commands(message)

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=context.Context)

        if ctx.command is None:
            return

        async with ctx.acquire():
            await self.invoke(ctx)

    async def on_command(self, ctx):
        await ctx.message.channel.trigger_typing()

    async def on_command_error(self, ctx, error):
        print('ok')
        print(''.join(traceback.format_exception(type(error), error, error.__traceback__, chain=False)))
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
        if self.get_blacklisted(guild.id):
            for channel in guild.text_channels:
                try:
                    channel.send("It appears this server has been blacklisted :thinking_face: "
                                 "This could be because"
                                 " you have too many bots or members spamming messages that will lag my client. "
                                 "If you believe this is incorrect, please join my support server: xxyyzz")
                    return await guild.leave()
                except discord.Forbidden:
                    pass
            return await guild.leave()
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
                await db.execute("INSERT INTO guildinfo VALUES (:id, '!', 0)",
                                 {'id': guild.id})
            await db.commit()

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
        print('ok')
        try:
            super().run(creds.discordtoken)
        except Exception as e:
            print(e)

    @property
    def config(self):
        return __import__('config')



if __name__ == '__main__':
    bot = MathsBot()
    bot.run(config.token)
