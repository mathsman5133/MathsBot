import discord
from discord.ext import commands
import time
import aiosqlite
import os
import io
from contextlib import redirect_stdout
import textwrap
import traceback
import datetime
import math
import json
import urllib.request

db_path = os.path.join(os.getcwd(), 'cogs', 'utils', 'database.db')


class GuildCommandStats:
    async def show_guild_stats(self, ctx):
        # emojis for top 5
        lookup = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{CLAPPING HANDS SIGN}',
            '\N{CLAPPING HANDS SIGN}'
        )
        # make embed with blurple colour
        embed = discord.Embed(colour=discord.Colour.blurple(), title='Command Stats')
        # get first command and number of commands in db
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT COUNT(*), MIN(used) FROM commands WHERE guild_id = :guild_id",
                                 {'guild_id': ctx.guild.id})
            dump = await c.fetchall()
        # add number of commands to embed
        embed.description = f'{dump[0][0]} commands used.'
        # add first commands date to embed
        embed.set_footer(text="Tracking commands since: ").timestamp = \
            datetime.datetime.strptime(dump[0][1], '%Y-%m-%d %H:%M:%S.%f'
                                                   or datetime.datetime.utcnow())

        # get commands from db and count total number per command
        # get top 5 descending
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute('SELECT command, COUNT(*) as "uses" FROM commands WHERE guild_id = :guild_id'
                                 ' GROUP BY command ORDER BY "uses" DESC LIMIT 5', {'guild_id': ctx.guild.id})
            cmdump = await c.fetchall()
        uses = []
        command = []
        # get uses and command in a nice list which we can use rather than [('!help','5'), ('!ping', '3')]
        for a in cmdump:
            uses.append(a[1])
            command.append(a[0])
        # join them together with emoji
        value = '\n'.join(f'{lookup[index]}: {command} ({uses} uses)'
                          for (index, (command, uses)) in enumerate(cmdump)) or 'No Commands'
        # add top commands field
        embed.add_field(name='Top Commands', value=value, inline=True)

        # its basically the exact same as above 3x again so I'm not gonna type it out again
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT command, COUNT(*) as 'uses' FROM commands WHERE guild_id = :guild_id"
                                 " AND used > (CURRENT_TIMESTAMP - 1) "
                                 "GROUP BY command ORDER BY 'uses' DESC LIMIT 5",
                                 {'guild_id': ctx.guild.id})
            todaycmdump = await c.fetchall()

        uses = []
        command = []
        for a in cmdump:
            uses.append(a[1])
            command.append(a[0])
        value = '\n'.join(f'{lookup[index]}: {command} ({uses} uses)'
                          for (index, (command, uses)) in enumerate(todaycmdump)) or 'No Commands'

        embed.add_field(name='Top Commands Today', value=value, inline=True)
        embed.add_field(name='\u200b', value='\u200b', inline=True)

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT author_id, COUNT(*) as 'uses' FROM commands WHERE guild_id = :guild_id"
                                 " GROUP BY author_id ORDER BY 'uses' DESC LIMIT 5", {'guild_id': ctx.guild.id})
            authdump = await c.fetchall()
        uses = []
        command = []
        for a in cmdump:
            print(a)
            uses.append(a[1])
            command.append(a[0])

        value = '\n'.join(f'{lookup[index]}: <@!{command}> ({uses} bot uses)'
                          for (index, (command, uses)) in enumerate(authdump)) or 'No bot users.'

        embed.add_field(name='Top Command Users', value=value, inline=True)

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT author_id, COUNT(*) as 'uses' FROM commands WHERE guild_id = :guild_id"
                                 " AND used > (CURRENT_TIMESTAMP - 1) GROUP BY author_id ORDER BY 'uses' DESC LIMIT 5",
                                 {'guild_id': ctx.guild.id})
            todayauthdump = await c.fetchall()

        uses = []
        command = []
        for a in cmdump:
            print(a)
            uses.append(a[1])
            command.append(a[0])

        value = '\n'.join(f'{lookup[index]}: <@!{command}> ({uses} bot uses)'
                          for (index, (command, uses)) in enumerate(todayauthdump)) or 'No command users.'

        embed.add_field(name='Top Command Users Today', value=value, inline=True)
        await ctx.send(embed=embed)

    async def show_member_stats(self, ctx, member):
        # basically same as show guild stats but for a member
        lookup = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{CLAPPING HANDS SIGN}',
            '\N{CLAPPING HANDS SIGN}'
        )

        embed = discord.Embed(title='Command Stats', colour=member.colour)
        embed.set_author(name=str(member), icon_url=member.avatar_url)

        # total command uses
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT COUNT(*), MIN(used) FROM commands WHERE guild_id=:id AND author_id=:aid",
                                 {'id': ctx.guild.id, 'aid': member.id})
            count = await c.fetchall()

        embed.description = f'{count[0][0]} commands used.'
        embed.set_footer(text='First command used').timestamp = \
            datetime.datetime.strptime(count[0][1], '%Y-%m-%d %H:%M:%S.%f'
                                       or datetime.datetime.utcnow())

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT command, COUNT(*) as 'uses' "
                                 "FROM commands WHERE guild_id = :gid "
                                 "AND author_id = :aid GROUP BY command ORDER BY 'uses' DESC LIMIT 5",
                                 {'gid': ctx.guild.id, 'aid': member.id})
            records = await c.fetchall()

        uses = []
        command = []
        for a in records:
            print(a)
            uses.append(a[1])
            command.append(a[0])

        value = '\n'.join(f'{lookup[index]}: {command} ({uses} uses)'
                          for (index, (command, uses)) in enumerate(records)) or 'No Commands'

        embed.add_field(name='Most Used Commands', value=value, inline=False)

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT command, COUNT(*) as 'uses' "
                                 "FROM commands WHERE guild_id=:gid "
                                 "AND author_id=:aid AND used > (CURRENT_TIMESTAMP - 1) "
                                 "GROUP BY command ORDER BY 'uses' DESC LIMIT 5",
                                 {'gid': ctx.guild.id, 'aid': member.id})
            records = await c.fetchall()
        uses = []
        command = []
        for a in records:
            print(a)
            uses.append(a[1])
            command.append(a[0])

        value = '\n'.join(f'{lookup[index]}: {command} ({uses} uses)'
                          for (index, (command, uses)) in enumerate(records)) or 'No Commands'

        embed.add_field(name='Most Used Commands Today', value=value, inline=False)
        await ctx.send(embed=embed)



