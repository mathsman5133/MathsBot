import discord
from discord.ext import commands
import asyncio
import os
from cogs.utils.help import HelpPaginator
from cogs.utils import checks

db_path = os.path.join(os.getcwd(), 'cogs', 'utils', 'database.db')


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
                          ctx.author.top_role > m.top_role

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
            member = discord.utils.find(lambda u: u.user.id == member_id, ban_list)
        except ValueError:
            member = discord.utils.find(lambda u: str(u.user) == argument, ban_list)

        print(member)
        if member is None:
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


class Prefix(commands.Converter):
    async def convert(self, ctx, argument):
        # disallows prefixes pinging bot as they are reserved
        user_id = ctx.bot.user.id
        if argument.startswith((f'<@{user_id}', f'<@!{user_id}>')):
            raise commands.BadArgument('This is a reserved prefix already in use!')
        return argument


class Mod:
    def __init__(self, bot):
        self.bot = bot

    async def __error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(error)

    @commands.group(name="prefix", invoke_without_command=True)
    @checks.is_mod()
    async def prefix(self, ctx):
        """Manages a servers prefixes.

        Invoke this without a command and get the server prefix

        Remember <@496558571605983262> is always a prefix.
        """
        try:
            prefixes = self.bot.get_guild_prefix(ctx.guild.id)
        except KeyError:
            return await ctx.send("The default prefixes are `!` and `?`. Remember you can always get my "
                                  f"attention with <@{self.bot.user.id}>` help`!")
        string = f'`@{ctx.guild.me.display_name}`, '
        for n in prefixes:
            string += f"`{n}`, "
        if len(prefixes) == 0:
            string += "`!`, "
        await ctx.send(f'The prefix(s) for {ctx.guild.name} are {string}'
                       f'Remember you can mention me as a prefix!')

    @prefix.command(ignore_extra=False)
    @checks.is_mod()
    async def add(self, ctx, prefix: Prefix):
        """Adds a prefix for server.
                    PARAMETERS: [Prefix name]
                    EXAMPLE: `prefix add !@`
                    RESULT: Adds prefix !@"""
        # get list of current prefixes
        try:
            current_prefixes = self.bot.get_guild_prefix(ctx.guild.id)
            if prefix in current_prefixes:
                return await ctx.send("Prefix already registered!")
        except KeyError as e:
            print(e)

        # if prefix changing to is already in the list of prefixes

        try:
            # update prefix
            d = {"guildid": ctx.guild.id, "prefix": prefix}
            self.bot.loaded['prefixes'].append(d)
            await self.bot.save_json()

        except Exception as e:
            return await ctx.send(f"{e}\N{THUMBS DOWN SIGN}")

        prefixes = self.bot.get_guild_prefix(ctx.guild.id)
        string = f'`@{ctx.guild.me.display_name}`, '
        for n in prefixes:
            string += f"`{n}`, "
        if len(prefixes) == 0:
            string += "`!`, "
        await ctx.send(f"\N{OK HAND SIGN} Current prefixes now set to: {string}. Remember you can always get my "
                       f"attention with <@{self.bot.user.id}>` help`!")

    @prefix.command(ignore_extra=False)
    @checks.is_mod()
    async def remove(self, ctx, prefix: Prefix):
        try:
            current_prefixes = self.bot.get_guild_prefix(ctx.guild.id)

            # if prefix changing to is already in the list of prefixes
            if prefix not in current_prefixes:
                return await ctx.send("Prefix not registered!")

        except KeyError:
            return await ctx.send("No prefixes registered")

        try:
            # update prefix
            d = {'guildid': ctx.guild.id, 'prefix': prefix}
            self.bot.loaded['prefixes'].remove(d)
            await self.bot.save_json()

        except Exception as e:
            return await ctx.send(f"{e}\N{THUMBS DOWN SIGN}")

        prefixes = self.bot.get_guild_prefix(ctx.guild.id)
        string = f'`@{ctx.guild.me.display_name}`, '
        for n in prefixes:
            string += f"`{n}`, "
        if len(prefixes) == 0:
            string += "`!`, "
        await ctx.send(f"\N{OK HAND SIGN} Current prefixes now set to: {string}. Remember you can always get my "
                       f"attention with <@{self.bot.user.id}>` help`!")

    @prefix.command()
    @checks.is_mod()
    async def clear(self, ctx):
        try:
            current_prefixes = self.bot.get_guild_prefix(ctx.guild.id)
        except KeyError:
            return await ctx.send("No prefixes registered")

        try:
            # update prefix
            for p in current_prefixes:
                d = {'guildid': ctx.guild.id, 'prefix': p}
                self.bot.loaded['prefixes'].remove(d)
            await self.bot.save_json()

        except Exception as e:
            return await ctx.send(f"{e}\N{THUMBS DOWN SIGN}")

        prefixes = self.bot.get_guild_prefix(ctx.guild.id)
        string = f'`@{ctx.guild.me.display_name}`, '
        for n in prefixes:
            string += f"`{n}`, "

        await ctx.send(f"\N{OK HAND SIGN} Current prefixes now set to default prefixes: {string}."
                       f" Remember you can always get my "
                       f"attention with <@{self.bot.user.id}>` help`!")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, user: discord.Member, *, reason: ActionReason=None):
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
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, user: MemberId, *, reason: ActionReason=None):
        # set reason if none supplied
        if reason is None:
            reason = f'Banned by {ctx.author} ({ctx.author.id})'
        # ban
        await ctx.guild.ban(discord.Object(id=user), reason=reason)
        s = await ctx.send(reason)
        await asyncio.sleep(5)
        # delete reason response after 5
        await s.delete()
        try:
            await ctx.delete()
        except:
            pass

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user: BannedMember, *, reason: ActionReason=None):
        # set reason
        if not reason:
            reason = f'Unbanned by {ctx.author} ({ctx.author.id})'

        # unban
        await ctx.guild.unban(user=user.user, reason=reason)
        # send response reason (why was banned)
        if reason:
            s = await ctx.send(f"Unbanned {user.user.name} ({user.user.id}) - banned for {user.reason}")
        else:
            s = await ctx.send(f"Unbanned {user.user.name} ({user.user.id})")
        await asyncio.sleep(5)
        # delete response reason
        await s.delete()
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, num_messages: int=None):
        if num_messages is None:
            num_messages = 100
        if num_messages > 100:
            num_messages = 100
        try:
            deleted = await ctx.channel.purge(limit=num_messages)
        except discord.Forbidden:
            raise discord.Forbidden("I don't have `manage_messages` permission to run this command!")
        msg = await ctx.send(f"Purged {len(deleted)} messages from this channel!")
        await asyncio.sleep(5)
        await msg.delete()

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def cleanup(self, ctx, num_messages: int, *users):
        try:
            to_clean = [(await commands.MemberConverter().convert(ctx, user)) for user in users]
        except commands.BadArgument:
            try:
                to_clean = [(await commands.RoleConverter().convert(ctx, user)) for user in users]
            except commands.BadArgument:
                print(users)
                if users[0] in ['bots', 'humans']:
                    to_clean = []
                    members = ctx.channel.members
                    if users[0] == 'bots':
                        for m in members:
                            if m.bot:
                                to_clean.append(m)
                    if users[0] == 'humans':
                        for m in members:
                            if not m.bot:
                                to_clean.append(m)
                else:
                    raise commands.BadArgument("That was not a correct mention(s), role(s) or `bots` or `humans`")

        if num_messages > 100:
            num_messages = 100

        def check(m):
            return m.author in to_clean
        try:
            deleted = await ctx.channel.purge(limit=num_messages, check=check)
        except discord.Forbidden:
            raise discord.Forbidden("I don't have the required `manage_messages` permission to run this command!")

        send = await ctx.send(f"Deleted {len(deleted)} messages from `{[n.name for n in to_clean]}`.")
        await asyncio.sleep(5)
        await send.delete()

    @commands.group(name='ignore', invoke_without_command=True)
    @checks.is_mod()
    async def _ignore(self, ctx, *user_or_channel):
        try:
            user_or_channel = [(await commands.MemberConverter().convert(ctx, u_c)) for u_c in user_or_channel]
        except commands.BadArgument:
            try:
                user_or_channel = [(await commands.TextChannelConverter().convert(ctx, u_c)) for u_c in user_or_channel]
            except commands.BadArgument:
                raise commands.BadArgument(f"Channel(s) or user(s) {user_or_channel} not found!")

        # user_or_channel = await MemberChannel().convert(ctx, user_or_channel)
        current_ignored = [(self.bot.get_ignored(ctx.guild.id, cid=u_c.id)) for u_c in user_or_channel][0]
        if len(current_ignored) != 0:
            raise commands.BadArgument("Channel or member is already being ignored!")

        to_send = []
        for indiv in user_or_channel:
            b = {'guildid': ctx.guild.id, 'id': indiv.id}
            self.bot.loaded['ignored'].append(b)

        all_ignored = self.bot.get_ignored(ctx.guild.id, cid='all')
        for indiv in all_ignored:
            try:
                user = await commands.MemberConverter().convert(ctx, str(indiv))
                to_send.append(f"{user.display_name}#{user.discriminator}")
            except commands.BadArgument:
                channel = await commands.TextChannelConverter().convert(ctx, str(indiv))
                to_send.append(f"#{channel.name}")

        await ctx.send(f"The list of ignored channels or members is now: `{to_send}`")
        await self.bot.save_json()

    @_ignore.command()
    @checks.is_mod()
    async def list(self, ctx):
        to_send = []
        all_ignored = self.bot.get_ignored(ctx.guild.id, cid='all')
        for indiv in all_ignored:
            try:
                user = await commands.MemberConverter().convert(ctx, str(indiv))
                to_send.append(f"{user.display_name}#{user.discriminator}")
            except commands.BadArgument:
                channel = await commands.TextChannelConverter().convert(ctx, str(indiv))
                to_send.append(f"#{channel.name}")
        e = discord.Embed(colour=discord.Colour.blue())
        e.description = '\n'.join(f'{index}: {to_send[index]}' for index in range(0, len(to_send)))
        return await ctx.send(embed=e)

    @commands.group(name='unignore', invoke_without_command=True)
    @checks.is_mod()
    async def _unignore(self, ctx, *user_or_channel):
        try:
            user_or_channel = [(await commands.MemberConverter().convert(ctx, u_c)) for u_c in user_or_channel]
        except commands.BadArgument:
            try:
                user_or_channel = [(await commands.TextChannelConverter().convert(ctx, u_c)) for u_c in user_or_channel]
            except commands.BadArgument:
                raise commands.BadArgument(f"Channel(s) or user(s) {user_or_channel} not found!")

        current_ignored = [(self.bot.get_ignored(ctx.guild.id, cid=u_c.id)) for u_c in user_or_channel]
        if len(current_ignored) == 2:
            raise commands.BadArgument("Channel or member is not currently being ignored!")

        to_send = []

        for indiv in user_or_channel:
            b = {'guildid': ctx.guild.id, 'id': indiv.id}
            self.bot.loaded['ignored'].remove(b)

        all_ignored = self.bot.get_ignored(ctx.guild.id, cid='all')
        for indiv in all_ignored:
            try:
                user = await commands.MemberConverter().convert(ctx, str(indiv))
                to_send.append(f"{user.display_name}#{user.discriminator}")
            except commands.BadArgument:
                channel = await commands.TextChannelConverter().convert(ctx, str(indiv))
                to_send.append(f"#{channel.name}")

        await ctx.send(f"The list of ignored channels or members is now: `{to_send}`")
        await self.bot.save_json()

    @_unignore.command(name='list')
    @checks.is_mod()
    async def _list(self, ctx):
        return await self.list(ctx)

    # @commands.group(name='admin')
    # @commands.guild_only()
    # @checks.is_admin()
    # async def _admin(self):
    #     pass
    # @_admin.command()
    # @commands.guild_only()
    # @checks.is_admin()
    # async def add(self, ctx, *user_or_role):
    #     pass

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

def setup(bot):
    bot.add_cog(Mod(bot))
