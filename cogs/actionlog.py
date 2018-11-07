import discord
from discord.ext import commands
import asyncio
from cogs.utils.help import HelpPaginator
import webcolors
import aiosqlite
import enum
import re
import os
import datetime
import io
from .admin import TabularData

db_path = os.path.join(os.getcwd(), 'cogs', 'utils', 'database.db')

# action log in progress


class ChannelConverter(commands.Converter):
    async def convert(self, ctx, argument):
        _id_regex = re.compile(r'([0-9]{15,21})$')

        def _get_id_match(argument):
            return _id_regex.match(argument)

        def _get_from_guilds(bot, getter, argument):
            result = None
            for guild in bot.guilds:
                result = getattr(guild, getter)(argument)
                if result:
                    return result
            return result

        bot = ctx.bot

        match = _get_id_match(argument) or re.match(r'<#([0-9]+)>$', argument)
        result = None
        guild = ctx.guild

        if match is None:
            # not a mention
            if guild:
                result = discord.utils.get(guild.text_channels, name=argument)
                if result is None:
                    result = discord.utils.get(guild.categories, name=argument)

            else:
                def check(c):
                    return isinstance(c, (discord.TextChannel, discord.CategoryChannel)) and c.name == argument
                result = discord.utils.find(check, bot.get_all_channels())
        else:
            channel_id = int(match.group(1))
            if guild:
                result = guild.get_channel(channel_id)
            else:
                result = _get_from_guilds(bot, 'get_channel', channel_id)

        if not isinstance(result, (discord.TextChannel, discord.CategoryChannel)):
            raise commands.BadArgument('Channel or category "{}" not found. If you are using a multi-word name,'
                                       ' you need to surround the whole name in " " for me'
                                       ' to read it as one channel (not 2)'.format(argument))

        return result


class _ActionLog(enum.Enum):
    on = 1
    off = 0

    def __str__(self):

        return self.name


Modules = ['welcome_message',
           'leave_message',
           'on_member_join',
           'on_member_leave',
           'on_member_kicked',
           'on_member_banned',
           'on_member_unbanned',
           'on_message_edit',
         'on_message_delete',
         'on_mass_message_delete',
         'on_role_given',
         'on_role_created',
         'on_role_edit',
         'on_role_removed',
         'on_channel_created',
         'on_channel_edit',
         'on_channel_removed',
         'on_invite_posted',
         'on_invite_created',
         'on_nickname_change',
        'on_avatar_change',
         'on_server_edit',
         'on_moderator_commands',
         ]


class ActionLog:
    # work in progress
    __slots__ = ('action_log', 'guildid', 'bot', 'action_log_channel_id', 'welcome_message', 'leave_message', 'record')

    @classmethod
    async def from_db(cls, record, bot):
        record = record[0]
        self = cls()
        self.record = record
        self.bot = bot
        self.action_log = record[0]
        self.guildid = record[1]
        self.action_log_channel_id = record[2]
        self.welcome_message = record[3]
        self.leave_message = record[5]
        return self

    @property
    def action_log_channel(self):
        guild = self.bot.get_guild(int(self.guildid))
        channel = self.bot.get_channel(int(self.action_log_channel_id))
        return guild and channel

    @property
    def lookup_enabled_action_log(self):
        lookup = Modules
        enabled = []
        disabled = []
        for index, item in enumerate(self.action_log):
            if item == '0':
                disabled.append(lookup[index])
            else:
                enabled.append(lookup[index])
        return enabled

    @property
    def lookup_disabled_action_log(self):
        lookup = Modules
        disabled = []
        for index, item in enumerate(self.action_log):
            if item == '0':
                disabled.append(lookup[index])
        return disabled


class WatchLog:
    __slots__ = ('guild_id', 'userid', 'record', 'bot', 'toggled', 'watch_log_channel_id')

    @classmethod
    async def from_db(cls, record, bot):
        record = record[0]
        self = cls()
        self.record = record
        self.bot = bot
        self.userid = record[0]
        self.watch_log_channel_id = record[1]
        self.guild_id = record[2]
        self.toggled = record[3]
        return self

    @property
    def watch_log_channel(self):
        guild = self.bot.get_guild(int(self.guild_id))
        channel = self.bot.get_channel(int(self.watch_log_channel_id))
        return guild and channel

    @property
    def lookup_enabled_watch_log(self):
        lookup = Modules
        enabled = []
        disabled = []
        for index, item in enumerate(self.toggled):
            if item == '0':
                disabled.append(lookup[index])
            else:
                enabled.append(lookup[index])
        return enabled

    @property
    def lookup_disabled_watch_log(self):
        lookup = Modules
        disabled = []
        for index, item in enumerate(self.toggled):
            if item == '0':
                disabled.append(lookup[index])
        return disabled


