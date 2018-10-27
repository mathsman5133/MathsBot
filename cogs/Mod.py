import discord
from discord.ext import commands
import asyncio
import aiosqlite
import os
import re

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
    async def kick(self, ctx, user: discord.Member, *, reason: ActionReason=None):
        # set reason if none supplied
        print('ok')
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
    bot.add_cog(Mod(bot))
