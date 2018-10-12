import discord
from discord.ext import commands
import datetime
from collections import Counter, deque
import aiosqlite
import os

db_path = os.path.join(os.getcwd(), 'cogs', 'utils', 'database.db')


class Stats:
    def __init__(self, bot):
        self.bot = bot

    async def on_command(self, ctx):
        # command name
        command = ctx.command.qualified_name
        # add this command to command stats for current session
        self.bot.command_stats[command] += 1
        message = ctx.message
        destination = None
        # if dm
        if ctx.guild is None:
            destination = 'Private Message'
            guild_id = None
        # otherwise
        else:
            destination = f'#{message.channel} ({message.guild})'
            guild_id = ctx.guild.id
        # insert command (and info) into db
        async with aiosqlite.connect(db_path) as db:
            await db.execute("INSERT INTO commands VALUES "
                             "(:guild_id, :channel_id, :author_id, :used, :prefix, :command)",
                             {'guild_id': guild_id,
                              'channel_id': ctx.channel.id,
                              'author_id': ctx.author.id,
                              'used': datetime.datetime.utcnow(),
                              'prefix': ctx.prefix,
                              'command': command})
            # save
            await db.commit()

    async def on_socket_response(self, msg):
        # add socket reponse to counter (scroll to bottom)
        self.bot.socket_stats[msg.get('t')] += 1

    @commands.command(hidden=True)
    @commands.is_owner()
    async def commandstats(self, ctx, limit=20):
        # gets stats of what commands run
        counter = self.bot.command_stats
        # make codeblock msg formatting look kinda ok
        width = len(max(counter, key=len))

        if limit > 0:
            # get limit most common commands (ie. 20 most common)
            common = counter.most_common(limit)
        else:
            # get em all
            common = counter.most_common()[limit:]

        # codeblock formatting
        output = '\n'.join(f'{k:<{width}}: {c}' for k, c in common)

        await ctx.send(f'```\n{output}\n```')

    @commands.command(hidden=True)
    async def socketstats(self, ctx):
        # get time bot up for
        delta = datetime.datetime.utcnow() - self.bot.uptime
        minutes = delta.total_seconds() / 60
        # number of socket stats observed
        total = sum(self.bot.socket_stats.values())
        cpm = total / minutes
        # send socket stats
        await ctx.send(f'{total} socket events observed ({cpm:.2f}/minute):\n{self.bot.socket_stats}')

    @commands.command()
    async def uptime(self, ctx):
        """Returns bot uptime
            PARAMETERS: None
            EXAMPLE: `uptime`
            RESULT: Returns how long bot has been online for"""
        # get time bot up for as datetime object
        delta_uptime = datetime.datetime.utcnow() - self.bot.uptime
        # just get hours, minutes seconds by dividing by remainder of each
        hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        await ctx.send(f"Uptime: **{days}d, {hours}h, {minutes}m, {seconds}s**")

    @commands.command(name='ping')
    async def pingcmd(self, ctx):
        """Gives bot latency, ie. how fast the bot responds (avg 300ms)
                PARAMETERS: []
                EXAMPLE: `ping`
                RESULT: Bot latency/speed/delay in ms"""
        # get bot latency. I need to investigate how to get library and actual heartbeat stuff too
        duration = self.bot.latency * 1000
        await ctx.send(content='Pong! {:.2f}ms'.format(duration))

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

    @commands.command()
    async def stats(self, ctx, *, member: discord.Member = None):
        """Tells you command usage stats for the server or a member.
            PARAMETERS: optional: [member] - a ping, name#discrim or userid
            EXAMPLE: `stats @mathsman` or `stats`
            RESULT: Returns command stats for mathsman or server as a whole"""
        # if no mention show guild stats
        if member is None:
            await self.show_guild_stats(ctx)
        # else show member stats
        else:
            await self.show_member_stats(ctx, member)


def setup(bot):
    if not hasattr(bot, 'command_stats'):
        # start counter for commands used (and type) for current session, add as bot attribute
        bot.command_stats = Counter()

    if not hasattr(bot, 'socket_stats'):
        # start counter for commands used (and type) for current session, add as bot attribute
        bot.socket_stats = Counter()

    bot.add_cog(Stats(bot))