class ActionLogConfig:
    def __init__(self, bot, msg, ctx, dump, config):
        self.bot = bot
        self.msg = msg
        self.modules_set = ''
        self.ctx = ctx
        self.dump = dump
        self.config = config
        self.prev_set = config.action_log
        self.enabled = []

    async def add_reaction(self, msg):
        await msg.add_reaction('\N{WHITE HEAVY CHECK MARK}')
        await msg.add_reaction('\N{CROSS MARK}')
        await msg.add_reaction('\N{WHITE QUESTION MARK ORNAMENT}')

    async def choose_actionlog_channel(self):
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name="Which channel would you like me to send actionlogs to? Reply with a channel within 60sec."
                          " If no channel is selected, I will send them to the channel we are currently in.",
                     icon_url=self.ctx.author.avatar_url)
        msg = await self.ctx.send(embed=e)
        while True:
            try:
                channelmsg = await self.bot.wait_for('message', check=self.msgcheck, timeout=60)
                channelid = channelmsg.raw_channel_mentions[0]
                break
            except asyncio.TimeoutError:
                channelid = self.ctx.channel.id
                break
        async with aiosqlite.connect(db_path) as db:
            await db.execute("UPDATE action_log_config SET action_log_id = :channelid WHERE guildid = :guildid",
                             {'channelid': channelid, 'guildid': self.ctx.guild.id})
            await db.commit()
        e.set_author(name=f"ActionLog Channel has been changed to: ",
                     icon_url=self.ctx.author.avatar_url)
        e.description = f"<#{channelid}>. If you want to change that, rerun the command."
        await msg.edit(embed=e)

    async def set_welcome_channel(self, msg):
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name="Please send a channel for welcome messages to be sent in",
                     icon_url=self.ctx.author.avatar_url)
        e.description = 'Eg. `#welcome`'
        await msg.edit(embed=e)
        while True:
            try:
                welcome = await self.bot.wait_for('message', check=self.msgcheck, timeout=60)
                channels = welcome.channel_mentions
                break
            except asyncio.TimeoutError:
                return
        ids = [n.id for n in channels]
        id_to_use = ids[0]
        async with aiosqlite.connect(db_path) as db:
            await db.execute("UPDATE action_log_config SET welcome_channel_id = :msg WHERE guildid = :id",
                             {'msg': id_to_use, 'id': self.ctx.guild.id})
            await db.commit()
        e.set_author(name="All done! This is the channel welcome messages will be sent in: ",
                     icon_url=self.ctx.author.avatar_url)
        e.description = f'<#{id_to_use}>'
        await msg.edit(embed=e)

    async def set_welcome_msg(self):
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name="Please send what you want your welcome message to be. If it pings the person joining"
                          ", use {@user}, if it says the server name, user {servername},"
                          "if it has a channel, just do #channel-name like normal. If it has a "
                          "role mention, mention it like normal",
                     icon_url=self.ctx.author.avatar_url)
        e.description = 'For example, `Hello, {@user}, welcome to {servername}. Please say hello in #chat, and ' \
                        'mention @Moderators when you have read rules in #rules!`'
        msg = await self.ctx.send(embed=e)
        while True:
            try:
                welcomemsg = await self.bot.wait_for('message', check=self.msgcheck, timeout=60)
                message = welcomemsg.content
                break
            except asyncio.TimeoutError:
                message = ''
                break
        async with aiosqlite.connect(db_path) as db:
            await db.execute("UPDATE action_log_config SET welcome_msg = :msg WHERE guildid = :id",
                             {'msg': message, 'id': self.ctx.guild.id})
            await db.commit()
        e.set_author(name="All done! This is your message: ", icon_url=self.ctx.author.avatar_url)
        e.description = message
        await msg.edit(embed=e)

    async def set_welcome_roles(self, msg):
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name="Please send which roles (mention or name) "
                          "you would like me to give to everyone who joins the server.")
        e.description = 'Eg. `@General, Announcements`'
        await msg.edit(embed=e)
        while True:
            try:
                message = await self.bot.wait_for('message', check=self.msgcheck, timeout=60)
                roles = message.role_mentions
                if len(roles) == 0:
                    roles = []
                    for argum in message.content:
                        role = await discord.utils.get(message.guild._roles.values(), name=argum)
                        roles.append(role)
                if roles is None:
                    raise commands.BadArgument(f"Role(s) {message.content} not found")
                role_id = [n.id for n in roles]
                r = '\n'
                for role in role_id:
                    r += f'<@&{role}>\n'
                e.set_author(name="Success")
                e.description = f'Roles set: {r}'
                return await msg.edit(embed=e)
            except asyncio.TimeoutError:
                return

    async def set_leave_channel(self):
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name="Please send a channel for leaving messages to be sent in",
                     icon_url=self.ctx.author.avatar_url)
        e.description = 'Eg. `#welcome-and-goodbye`'
        msg = await self.ctx.send(embed=e)
        while True:
            try:
                welcome = await self.bot.wait_for('message', check=self.msgcheck, timeout=60)
                channels = welcome.channel_mentions
                break
            except asyncio.TimeoutError:
                return
        ids = [n.id for n in channels]
        id_to_use = ids[0]
        async with aiosqlite.connect(db_path) as db:
            await db.execute("UPDATE action_log_config SET leave_channel_id = :msg WHERE guildid = :id",
                             {'msg': id_to_use, 'id': self.ctx.guild.id})
            await db.commit()
        e.set_author(name="All done! This is the channel leaving messages will be sent in: ",
                     icon_url=self.ctx.author.avatar_url)
        e.description = f'<#{id_to_use}>'
        await msg.edit(embed=e)

    async def set_leave_msg(self):
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name="Please send what you want your leaving message to be.",
                     icon_url=self.ctx.author.avatar_url)

        e.description = "If it mentions (nick#discrim)"\
                        " the person leaving"\
                        ", use {@user}, if it says the server name, user {servername},"\
                        "if it has a channel, just do #channel-name like normal. If it has a "\
                        "role mention, mention it like normal\n\nFor example, " \
                        "`{@user} just left the amazing {servername}! What a looser...`"
        msg = await self.ctx.send(embed=e)
        while True:
            try:
                leavemsg = await self.bot.wait_for('message', check=self.msgcheck, timeout=60)
                message = leavemsg.content
                break
            except asyncio.TimeoutError:
                message = ''
                break
        async with aiosqlite.connect(db_path) as db:
            await db.execute("UPDATE action_log_config SET leave_msg = :msg WHERE guildid = :id",
                             {'msg': message, 'id': self.ctx.guild.id})
            await db.commit()
        e.set_author(name="All done! This is your message: ", icon_url=self.ctx.author.avatar_url)
        e.description = message
        await msg.edit(embed=e)

    async def welcome_message(self):
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name="You have enabled the welcome message module, so lets set that up! First, would you like a "
                          "message sent? We'll work out which channel first.",
                     icon_url=self.ctx.author.avatar_url)
        e.description = "Press the :white_check_mark: if you do, the :x: emoji if you don't. \n\n" \
                        "Available customisations: \nSet a welcome message\nAuto give a role on joining"
        msg = await self.ctx.send(embed=e)
        await self.add_reaction(msg)
        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=self.check, timeout=60)
                await msg.remove_reaction(reaction, self.ctx.author)
                if str(reaction.emoji) == '\N{WHITE HEAVY CHECK MARK}':
                    await self.set_welcome_channel(msg)
                    await self.set_welcome_msg()
                    break
                if str(reaction.emoji) == '\N{CROSS MARK}':
                    break
                if str(reaction.emoji) == '\N{WHITE QUESTION MARK ORNAMENT}':
                    shelp = await self.show_help()
                    await self.msg.remove_reaction(reaction, self.ctx.author)
                    if shelp is True:
                        await self.set_welcome_channel(msg)
                        await self.set_welcome_msg()
                        break
                    else:
                        return
            except asyncio.TimeoutError:
                return

        e.set_author(name="The second welcome message customisation is automatically adding a role when people join."
                          " ",
                     icon_url=self.ctx.author.avatar_url)
        e.description = "If you want to give a role on joining, click the :white_check_mark:, if you don't," \
                        " click the :x: emoji.\n\nRemember you can do " \
                        "`?role @user [role]` too to manually give people roles,"\
                        " or set a role that they can give themselves."
        msg = await self.ctx.send(embed=e)
        await self.add_reaction(msg)
        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=self.check, timeout=60)
                await self.msg.remove_reaction(reaction, self.ctx.author)
                if str(reaction.emoji) == '\N{WHITE HEAVY CHECK MARK}':
                    return await self.set_welcome_roles(msg)
                if str(reaction.emoji) == '\N{CROSS MARK}':
                    break
                if str(reaction.emoji) == '\N{WHITE QUESTION MARK ORNAMENT}':
                    shelp = await self.show_help()
                    if shelp is True:
                        return await self.set_welcome_roles(msg)
                    else:
                        break
            except asyncio.TimeoutError:
                return

    async def quit(self, indexs):
        remaining = len(Modules) - indexs
        print(remaining)
        for _ in range(1, remaining):
            self.modules_set += '0'
        if remaining == 0:
            e = discord.Embed(colour=discord.Colour.green())
            e.set_author(name="All done! Modules have been updated and should be in effect immediately",
                         icon_url=self.ctx.author.avatar_url)
        else:
            e = discord.Embed(colour=discord.Colour.red())
            e.set_author(name="You took too long! I timed out and set the remaining modules to false",
                         icon_url=self.ctx.author.avatar_url)
        await self.ctx.send(embed=e)
        async with aiosqlite.connect(db_path) as db:
            await db.execute("UPDATE action_log_config SET config = :modules WHERE guildid = :id",
                             {'modules': self.modules_set, 'id': self.ctx.guild.id})
            await db.commit()
        if self.enabled is None:
            return
        await self.choose_actionlog_channel()
        if 'welcome_message' in self.enabled:
            await self.welcome_message()
        if 'leave_message' in self.enabled:
            await self.set_leave_channel()
            await self.set_leave_msg()
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name="All done! For real this time.",
                     icon_url=self.ctx.author.avatar_url)
        e.title = 'Some handy actionlog commands: '
        e.add_field(name="actionlog",
                    value="Get enabled and disabled module list, useful for individually setting modules",
                    inline=False)
        e.add_field(name="actionlog edit [module_name]",
                    value="Where module name is in the list found using `actionlog`. Edit a module directly"
                          ", without having do set them all",
                    inline=False)
        e.add_field(name="actionlog channel [#new channel]",
                    value="Change the actionlog channel",
                    inline=False)
        e.add_field(name="actionlog disable",
                    value="All your settings and welcome/leave messages will be saved, however the whole module"
                          " will be turned off. Use `actionlog enable` at any time to reenable it with previous "
                          "settings.",
                    inline=False)
        e.add_field(name="actionlog enable",
                    value="Turn on action log if it was previously turned off. "
                          "All previously set settings will remain.",
                    inline=False)
        await self.ctx.send(embed=e)
        return

    async def show_help(self):
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name="Lost? Too complicated? I'll try to explain it slowly and carefully.",
                     icon_url=self.ctx.author.avatar_url)
        e.add_field(name="What is the module thingo's?",
                    value="The bot will tell you a module that can be enabled."
                          " This module will tell you in a channel of your"
                          " choosing when that thing happens (ie. someone joins server"
                          " or edits a message). ",
                    inline=False)
        e.add_field(name="What do the reactions do?",
                    value="The reactions tell me (the bot) what you want to do. "
                          "If you want to enable the module (ie. tell you when someone joins etc.),"
                          " then press the :white_check_mark: emoji. If you don't want the module, "
                          "press the :x: emoji. I will then enable or disable in the bot. Green for Yes,"
                          " Red for No.",
                    inline=False)
        e.add_field(name="How do I set a custom welcome or leave message, or give roles on join?",
                    value="Once the relevant module is enabled, you can use the command `actionlog customise"
                          " [module name]` where I will then ask you what you want to customise.",
                    inline=False)
        e.set_footer(text="Press the green tick to go back to the module you got stuck on.")
        await self.msg.edit(embed=e)
        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=self.check, timeout=5)
                await self.msg.remove_reaction(reaction, self.ctx.author)
                if str(reaction.emoji) == '\N{WHITE HEAVY CHECK MARK}':
                    return True
                else:
                    continue
            except asyncio.TimeoutError:
                return False

    async def next_module(self, indexs):
        module = Modules[indexs]
        toggle = self.config.action_log[indexs]
        e = discord.Embed()
        if toggle == '1':
            e.description = 'Module currently enabled'
            e.colour = discord.Colour.green()
        if toggle == '0':
            e.description = 'Module currently disabled'
            e.colour = discord.Colour.red()
        e.set_author(name=module, icon_url=self.ctx.author.avatar_url)
        e.set_footer(text="React with tick if you want it enabled, "
                          "cross for disabled, question mark for help")
        edit = await self.msg.edit(embed=e)

    async def modules_config(self):
        for indexs in (range(len(Modules))):
            await self.next_module(indexs)
            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', check=self.check, timeout=60)
                    await self.msg.remove_reaction(reaction, self.ctx.author)
                    if str(reaction.emoji) == '\N{WHITE HEAVY CHECK MARK}':
                        self.modules_set += '1'
                        self.enabled.append(Modules[indexs])
                        break
                    if str(reaction.emoji) == '\N{CROSS MARK}':
                        self.modules_set += '0'
                        break
                    if str(reaction.emoji) == '\N{WHITE QUESTION MARK ORNAMENT}':
                        shelp = await self.show_help()
                        if shelp is True:
                            await self.next_module(indexs)
                            break
                        else:
                            return
                except asyncio.TimeoutError:
                    break
        return

    async def indiv_module_config(self, module_name):
        if module_name not in Modules:
            raise commands.BadArgument(f"Couldn't find module with name {module_name}.")
        indexs = Modules.index(module_name)
        print(str(self.prev_set))
        l = list(self.prev_set)
        new = ''
        await self.add_reaction(self.msg)
        await self.next_module(indexs)
        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=self.check, timeout=60)
                await self.msg.remove_reaction(reaction, self.ctx.author)
                if str(reaction.emoji) == '\N{WHITE HEAVY CHECK MARK}':
                    l[indexs] = 1
                    new = ''.join(str(e) for e in l)
                    self.enabled.append(Modules[indexs])
                    if module_name == 'welcome_message':
                        await self.welcome_message()
                    if module_name == 'leave_message':
                        await self.set_leave_channel()
                        await self.set_leave_msg()
                    break
                if str(reaction.emoji) == '\N{CROSS MARK}':
                    l[indexs] = 0
                    new = ''.join(str(e) for e in l)
                    break
            except asyncio.TimeoutError:
                break
        async with aiosqlite.connect(db_path) as db:
            await db.execute("UPDATE action_log_config SET config = :config WHERE guildid = :id",
                             {'id': self.ctx.guild.id, 'config': new})
            await db.commit()
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name="All done and saved",
                     icon_url=self.ctx.author.avatar_url)
        await self.msg.edit(embed=e)

    def check(self, reaction, user):
        return user == self.ctx.author and str(reaction.emoji) in ['\N{WHITE HEAVY CHECK MARK}', '\N{CROSS MARK}',
                                                                   '\N{WHITE QUESTION MARK ORNAMENT}']

    def msgcheck(self, user):
        print(user.author.id)
        if (user is None) or (user.author.id != self.ctx.author.id):
            return False
        else:
            return True


