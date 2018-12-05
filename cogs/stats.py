import discord
from discord.ext import commands
import datetime
from collections import Counter
from cogs.utils import db


class Commands(db.Table):
    id = db.PrimaryKeyColumn()

    guild_id = db.Column(db.Integer(big=True))
    channel_id = db.Column(db.Integer(big=True))
    author_id = db.Column(db.Integer(big=True))
    timestamp = db.Column(db.Datetime())
    prefix = db.Column(db.String())
    command = db.Column(db.String())


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

        query = """
                INSERT INTO commands (guild_id, channel_id, author_id, timestamp, prefix, command)
                VALUES ($1, $2, $3, $4, $5, $6);
                """

        await self.bot.pool.execute(query, guild_id, ctx.channel.id,
                                    ctx.author.id, datetime.datetime.utcnow(),
                                    ctx.prefix, command)

        # async with aiosqlite.connect(db_path) as db:
        #     await db.execute("INSERT INTO commands VALUES "
        #                      "(:guild_id, :channel_id, :author_id, :used, :prefix, :command)",
        #                      {'guild_id': guild_id,
        #                       'channel_id': ctx.channel.id,
        #                       'author_id': ctx.author.id,
        #                       'used': datetime.datetime.utcnow(),
        #                       'prefix': ctx.prefix,
        #                       'command': command})
        #     # save
        #     await db.commit()

    async def on_socket_response(self, msg):
        # add socket reponse to counter (scroll to bottom)
        self.bot.socket_stats[msg.get('t')] += 1

    @commands.command(hidden=True)
    @commands.is_owner()
    async def commandstats(self, ctx, limit=20):
        counter = self.bot.command_stats
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

    @commands.command()
    async def about(self, ctx):
        # get time bot up for as datetime object
        delta_uptime = datetime.datetime.utcnow() - self.bot.uptime
        # just get hours, minutes seconds by dividing by remainder of each
        hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        query = """SELECT command FROM commands
                """
        dump = await self.bot.pool.fetch(query)

        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT command FROM commands")
        #     dump = await c.fetchall()

        appinfo = await self.bot.application_info()
        dpn = appinfo.owner.display_name
        dscrm = appinfo.owner.discriminator
        channels = [len(n.channels) for n in self.bot.guilds]

        e = discord.Embed(colour=discord.Colour.orange())
        e.set_author(name=f"{dpn}"
                          f"#{dscrm}",
                     icon_url=appinfo.owner.avatar_url)
        e.description = 'Latest News:\n' \
                        '\N{BLACK SMALL SQUARE} `announce` - Send a message to all setup ' \
                        'channels/categories in the server' \
                        '\n\N{BLACK SMALL SQUARE} Moderation - `kick` `ban` `unban` `purge` `cleanup`'
        e.add_field(name="Guilds",
                    value=f"{len(self.bot.guilds)}",
                    inline=True)
        e.add_field(name="Members",
                    value=f"{len(self.bot.users)}",
                    inline=True)
        e.add_field(name="Channels",
                    value=f"{channels}",
                    inline=True)
        e.add_field(name="Uptime",
                    value=f"{days}d {hours}h {minutes}m {seconds}s")
        e.add_field(name="Ping Time", value=f"{round(self.bot.latency*1000, 2)}ms")
        e.add_field(name="Commands Used",
                    value=f"{len(dump)}")
        e.add_field(name="\u200b", value="[Bot invite (with mod features)]"
                                         "(https://discordapp.com/oauth2/"
                                         "authorize?client_id=496558571605983262&scope=bot&permissions=336063734)"
                                         "\n[Bot invite (restricted)]"
                                         "(https://discordapp.com/oauth2/authorize?"
                                         "client_id=496558571605983262&scope=bot&permissions=511040)",
                    inline=False)
        e.set_footer(text="In Python 3.6 using discord.py (1.0.0a)",
                     icon_url='https://data.world/api/datadotworld-apps/dataset/python/file/raw/logo.png')

        await ctx.send(embed=e)


def setup(bot):
    if not hasattr(bot, 'command_stats'):
        # start counter for commands used (and type) for current session, add as bot attribute
        bot.command_stats = Counter()

    if not hasattr(bot, 'socket_stats'):
        # start counter for commands used (and type) for current session, add as bot attribute
        bot.socket_stats = Counter()

    bot.add_cog(Stats(bot))
