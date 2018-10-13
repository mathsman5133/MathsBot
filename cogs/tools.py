import discord
from discord.ext import commands
import asyncio
from cogs.utils.help import HelpPaginator
from contextlib import redirect_stdout
import io
import textwrap
import traceback
import webcolors
import aiosqlite
import enum
import re
import os

db_path = os.path.join(os.getcwd(), 'cogs', 'utils', 'database.db')

# db_path = 'C:/Users/User/py/mathsbot/cogs/utils/database.db'
# action log in progress


class _ActionLog(enum.Enum):
    on = 1
    off = 0

    def __str__(self):

        return self.name


# check if valid id AND if your roles are higher than the person you're trying to affect -
# to do anything to them you need a more elevated role


class MemberId(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            # try to convert using normal discord.Member converter
            m = await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            # otherwise try to just get id
            try:
                return int(argument, base=10)
            # if that fails its not an id
            except ValueError:
                raise commands.BadArgument(f"{argument} is not a valid member or user id.")

        else:
            # if author it bot owner, guild owner or has roles higher than person they're affecting
            can_execute = ctx.author.id == ctx.bot.owner_id or \
                          ctx.author == ctx.guild.owner or \
                          ctx.author.top_rol > m.top_role

            if not can_execute:
                raise commands.BadArgument("You cant do this your "
                                           "top role is less than the person you're trying to affect")

            return m.id

# if its ban command and they're already kicked then we cant ping them or user member : discord.Member as they're
# not in server anymore or it's cache


class BannedMember(commands.Converter):
    async def convert(self, ctx, argument):
        ban_list = await ctx.guild.bans()
        try:
            member_id = int(argument, base=10)
            member = discord.utils.find(lambda u: u.user == member_id, ban_list)
        except ValueError:
            raise commands.BadArgument(f'{argument} is not a valid user id')
        return member


# override default reason for kick/ban etc
class ActionReason(commands.Converter):
    async def convert(self, ctx, argument):
        reason = f'{ctx.author} - ({ctx.author.id}), Reason: {argument}'
        # make sure does not exceed 512 char limit
        if len(reason) > 512:
            raise commands.BadArgument("Reason is too long")
        return reason


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


ActionModules = ['welcome_message',
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
                 'on_server_edit',
                 'on_moderator_commands',
                 'member_message_stalking'
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
        lookup = ActionModules
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
        lookup = ActionModules
        disabled = []
        for index, item in enumerate(self.action_log):
            if item == '0':
                disabled.append(lookup[index])
        return disabled


class Prefix(commands.Converter):
    async def convert(self, ctx, argument):
        # disallows prefixes pinging bot as they are reserved
        user_id = ctx.bot.user.id
        if argument.startswith((f'<@{user_id}', f'<@!{user_id}>')):
            raise commands.BadArgument('This is a reserved prefix already in use!')
        return argument

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
        e.set_author(name="Please send which roles you would like me to give to everyone who joins the server.")
        e.description = 'Eg. `@General @Announcements`'
        await msg.edit(embed=e)
        while True:
            try:
                message = await self.bot.wait_for('message', check=self.msgcheck, timeout=60)
                roles = message.role_mentions
                # argument = message.content
                # match = re.compile(r'([0-9]{15,21})$').match(argument) or re.match(r'<@&([0-9]+)>$', argument)
                # if match:
                #     result = await msg.guild.get_role(int(match.group(1)))
                # else:
                #     result = await discord.utils.get(guild._roles.values(), name=argument)
                #
                # if result is None:
                #     raise commands.BadArgument('Role "{}" not found.'.format(argument))
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
        remaining = len(ActionModules) - indexs
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
        module = ActionModules[indexs]
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
        for indexs in (range(len(ActionModules))):
            await self.next_module(indexs)
            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', check=self.check, timeout=60)
                    await self.msg.remove_reaction(reaction, self.ctx.author)
                    if str(reaction.emoji) == '\N{WHITE HEAVY CHECK MARK}':
                        self.modules_set += '1'
                        self.enabled.append(ActionModules[indexs])
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
        if module_name not in ActionModules:
            raise commands.BadArgument(f"Couldn't find module with name {module_name}.")
        indexs = ActionModules.index(module_name)
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
                    self.enabled.append(ActionModules[indexs])
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

    async def on_message(self, message):
        if message.author.bot:
            return
        enabled = await self.enabled(message.guild.id)
        if 'member_message_stalking' in enabled:
            e = discord.Embed(colour=message.author.colour)
            e.set_author(name=f'Watching {message.author.display_name}#{message.author.discriminator}',
                         icon_url=message.author.avatar_url)
            e.description = f'<@{message.author.id}>' \
                            f' sent a message in <#{message.channel.id}>'
            e.add_field(name="Contents:", value=message.content or 'None', inline=False)
            e.add_field(name="Users mentioned:",
                        value='\n'.join([n.mention for n in message.mentions]) or 'None',
                        inline=True)
            e.add_field(name="Roles mentioned:",
                        value='\n'.join([n.mention for n in message.mentions]) or 'None',
                        inline=True)
            e.add_field(name="Everyone mentioned:",
                        value=message.mention_everyone,
                        inline=True)
            e.add_field(name="Attachment URLs:",
                        value='\n'.join([n.url for n in message.attachments] )or 'None')
            e.add_field(name='Embed Links:',
                        value='\n'.join([n.url for n in message.embeds]) or 'None',
                        inline=True)
            e.add_field(name='Message URL:',
                        value=message.jump_url,
                        inline=False)
            e.set_footer(text='Turn this off or edit settings with `actionlog config bigbrother`')
            print(await self.action_log_channel(message.guild.id))
            await (await self.action_log_channel(message.guild.id)).send(embed=e)

    async def on_raw_message_delete(self, payload):
        enabled = await self.enabled(payload.guild_id)
        if 'on_message_delete' in enabled:
            message = self.get_message(payload.message_id, payload.channel_id)
            channel = self.get_channel(payload.channel_id)
            e = discord.Embed(colour=discord.Colour.orange())
            e.set_author(name=f"Message by {message.author.display_name}#{message.author.discriminator}"
                              f" deleted.",
                         icon_url=message.author.avatar_url)

    async def on_raw_bulk_message_delete(self, payload):
        enabled = await self.enabled(payload.guild_id)
        if 'on_mass_message_delete' in enabled:
            pass

    async def on_raw_message_edit(self, payload):
        enabled = await self.enabled(payload.guild_id)
        if 'on_message_edit' in enabled:
            pass

    # async def on_raw_reaction_add(self, payload):
    #     enabled = self.enabled(payload.guild_id)
    #
    #
    # async def on_raw_reaction_remove(self, payload):
    #     enabled = self.enabled(payload.guild_id)
    #
    # async def on_raw_reaction_clear(self, payload):
    #     enabled = self.enabled(payload.guild_id)

    async def on_guild_channel_create(self, channel):
        enabled = await self.enabled(channel.guild.id)
        if 'on_channel_created' in enabled:
            pass

    async def on_guild_channel_update(self, channel):
        enabled = await self.enabled(channel.guild.id)
        if 'on_channel_edit' in enabled:
            pass

    async def on_guild_channel_delete(self, channel):
        enabled = await self.enabled(channel.guild.id)
        if 'on_channel_removed' in enabled:
            pass

    async def on_guild_channel_pins_update(self, channel, pin):
        enabled = await self.enabled(channel.guild.id)
        pass

    async def on_webhooks_update(self, channel):
        enabled = await self.enabled(channel.guild.id)
        if 'on_webhook_edit' in enabled:
            pass

    async def on_member_join(self, member):
        enabled = await self.enabled(member.guild.id)
        if 'on_member_join' in enabled:
            pass

    async def on_member_leave(self, member):
        enabled = await self.enabled(member.guild.id)
        if 'on_member_leave' in enabled:
            pass

    # async def on_member_update(self, before, after):
    #     enabled = await self.enabled(after.guild.id)
    #     if 'on_nickname_change' in enabled:
    #         pass

    # async def on_guild_join(self, guild):
    #     enabled = self.enabled(guild.id)

    async def on_guild_update(self, before, after):
        enabled = await self.enabled(after.guild.id)
        if 'on_server_edit' in enabled:
            pass

    async def on_guild_role_create(self, role):
        enabled = await self.enabled(role.guild.id)
        if 'on_role_created' in enabled:
            pass

    async def on_guild_role_delete(self, role):
        enabled = await self.enabled(role.guild.id)
        if 'on_role_removed' in enabled:
            pass

    async def on_guild_role_update(self, before, after):
        enabled = await self.enabled(after.guild.id)
        if 'on_role_edit' in enabled:
            pass

    async def on_guild_emojis_update(self, guild, before, after):
        enabled = await self.enabled(guild.id)

    async def on_voice_state_update(self, member, before, after):
        pass

    async def on_member_ban(self, guild, user):
        enabled = await self.enabled(guild.id)
        if 'on_member_banned' in enabled:
            pass

    async def on_member_unban(self, guild, user):
        enabled = await self.enabled(guild.id)
        if 'on_member_unbanned' in enabled:
            pass



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
        for enabled in config.lookup_action_log[0]:
            strenabled += f'{enabled}\n'
        for disabled in config.lookup_action_log[1]:
            strdisabled += f'{disabled}\n'
        e = discord.Embed(colour=discord.Colour.blue())
        e.set_author(name="ActionLog modules", icon_url=ctx.author.avatar_url)
        e.add_field(name="Enabled modules:", value=strenabled, inline=False)
        e.add_field(name="Disabled modules:", value=strdisabled, inline=False)
        e.add_field(name="Action Log Channel:", value=f'<#{ActionLog.action_log_channel.id}>)', inline=False)
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
                    return await alc.quit(len(ActionModules))
                if str(reaction.emoji) == '\N{CROSS MARK}':
                    await msg.delete()
                if str(reaction.emoji) == '\N{WHITE QUESTION MARK ORNAMENT}':
                    shelp = await alc.show_help()
                    if shelp is True:
                        await alc.modules_config()
                        await alc.modules_config()
                        return await alc.quit(len(ActionModules))
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

    @commands.command(name='help')
    async def _help(self, ctx, *, command: str = None):
        """Shows help about a command or cog

        PARAMETERS: optional: command or cog name

        EXAMPLE: `help about`

        RESULT: Returns a help message for `about` command"""

        try:
            # if no command supplied to get help for run default help paginator
            if command is None:
                p = await HelpPaginator.from_bot(ctx)
            else:
                # get command from bot
                entity = self.bot.get_cog(command) or self.bot.get_command(command)
                # if nothing found return
                if entity is None:
                    clean = command.replace('@', '@\u200b')
                    return await ctx.send(f'Command or category "{clean}" not found.')

                # if its a command do help paginator for commands
                elif isinstance(entity, commands.Command):
                    p = await HelpPaginator.from_command(ctx, entity)

                # if its a cog do help paginator for cog
                else:
                    p = await HelpPaginator.from_cog(ctx, entity)

            # start paginating
            await p.paginate()
        except Exception as e:
            await ctx.send(e)

    @commands.group(invoke_without_command=True, name='announce')
    @commands.has_permissions(manage_messages=True)
    async def _announce(self, ctx, *, msg):
        """Setup announcing messages to specific channels in the server.
                Invoked without a command it will announce the message to set channels, or repeat in current channel if none have been set up.

                    PARAMETERS: [Message to announce]
                    EXAMPLE: `announce This is my cool bot!`
                    RESULT: Sends *This is my cool bot!* to all channels the bot has permissions for in the server

                """
        error_channels = ''
        successful = 0
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT * FROM announce_config WHERE guildid = :id",
                                 {'id': ctx.guild.id})
            dump = await c.fetchall()

        if len(dump) == 0:
            return await ctx.send(msg)
        channels = []
        [channels.append(c[1]) for c in dump]
        # get all channels in guild
        for channel in channels:
            try:
                # try to send the message supplied
                d = await self.bot.get_channel(channel).send(msg)
                successful += 1
            # no send msg permissions
            except discord.errors.Forbidden:
                error_channels += f'<#{channel}>\n'
        embed = discord.Embed()
        if error_channels == '':
            embed.color = (0x00ff00)
        else:
            embed.colour = (0xff0000)
        # tell them how many successful channels and which channels didnt work
        # (should be as intended by their discord perms)
        embed.set_author(name=f"Successful number of channels sent in: {successful}\n",
                         icon_url=self.bot.user.avatar_url)
        if error_channels:
            embed.title = f"I'm missing permissions in the following channels:\n"
            embed.description = error_channels
        c = await ctx.send(embed=embed)
        # delete the message after 5 seconds
        await asyncio.sleep(10)
        return await c.delete()

    @_announce.command()
    async def add(self, ctx, *channels: ChannelConverter):
        error_channels = ''
        chan = []
        for channel in channels:
            if isinstance(channel, discord.CategoryChannel):
                chan.extend(channel.channels)
            else:
                chan.append(channel)
        for channel in chan:
            if channel.permissions_for(ctx.guild.me).send_messages is False:
                error_channels += f'<#{channel.id}>\n'
                continue
            async with aiosqlite.connect(db_path) as db:
                c = await db.execute("SELECT * FROM announce_config WHERE guildid = :id AND channelid = :cid",
                                     {'id': ctx.guild.id, 'cid':channel.id})
                dump = await c.fetchall()
                if len(dump) == 0:
                    await db.execute('INSERT INTO announce_config VALUES (:id, :channelid)',
                                     {'id': ctx.guild.id, 'channelid': channel.id})
                    await db.commit()
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name="All done!", icon_url=ctx.author.avatar_url)
        if len(error_channels) != 0:
            e.title = 'I need send_message permissions in the following channels to add these to' \
                      ' the list, however. These channels were not added:'
            e.description = error_channels
        await ctx.send(embed=e)

    @_announce.command()
    async def remove(self, ctx, *channels: ChannelConverter):
        chan = []
        for channel in channels:
            if isinstance(channel, discord.CategoryChannel):
                chan.extend(channel.channels)
            else:
                chan.append(channel)
        for channel in chan:
            async with aiosqlite.connect(db_path) as db:
                await db.execute("DELETE FROM announce_config WHERE channelid = :id",
                                 {'id': channel.id})
                await db.commit()
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name="All done!", icon_url=ctx.author.avatar_url)
        await ctx.send(embed=e)

    @_announce.command()
    async def sendtemp(self, ctx, *channels: ChannelConverter):
        def check(user):
            if (user is None) or (user.author.id != ctx.author.id):
                return False
            else:
                return True
        error_channels = ''
        chan_to_send = []
        for channel in channels:
            if channel.permissions_for(ctx.guild.me).send_messages is False:
                error_channels += f'<#{channel.id}>\n'
                continue
            else:
                chan_to_send.append(channel)
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name="Gotcha, those channels have been recorded. \n"
                          "What would you like the message to be? (120 sec timeout)",
                     icon_url=ctx.author.avatar_url)
        if len(error_channels) != 0:
            e.title = f"Hm...seems like I don't have `send_messages` permission in the following channels:"
            e.description = error_channels
        await ctx.send(embed=e)
        while True:
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=120.0)
                for channel in chan_to_send:
                    try:
                        await channel.send(msg.content)
                    except discord.Forbidden:
                        continue
                return await ctx.send('All done. Thanks!')

            except asyncio.TimeoutError:
                await ctx.send("You took too long. Try again (120 second timeout)")
                return


    @commands.command()
    async def makeembed(self, ctx):
        # work in progress
        def check(user):
            if (user is None) or (user.author.id != ctx.author.id):
                return False
            else:
                return True

        await ctx.send("Welcome to the interactive embed maker. We are going to make an embed; and then send it to"
                       " a channel. I will time out if you do not reply to a step within 60 seconds. "
                       "If you want to skip a step, type `None`. Let's begin.")

        await ctx.send(f"What would you like the colour to be? Type a name (eg. `navy`) "
                       f"and I will attempt to convert it, or any hex (ie. 0x00ff00 is green). Find a list here:"
                       f"https://www.w3schools.com/cssref/css_colors.asp")
        while True:
            try:
                colour = await self.bot.wait_for('message', check=check, timeout=60.0)
                try:
                    r = webcolors.name_to_rgb(colour.content)[0]
                    g = webcolors.name_to_rgb(colour.content)[1]
                    b = webcolors.name_to_rgb(colour.content)[2]
                    embed = discord.Embed(colour=discord.Colour.from_rgb(r, g, b))
                    break
                except ValueError:
                    await ctx.send("That's not a valid colour! You can find the full list at: "
                                   "https://www.w3schools.com/cssref/css_colors.asp")
                    pass
            except asyncio.TimeoutError:
                await ctx.send("I give up. You took too long")
                return
        await ctx.send(embed=embed)
        await ctx.send("What would you like the author field to contain? Max. 256 characters")
        while True:
            try:
                author = await self.bot.wait_for('message', check=check, timeout=60.0)
                if author.content == 'quit':
                    return
                if author.content == 'None':
                    pass
                else:
                    embed.set_author(name=author.content)
                    break
            except asyncio.TimeoutError:
                await ctx.send("I give up. You took too long")
                return
        await ctx.send('What would you like the title to be? Max characters: 256')
        while True:
            try:
                title = await self.bot.wait_for('message', check=check, timeout=60.0)
                if author.content == 'quit':
                    return
                if author.content == 'None':
                    pass
                if chr(author.content) > 256:
                    await ctx.send("This is more than the allowed 256 characters! Please try again")
                    pass
                else:
                    embed.title = title.content
                    break
            except asyncio.TimeoutError:
                await ctx.send("I give up. You took too long")
                return
        embed.description = 'This is your embed so far.'
        await ctx.send(embed=embed)
        await ctx.send("What would you like the description to be?")
        try:
            description = await self.bot.wait_for('message', check=check, timeout=60.0)
        except asyncio.TimeoutError:
            pass
        embed.description = description
        embed.add_field(name="This is your embed so far",
                        value="These 2 are the first field. What do you want to fill them with?")
        field1 = await self.bot.wait_for('message', check=check, timeout=60.0)
    # to finish

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @commands.command(pass_context=True, hidden=True, name='eval')
    @commands.is_owner()
    async def _eval(self, ctx, *, body: str):
        """Evaluates a code"""

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

    @commands.group(name="prefix", invoke_without_command=True)
    async def prefix(self, ctx):
        """Manages a servers prefixes.

        Invoke this without a command and get the server prefix
        
        Remember <@496558571605983262> is always a prefix.
        """
        prefixes = self.bot.get_prefixes(ctx.message)
        await ctx.send(f'The prefix for {ctx.guild.name} is {prefixes[2] or None}. '
                       f'Remember you can mention me as a prefix!')

    @prefix.command(ignore_extra=False)
    async def change(self, ctx, prefix: Prefix):
        """Adds a prefix for server.
                    PARAMETERS: [Prefix name]
                    EXAMPLE: `prefix add !@`
                    RESULT: Adds prefix !@"""
        # get list of current prefixes
        current_prefix = self.bot.get_prefixes(ctx.message)
        # if prefix changing to is already in the list of prefixes
        if prefix in current_prefix:
            return await ctx.send("Prefix already registered!")
        try:
            # update prefix
            await self.bot.set_guild_prefixes(ctx.message, prefix)
        except Exception as e:
            await ctx.send(f"{e}\N{THUMBS DOWN SIGN}")
        else:
            await ctx.send(f"\N{OK HAND SIGN} Prefix now set to: `{prefix}`. Remember you can always get my "
                           f"attention with <@{self.bot.user.id}>` help`!")

    @commands.command()
    async def kick(self, ctx, user: discord.Member, *, reason: ActionReason):
        # set reason if none supplied
        if reason is None:
            reason = f'Removed by {ctx.author} ({ctx.author.id})'
        # kick
        await user.kick(reason=reason)
        # reason response message
        s = await ctx.send(reason)

        await asyncio.sleep(5)
        # delete response after 5 seconds
        await s.delete()
        try:
            # try to delete the command
            await ctx.delete()
        except:
            pass

    @commands.command()
    async def ban(self, ctx, user: MemberId, *, reason: ActionReason):
        # set reason if none supplied
        if reason is None:
            reason = f'Banned by {ctx.author} ({ctx.author.id})'
        # ban
        await ctx.guild.ban(id=discord.Object(id=user), reason=reason)
        s = await ctx.send(reason)
        await asyncio.sleep(5)
        # delete reason response after 5
        await s.delete()
        try:
            await ctx.delete()
        except:
            pass

    @commands.command()
    async def unban(self, ctx, user: BannedMember, *, reason: ActionReason):
        # set reason
        if not reason:
            reason = f'Unbanned by {ctx.author} ({ctx.author.id})'
        # unban
        await ctx.guild.unban(user.user, reason)
        # send response reason (why was banned)
        if user.reason:
            s = await ctx.send(f"Unbanned {user.user} ({user.user.id}) - banned for {user.reason}")
        else:
            s = await ctx.send(f"Unbanned {user.user} ({user.user.id})")
        await asyncio.sleep(5)
        # delete response reason
        await s.delete()
        try:
            await ctx.delete()
        except discord.Forbidden:
            pass

    # @commands.group(name="actionlog")
    # async def actionlog(self, ctx):
    #     print('ok')
    # @actionlog.command()
    # async def config(self, ctx):
    #     print('ok')

    # @add.error
    # async def prefix_add_error(self, ctx, error):
    #     if isinstance(error, commands.TooManyArguments):
    #         await ctx.send("You've given too many prefixes. Either quote it or only do it one by one.")
    #
    # @prefix.command(name="remove", ignore_extra=False)
    # async def prefix_remove(self, ctx, prefix: Prefix):
    #     """Removes a prefixes from a server.
    #                 PARAMETERS: [prefix name]
    #                 EXAMPLE: `prefix remove !@`
    #                 RESULT: Removes prefixes !@"""
    #     current_prefix = self.bot.get_prefixes(ctx.message)
    #
    #     try:
    #         current_prefix.remove(prefix)
    #     except ValueError:
    #         return await ctx.send("This prefix has not been registered!")
    #     try:
    #         await self.bot.set_guild_prefixes(ctx.message, current_prefix)
    #     except Exception as e:
    #         await ctx.send(f"{e}\N{THUMBS DOWN SIGN}")
    #     else:
    #         await ctx.send("\N{OK HAND SIGN}")
    #
    # @prefix.command(name="clear")
    # async def clear_prefix(self, ctx):
    #     """Clears prefixes for a server.
    #                 PARAMETERS: None
    #                 EXAMPLE: `prefix clear`
    #                 RESULT: Clears prefixes. Only prefix left is <@496558571605983262>. Use this to add more"""
    #     await self.bot.set_guild_prefixes(ctx.message, [])
    #


def setup(bot):
    bot.add_cog(Tools(bot))
    bot.add_cog(ActionLogImplementation(bot))