class SendLogs:
    def __init__(self, bot):
        self.bot = bot

    async def send_log(self, e, channel, action, userid: int = None, reason: str = None):
        if userid:
            user = await self.get_user(userid)
            e.set_author(name=f"{user.display_name}#{user.discriminator}",
                         icon_url=user.avatar_url)
        if reason:
            print(reason)
            e.add_field(name=action, value=reason)
        else:
            e.description = action
        e.set_footer(text='\u200b')
        e.timestamp = datetime.datetime.utcnow()
        await channel.send(embed=e)

    async def get_channel(self, channelid):
        return self.bot.get_channel(id=channelid)

    async def get_message(self, messageid, channelid):
        try:
            o = discord.Object(id=messageid + 1)
            # Use history rather than get_message due to
            #         poor ratelimit (50/1s vs 1/1s)
            msg = await self.get_channel(channelid).history(limit=1, before=o).next()
            if msg.id != messageid:
                return None
            return msg

        except Exception:
            return None

    async def get_user(self, userid):
        return self.bot.get_user(id=userid)

class ActionLogImplementation:
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def record(guild_id):
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT * FROM action_log_config WHERE guildid = :id",
                                 {'id': guild_id})
            dump = await c.fetchall()
        return dump

    @staticmethod
    async def watchrecord(guild_id, userid):
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT * FROM watch_log_config WHERE guildid = :gid AND userid = :id",
                                 {'gid': guild_id, 'id': userid})
            return await c.fetchall()

    async def enabled(self, guild_id):
        record = await self.record(guild_id)
        al = await ActionLog.from_db(record, self.bot)
        return al.lookup_enabled_action_log

    async def disabled(self, guild_id):
        record = await self.record(guild_id)
        al = await ActionLog.from_db(record, self.bot)
        return al.lookup_disabled_action_log

    async def action_log_channel(self, guild_id):
        record = await self.record(guild_id)
        al = await ActionLog.from_db(record, self.bot)
        return al.action_log_channel

    async def wlenabled(self, guild_id, userid):
        record = await self.watchrecord(guild_id, userid)
        wl = await WatchLog.from_db(record, self.bot)
        return wl.lookup_enabled_watch_log

    async def wldisabled(self, guild_id, userid):
        record = await self.watchrecord(guild_id, userid)
        wl = await WatchLog.from_db(record, self.bot)
        return wl.lookup_disabled_watch_log

    async def watchlogchannel(self, guild_id, user_id):
        record = await self.watchrecord(guild_id, user_id)
        wl = await WatchLog.from_db(record, self.bot)
        return wl.watch_log_channel

    def get_channel(self, channelid):
        return self.bot.get_channel(channelid)

    async def get_message(self, messageid, channel):
        try:
            o = discord.Object(id=messageid)
            # Use history rather than get_message due to
            #         poor ratelimit (50/1s vs 1/1s)

            msg = await channel.get_message(id=messageid)
            print(msg.id)
            if msg.id != messageid:
                return None
            return msg

        except Exception as e:
            print(e)
            return None

    async def get_user(self, userid):
        return self.bot.get_user(id=userid)

    e = discord.Embed(colour=discord.Colour.red())
    e.title = 'Level 1 - Moderator Commands'

    async def on_raw_bulk_message_delete(self, payload=discord.RawBulkMessageDeleteEvent):
        enabled = await self.enabled(payload.guild_id)
        if 'on_mass_message_delete' in enabled:
            count = len(payload.message_ids)
            channel_id = await self.action_log_channel(payload.guild_id)
            await SendLogs(self.bot).send_log(e=self.e, channel=channel_id,
                                              action=f'Mass Message Delete: {count} messages',
                                              )
    async def on_member_join(self, member):
        enabled = await self.enabled(member.guild.id)
        wlenabled = await self.wlenabled(member.guild.id, member.id)

        async def send(channel_id):
            roles = '\n'.join(n.mention for n in member.roles)
            self.e.set_thumbnail(url=member.avatar_url)
            self.e.colour = member.colour
            extra = ''
            async for log in member.guild.audit_logs(action=discord.AuditLogAction.kick):
                counter = 0
                if log.target == self.bot.get_user(id=member.id):
                    if counter == 0:
                        extra += "Previously kicked by:\n "
                        counter += 1
                    extra += f'{log.user} for reason: {log.reason} ({log.created_at})\n'
            async for log in member.guild.audit_logs(action=discord.AuditLogAction.ban):
                counter = 0
                if log.target == self.bot.get_user(id=member.id):
                    if counter == 0:
                        extra += "Previously banned by:\n "
                        counter += 1
                    extra += f'{log.user} for reason: {log.reason} ({log.created_at})\n'
            async for log in member.guild.audit_logs(action=discord.AuditLogAction.unban):
                counter = 0
                if log.target == self.bot.get_user(id=member.id):
                    if counter == 0:
                        extra += "Previously unbanned by:\n "
                        counter += 1
                    extra += f'{log.user} for reason: {log.reason} ({log.created_at})\n'

            await SendLogs(self.bot).send_log(e=self.e, channel=channel_id,
                                              action=f"Member Joined - {member.display_name}#{member.discriminator}",
                                              reason=f"Roles: {roles}\n"
                                                     f"Bot: {member.bot}\n"
                                                     f"Account created at: \n{member.created_at}"
                                                     f"\n{extra}",
                                              userid=member.id)

        if 'on_member_join' in enabled:
            channel_id = await self.action_log_channel(member.guild.id)
            await send(channel_id)

        if 'on_member_join' in wlenabled:
            channel_id = await self.watchlogchannel(member.guild.id, member.id)
            await send(channel_id)

    async def on_member_leave(self, member):
        enabled = await self.enabled(member.guild.id)
        wlenabled = await self.wlenabled(member.guild.id, member.id)

        async def send(channel_id, left: bool = None, kicks: bool = None, watch_kicks: bool = None):
            extra = ''
            async for log in member.guild.audit_logs(action=discord.AuditLogAction.kick):
                counter = 0
                if log.target == self.bot.get_user(id=member.id):
                    if counter == 0:
                        extra += "Previously kicked by:\n "
                        counter += 1
                    extra += f'{log.user} for reason: {log.reason} ({log.created_at})\n'
            async for log in member.guild.audit_logs(action=discord.AuditLogAction.ban):
                counter = 0
                if log.target == self.bot.get_user(id=member.id):
                    if counter == 0:
                        extra += "Previously banned by:\n "
                        counter += 1
                    extra += f'{log.user} for reason: {log.reason} ({log.created_at})\n'
            async for log in member.guild.audit_logs(action=discord.AuditLogAction.unban):
                counter = 0
                if log.target == self.bot.get_user(id=member.id):
                    if counter == 0:
                        extra += "Previously unbanned by:\n "
                        counter += 1
                    extra += f'{log.user} for reason: {log.reason} ({log.created_at})\n'
            if kicks:
                async for log in member.guild.audit_logs(action=discord.AuditLogAction.kick):
                    if log.action == self.bot.get_user(id=member.id):
                        self.e.set_thumbnail(url=member.avatar_url)
                        await SendLogs(self.bot).send_log(e=self.e, channel=channel_id,
                                                          action=f"Member Kicked - {member.display_name}#{member.discriminator}",
                                                          reason=f"Responsible Moderator: {log.user.mention}"
                                                                 f"Reason: {log.reason}"
                                                                 f"Bot: {member.bot}\n"
                                                                 f"Account created at: \n{member.created_at}"
                                                                 f"\n{extra}",
                                                          userid=member.id)
                        return
            if left:
                self.e.set_thumbnail(url=member.avatar_url)
                await SendLogs(self.bot).send_log(e=self.e, channel=channel_id,
                                                  action=f"Member Left - {member.display_name}#{member.discriminator}",
                                                  reason=f"Bot: {member.bot}\n"
                                                         f"Account created at: \n{member.created_at}"
                                                         f"\n{extra}",
                                                  userid=member.id)
                return
            if watch_kicks:
                async for log in member.guild.audit_logs(action=discord.AuditLogAction.kick,
                                                         user=member):
                    if log.action == self.bot.get_user(id=member.id):
                        self.e.set_thumbnail(url=member.avatar_url)
                        await SendLogs(self.bot).send_log(e=self.e, channel=channel_id,
                                                          action=f"Kicked Member "
                                                                 f"{member.display_name}#{member.discriminator}",
                                                          reason=f"Reason: {log.reason}",
                                                          userid=member.id)
                        return

        if 'on_member_leave' in enabled:
            channel_id = await self.action_log_channel(member.guild.id)
            await send(channel_id, left=True)

        if 'on_member_kicked' in enabled:
            channel_id = await self.action_log_channel(member.guild.id)
            await send(channel_id, kicks=True)

        if 'on_moderator_commands' in enabled:
            channel_id = await self.action_log_channel(member.guild.id)
            await send(channel_id, watch_kicks=True)

        if 'on_member_leave' in wlenabled:
            channel_id = await self.watchlogchannel(member.guild.id, member.id)
            await send(channel_id, left=True)

        if 'on_member_kicked' in wlenabled:
            channel_id = await self.watchlogchannel(member.guild.id, member.id)
            await send(channel_id, kicks=True)

        if 'on_moderator_commands' in wlenabled:
            channel_id = await self.watchlogchannel(member.guild.id, member.id)
            await send(channel_id, watch_kicks=True)

    # async def on_member_update(self, before, after):
    #     # print(before.guild.name, before.guild.id)
    #     enabled = await self.enabled(after.guild.id)
    #     if 'on_nickname_change' in enabled:
    #         if before.nick != after.nick:
    #             channel_id = await self.action_log_channel(before.guild.id)
    #             async for log in after.guild.audit_logs(limit=1):
    #                 try:
    #                     if log.user != after:
    #                         await SendLogs(self.bot).send_log(e=self.e, channel=channel_id,
    #                                                           action=f"Update Nickname",
    #                                                           reason=f"Before: "
    #                                                                  f"{before.display_name}#{before.discriminator}\n"
    #                                                                  f"After: "
    #                                                                  f"{after.display_name}#{after.discriminator}\n"
    #                                                                  f"Moderator: "
    #                                                                  f"{log.user.display_name}#{log.user.discriminator}",
    #                                                           )
    #                     else:
    #                         await SendLogs(self.bot).send_log(e=self.e, channel=channel_id,
    #                                                           action=f"Nickname Change: ",
    #                                                           reason=f"Before: "
    #                                                                  f"{before.display_name}#{before.discriminator}\n"
    #                                                                  f"After: "
    #                                                                  f"{after.display_name}#{after.discriminator}",
    #                                                           userid=after.id)
    #                 except AttributeError:
    #                     pass
    #
    #     if 'on_avatar_change' in enabled:
    #         if before.avatar_url != after.avatar_url:
    #             channel_id = await self.action_log_channel(before.guild.id)
    #             self.e.set_thumbnail(url=after.avatar_url)
    #             self.e.set_footer(text="This was the previous avatar",
    #                               icon_url=before.avatar_url)
    #             await SendLogs(self.bot).send_log(e=self.e, channel=channel_id,
    #                                               action=f"Avatar Change: "
    #                                                      f"{after.display_name}#{after.discriminator}",
    #                                               userid=after.id)
    #     if ('on_role_given', 'on_role_removed', 'on_moderator_commands') in enabled:
    #         if before.roles != after.roles:
    #             channel_id = await self.action_log_channel(before.guild.id)
    #             async for log in after.guild.audit_logs(limit=1):
    #                 try:
    #                     if log.user != after:
    #                         async def mod_roles(give_remove, from_to):
    #                             roles = '\n'.join(list(n.mention for n in log.roles))
    #                             await SendLogs(self.bot).send_log(e=self.e, channel=channel_id,
    #                                                               action=f"Moderator Change: {give_remove} "
    #                                                                      f"Role {from_to} "
    #                                                                      f"{after.display_name}#{after.discriminator}",
    #                                                               reason=f"Roles: {roles}"
    #                                                                      f"Moderator: "
    #                                                                      f"{log.user.display_name}#"
    #                                                                      f"{log.user.discriminator}"
    #                                                               )
    #                         if log.roles in after.roles:
    #                             if ('on_role_given', 'on_moderator_commands') in enabled:
    #                                 await mod_roles('Give', 'To')
    #                         else:
    #                             if ('on_role_removed', 'on_moderator_commands') in enabled:
    #                                 await mod_roles('Removed', 'From')
    #
    #                     else:
    #                         async def self_roles(give_remove, to_from):
    #                             roles = '\n'.join(list(n.mention for n in log.roles))
    #                             await SendLogs(self.bot).send_log(e=self.e, channel=channel_id,
    #                                                               action=f"Role {give_remove} {to_from} Self",
    #                                                               reason=f"Roles: {roles}",
    #                                                               userid=after.id
    #                                                               )
    #                         if log.roles in after.roles:
    #                             if 'on_role_given' in enabled:
    #                                 await self_roles('Given', 'To')
    #                         else:
    #                             if 'on_role_removed' in enabled:
    #                                 await self_roles('Removed', 'From')
    #                 except AttributeError:
    #                     pass

    async def on_guild_channel_create(self, channel):
        enabled = await self.enabled(channel.guild.id)
        async for log in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            user = log.user
        wlenabled = await self.wlenabled(channel.guild.id, user.id)
        self.e.clear_fields()

        async def send_logs(channel_id):
            roles = '\n'.join(list(n.mention for n in channel.changed_roles))
            await SendLogs(self.bot).send_log(e=self.e, channel=channel_id,
                                              action=f"Channel created - {channel.name}",
                                              reason=f"Category: {channel.category}\n"
                                                     f"Members: {len(channel.members)}\n"
                                                     f"Changed roles: \n{roles}",
                                              userid=user.id)
        if 'on_channel_created' in enabled:
            channel_id = await self.action_log_channel(channel.guild.id)
            await send_logs(channel_id)

        self.e.clear_fields()
        if 'on_channel_created' in wlenabled:
            channel_id = await self.watchlogchannel(channel.guild.id, user.id)
            await send_logs(channel_id)

    async def on_guild_channel_update(self, before, after):
        async for log in after.guild.audit_logs(limit=1):
            user = log.user
            print(log.user, log.action)
        async for log in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.overwrite_update):
            user = log.user
            print(log.user)

        enabled = await self.enabled(before.guild.id)
        wlenabled = await self.wlenabled(after.guild.id, user.id)
        self.e.clear_fields()
        if 'on_channel_edit' in enabled:
            changes = ''
            if before.name != after.name:
                changes += f'Old Name: {before.name}\n' \
                           f'New Name: {after.name}\n'
            if before.topic != after.topic:
                changes += f'Old Topic: {before.topic}\n' \
                           f'New Topic: {after.topic}\n'
            if before.is_nsfw() != after.is_nsfw():
                changes += f"NSFW Before: {before.is_nsfw()}\n" \
                           f"NSFW After: {after.is_nsfw()}\n"
            if before.overwrites != after.overwrites:
                for perms in after.overwrites:
                    if perms not in before.overwrites:
                        print(perms[1].pair())
                        # perm = '\n'.join(perms[1])
                        changes += f"Changed permission for {perms[0].mention}:\n"

            async def send_logs(channel_id):
                await SendLogs(self.bot).send_log(e=self.e, channel=channel_id,
                                                  action=f"Channel Modified - {before.name}",
                                                  reason=f"Category: {before.category}\n"
                                                         f"Members: {len(before.members)}\n"
                                                         f"{changes}",
                                                  userid=user.id)

            if 'on_channel_edit' in enabled:
                channel_id = await self.action_log_channel(after.guild.id)
                await send_logs(channel_id)

            self.e.clear_fields()
            if 'on_channel_edit' in wlenabled:
                channel_id = await self.watchlogchannel(after.guild.id, user.id)
                await send_logs(channel_id)

    async def on_guild_channel_delete(self, channel):
        enabled = await self.enabled(channel.guild.id)
        if 'on_channel_removed' in enabled:
            async for log in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                user = log.user
            enabled = await self.enabled(channel.guild.id)
            wlenabled = await self.wlenabled(channel.guild.id, user.id)
            self.e.clear_fields()
            async def send_logs(channel_id):
                await SendLogs(self.bot).send_log(e=self.e, channel=channel_id,
                                                  action=f"Moderator Command: Channel Deleted - {channel.name}",
                                                  reason=f"Category: {channel.category}\n"
                                                         f"Members: {len(channel.members)}\n"
                                                         f"Moderator: {user.display_name}#{user.discriminator}",
                                                  userid=user.id)

            if 'on_channel_removed' in enabled:
                channel_id = await self.action_log_channel(channel.guild.id)
                await send_logs(channel_id)

            self.e.clear_fields()
            if 'on_channel_removed' in wlenabled:
                channel_id = await self.watchlogchannel(channel.guild.id, user.id)
                await send_logs(channel_id)

    # async def on_guild_join(self, guild):
    #     enabled = self.enabled(guild.id)