class TabularData:
    def __init__(self):
        self._widths = []
        self._columns = []
        self._rows = []

    def set_columns(self, columns):
        self._columns = columns
        self._widths = [len(c) + 2 for c in columns]

    def add_row(self, row):
        rows = [str(r) for r in row]
        self._rows.append(rows)
        for index, element in enumerate(rows):
            width = len(element) + 2
            if width > self._widths[index]:
                self._widths[index] = width

    def add_rows(self, rows):
        for row in rows:
            self.add_row(row)

    def render(self):
        """Renders a table in rST format.
        Example:
        +-------+-----+
        | Name  | Age |
        +-------+-----+
        | Alice | 24  |
        |  Bob  | 19  |
        +-------+-----+
        """

        sep = '+'.join('-' * w for w in self._widths)
        sep = f'+{sep}+'

        to_draw = [sep]

        def get_entry(d):
            elem = '|'.join(f'{e:^{self._widths[i]}}' for i, e in enumerate(d))
            return f'|{elem}|'

        to_draw.append(get_entry(self._columns))
        to_draw.append(sep)

        for row in self._rows:
            to_draw.append(get_entry(row))

        to_draw.append(sep)
        return '\n'.join(to_draw)


class Admin:
    def __init__(self, bot):
        self.bot = bot
        self._last_result = ''

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @commands.command()
    @commands.is_owner()
    async def stat(self, ctx, *, member: discord.Member = None):
        """Tells you command usage stats for the server or a member.
            PARAMETERS: optional: [member] - a ping, name#discrim or userid
            EXAMPLE: `stats @mathsman` or `stats`
            RESULT: Returns command stats for mathsman or server as a whole"""
        # if no mention show guild stats
        if member is None:
            await GuildCommandStats.show_guild_stats(ctx)
        # else show member stats
        else:
            await GuildCommandStats.show_member_stats(ctx, member)

    @commands.command()
    @commands.is_owner()
    async def load(self, ctx, *, module):
        """Load a cog/extension. Available cogs to reload: `ClaimCommands`, `PlayerCommands`, `ClanCommands`, `DownloadCommands`, `DatabaseCommands`.
                PARAMETERS: [extension name]
                EXAMPLE: `load DownloadCommands`
                RESULT: Loads commands: dl and stopdl. These will now work. Returns result"""
        module = module.lower()
        if not module.startswith("cogs"):
            module = f"cogs.{module}"
        try:
            self.bot.load_extension(module)
        except Exception as e:
            await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @commands.command()
    @commands.is_owner()
    async def unload(self, ctx, *, module):
        """Unloads a cog/extension. Available cogs to unload: `ClaimCommands`, `PlayerCommands`, `ClanCommands`, `DownloadCommands`.
                PARAMETERS: [extension name]
                EXAMPLE: `unload DownloadCommands`
                RESULT: Unloads commands: dl and stopdl. These will now not work. Returns result"""
        module = module.lower()
        if not module.startswith("cogs"):
            module = f"cogs.{module}"

        try:
            self.bot.unload_extension(module)

        except Exception as e:
            await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx, *, module):
        module = module.lower()
        if not module.startswith("cogs"):
            module = f"cogs.{module}"

        self.bot.unload_extension(module)
        self.bot.load_extension(module)
        await ctx.send("\N{THUMBS UP SIGN}")

    @commands.command()
    @commands.is_owner()
    async def shutdown(self, ctx):
        await ctx.send("\N{THUMBS UP SIGN}")
        await self.bot.logout()
        await self.bot.close()

    @commands.command()
    @commands.is_owner()
    async def send_message(self,ctx, cid: int, *, message):
        channel = self.bot.get_channel(cid)

        try:
            await channel.send(message)
            await ctx.send("\N{THUMBS UP SIGN}")
        except Exception as e:
            await ctx.send(f'```py\n{e}\n```')

    @commands.command(name='sqlite')
    @commands.is_owner()
    async def _sqlite(self, ctx, *, query: str):
        try:
            start = time.perf_counter()
            async with aiosqlite.connect(db_path) as db:
                c = await db.execute(query)
                dt = (time.perf_counter() - start) * 1000.0
                try:
                    dump = await c.fetchall()
                    desc = c.description
                    await db.commit()
                except:
                    await db.commit()
                    return await ctx.send(f'`{dt:.2f}ms`')
        except Exception:
            return await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        if len(dump) == 0:
            return await ctx.send(f'`{dt:.2f}ms`')
        headers = list([r[0] for r in desc])
        table = TabularData()
        table.set_columns(headers)
        table.add_rows(list(r for r in dump))
        render = table.render()
        fmt = f'```\n{render}\n```\n*Returned in {dt:.2f}ms*'
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode('utf-8'))
            await ctx.send('Too many results...', file=discord.File(fp, 'results.txt'))
        else:
            await ctx.send(fmt)

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

    @commands.command()
    @commands.is_owner()
    async def status(self, ctx, *, status: str):
        try:
            await self.bot.change_presence(activity=discord.Game(name=status, type=0))
            await ctx.send("\N{THUMBS UP SIGN}")
        except Exception as e:
            await ctx.send(f'```py\n{e}\n```')

    @commands.command()
    @commands.is_owner()
    async def global_ignore(self, ctx, id: int):
        b = {'id': id}
        self.bot.loaded['global_ignored'].append(b)
        await ctx.send("\N{THUMBS UP SIGN}")
        await self.bot.save_json()

    @commands.command()
    @commands.is_owner()
    async def global_unignore(self, ctx, id: int):
        b = {'id': id}
        self.bot.loaded['global_ignored'].remove(b)
        await ctx.send("\N{THUMBS UP SIGN}")
        await self.bot.save_json()

def setup(bot):
    bot.add_cog(Admin(bot))