class Tools:
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    @commands.group(name='actionlog', invoke_without_command=True)
    async def _actionlog(self, ctx):
        """Configure the action log for a guild.
        Invoke without a command and get the enabled and disabled modules for a guild
        PARAMETERS: None
        EXAMPLE: `actionlog`
        RESULT: Gives enabled and disabled modules, and log channel"""

        guildid = ctx.guild.id
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT * FROM action_log_config WHERE guildid = :id",
                                 {'id': guildid})
            dump = await c.fetchall()

        config = await ActionLog.from_db(dump, self.bot)
        strenabled = ''
        strdisabled = ''
        for enabled in config.lookup_enabled_action_log:
            strenabled += f'{enabled}\n'
        for disabled in config.lookup_disabled_action_log:
            strdisabled += f'{disabled}\n'
        e = discord.Embed(colour=discord.Colour.blue())
        e.set_author(name="ActionLog modules", icon_url=ctx.author.avatar_url)
        e.add_field(name="Enabled modules:", value=strenabled or '\u200b', inline=False)
        e.add_field(name="Disabled modules:", value=strdisabled or '\u200b', inline=False)
        e.add_field(name="Action Log Channel:", value=f'<#{config.action_log_channel.id}>' or '\u200b', inline=False)
        await ctx.send(embed=e)

    @_actionlog.command()
    async def config(self, ctx):
        """Go through all setup features of the action log.
        I will walk you through every module where you can choose to enable or disable through reaction emojis.
        Reply when I tell you (without a command) to set the welcome and leaving messages, if applicable.
        This may take 5 minutes to complete.
        PARAMETERS: None
        EXAMPLE: `actionlog config`
        RESULT: Walk through the interactive actionlog configuration tool"""

        guildid = ctx.guild.id

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT * FROM action_log_config WHERE guildid = :id",
                                 {'id': guildid})
            dump = await c.fetchall()

        config = await ActionLog.from_db(dump, self.bot)

        strenabled = ''

        strdisabled = ''

        for enabled in config.lookup_action_log[0]:
            strenabled += f'{enabled}\n'

        for disabled in config.lookup_action_log[1]:
            strdisabled += f'{disabled}\n'

        e = discord.Embed(colour=discord.Colour.blue())
        e.set_author(name="Welcome to the interactive action log configuration.", icon_url=ctx.author.avatar_url)
        e.title = "It's pretty simple; If you want a module, add the green tick emoji. If you don't want it," \
                  " add the red X emoji. If you get stuck or need help, press the questionmark emoji"
        e.description = 'These are your current enabled/disabled modules. If you want to edit these individually,' \
                        ' use the `actionlog add [module name]` or `actionlog remove [module name]` commands. ' \
                        '\nPress the green tick to start!'
        if len(strenabled) == 0:
            strenabled = '\u200b'
        if len(strdisabled) == 0:
            strdisabled = '\u200b'
        e.add_field(name="Enabled modules:", value=strenabled, inline=False)
        e.add_field(name="Disabled modules:", value=strdisabled, inline=False)
        msg = await ctx.send(embed=e)
        alc = ActionLogConfig(self.bot, msg, ctx, dump, config)
        await alc.add_reaction(msg)
        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=alc.check, timeout=60)
                await msg.remove_reaction(reaction, ctx.author)
                if str(reaction.emoji) == '\N{WHITE HEAVY CHECK MARK}':
                    await alc.modules_config()
                    return await alc.quit(len(Modules))
                if str(reaction.emoji) == '\N{CROSS MARK}':
                    await msg.delete()
                if str(reaction.emoji) == '\N{WHITE QUESTION MARK ORNAMENT}':
                    shelp = await alc.show_help()
                    if shelp is True:
                        await alc.modules_config()
                        await alc.modules_config()
                        return await alc.quit(len(Modules))
                    else:
                        return await alc.quit(0)
            except asyncio.TimeoutError:
                return await alc.quit(0)

    @_actionlog.command()
    async def edit(self, ctx, module_name: str):
        """Edit an action log module individually without going through entire configuration
        PARAMETERS: [module_name] - find a list of these with `actionlog` command
        EXAMPLE: `actionlog edit welcome_message`
        RESULT: Get the interactive configuration for the welcome message"""
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT * FROM action_log_config WHERE guildid = :id",
                                 {'id': ctx.guild.id})
            dump = await c.fetchall()
        msg = await ctx.send('\u200b')
        config = await ActionLog.from_db(dump, self.bot)
        alc = ActionLogConfig(self.bot, msg, ctx, dump, config)
        await alc.indiv_module_config(module_name)

    @_actionlog.command()
    async def channel(self, ctx, new_channel: discord.TextChannel):
        """Reassign or change the channel the actionlog logs to
        PARAMETERS: #[new-channel] - mention the new channel
        EXAMPLE: `actionlog channel #maths-bot-log`
        RESULT: Set the actionlog to now report to #maths-bot-log"""
        async with aiosqlite.connect(db_path) as db:
            await db.execute("UPDATE action_log_config SET action_log_id = :channelid WHERE guildid = :guildid",
                             {'channelid': new_channel.id, 'guildid': self.ctx.guild.id})
            await db.commit()
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name=f"ActionLog Channel has been changed to: ",
                     icon_url=self.ctx.author.avatar_url)
        e.description = f"<#{new_channel.id}>. If you want to change that, rerun the command."
        await ctx.send(embed=e)

    @_actionlog.command()
    async def enable(self, ctx):
        """Enable the actionlog as a whole. It will store and reuse saved module info (if applicable)
        PARAMETERS: None
        EXAMPLE: `actionlog enable`
        RESULT: It will enable the action log. If you have not previously set it up you need to go through `actionlog config`."""
        async with aiosqlite.connect(db_path) as db:
            await db.execute("UPDATE guildinfo SET actionlog = 1 WHERE guildid = :id",
                             {'id': ctx.guild.id})
            await db.commit()
        e = discord.Embed(colour=discord.Colour.green())
        e.description = "Action Log enabled. Get enabled modules and channel info with `actionlog`"
        await ctx.send(embed=e)

    @_actionlog.command()
    async def disable(self, ctx):
        """Disable the actionlog as a whole. No logging will occur while this is disabled.
        PARAMETERS: None
        EXAMPLE: `actionlog disable`
        RESULT: It will disable the actionlog as a whole. All saved module info will be stored until you next enable."""
        async with aiosqlite.connect(db_path) as db:
            await db.execute("UPDATE guildinfo SET actionlog = 0 WHERE guildid = :id",
                             {'id': ctx.guild.id})
            await db.commit()
        e = discord.Embed(colour=discord.Colour.green())
        e.description = "Action Log disabled. Saved modules and welcome messages have been saved and ready next time " \
                        "you enable actionlog"
        await ctx.send(embed=e)

    def levelinfo(self, level):
        if level == '1':
            return f'Moderator Commands (kick, (un)ban, channel/role ' \
                 f'add/remove/update, server changes, any MathsBot moderation commands) Only'
        if level == '2':
            return f'Moderator Commands, and any manage_message commands (delete/pin/unpin msg, remove reactions)'
        if level == '3':
            return f'Moderator Commands, manage_message commands, and personal message edits and deletes'
        if level == '4':
            return 'Moderator Commands, manage_message commands, ' \
                   'personal edit/deletes and all messages and reaction adds'

    @commands.group(name='watch', invoke_without_command=True)
    async def _watch(self, ctx):
        e = discord.Embed(colour=discord.Colour.green())
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT * FROM watch_log_config WHERE guildid = :gid",
                                 {'gid': ctx.guild.id})
            dump = await c.fetchall()
        users = []
        channels = []
        level = []
        for indiv in dump:
            users.append(indiv[0])
            channels.append(indiv[1])
            level.append(indiv[3])
        if len(dump) != 0:
            e.add_field(name="User",
                        value='\n'.join(f'Level {self.levelinfo(level)}: <@{users}>' for (level, users) in enumerate(dump)))
            e.add_field(name="Channel",
                        value='\n'.join(f'<#{channels[_]}>' for _ in range(0, len(channels))),
                        inline=True)
        e.set_author(name=f"Currently Watching {len(users)} users")

        e.add_field(name="Levels Info",
                    value='\u200b')
        e.add_field(name="Level 1", value=self.levelinfo('1'), inline=False)
        e.add_field(name="Level 2", value=self.levelinfo('2'), inline=False)
        e.add_field(name="Level 3", value=self.levelinfo('3'), inline=False)
        e.add_field(name="Level 4", value=self.levelinfo('4'), inline=False)
        await ctx.send(embed=e)

    @_watch.command(name="add")
    async def _add(self, ctx, user: discord.Member, channel: discord.TextChannel, level: str):
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT * FROM watch_log_config WHERE guildid = :gid AND userid = :id",
                                 {'id': user.id, 'gid': ctx.guild.id})
            dump = await c.fetchall()
        if len(dump) != 0:
            async with aiosqlite.connect(db_path) as db:
                await db.execute("UPDATE watch_log_config SET channel = :channel, level = :level WHERE "
                                 "guildid = :gid AND userid = :id",
                                 {'channel': channel.id, 'level': level,
                                  'gid': ctx.guild.id, 'id': user.id})
                await db.commit()
            e = discord.Embed(colour=discord.Colour.blue())
            e.description = f"{user.display_name}#{user.discriminator} is already being watched. "\
                            f"\n\nI have updated their settings so they report in {channel.mention} "\
                            f"with level {level}."
            return await ctx.send(embed=e)
        async with aiosqlite.connect(db_path) as db:
            await db.execute("INSERT INTO watch_log_config VALUES (:id, :cid, :gid, :level)",
                             {'id': user.id, 'cid': channel.id, 'gid': ctx.guild.id,
                              'level': level})
            await db.commit()
        e = discord.Embed(colour=discord.Colour.green())
        e.description = f"Added {user.display_name}#{user.discriminator} to {ctx.guild.name}'s" \
                        f" watch list, reporting in {channel.mention} with level {level}."
        e.add_field(name=f"Level {level} Info: ",
                    value=self.levelinfo(level))
        await ctx.send(embed=e)

    @_watch.command(name="delete")
    async def _delete(self, ctx, user: discord.Member):
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT * FROM watch_log_config WHERE guildid = :gid AND userid = :id",
                                 {'id': user.id, 'gid': ctx.guild.id})
            dump = await c.fetchall()
        if len(dump) == 0:
            e = discord.Embed(colour=discord.Colour.blue())
            e.description = f"{user.display_name}#{user.discriminator} has not been added to the watch list.\n\n"\
                            f"To add them, use `watch add [user] [#channel] [level]`."
            return await ctx.send(embed=e)
        async with aiosqlite.connect(db_path) as db:
            await db.execute("DELETE FROM watch_log_config WHERE userid = :id AND guildid = :id",
                             {'id': user.id, 'guildid': ctx.guild.id})
            await db.commit()
        await ctx.send('\N{THUMBS UP SIGN}')

    # when you call function that returns one of these errors send it as follows
    async def __error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(error)
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if isinstance(original, discord.Forbidden):
                await ctx.send('I do not have permission to execute this action.')
            elif isinstance(original, discord.NotFound):
                await ctx.send(f'This entity does not exist: {original.text}')
            elif isinstance(original, discord.HTTPException):
                await ctx.send('Somehow, an unexpected error occurred. Try again later?')

def setup(bot):
    bot.add_cog(Tools(bot))
    bot.add_cog(ActionLogImplementation(bot))

