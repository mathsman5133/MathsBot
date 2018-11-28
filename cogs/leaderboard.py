import discord
import aiosqlite
import os
from discord.ext import commands
from cogs.utils import db


db_path = os.path.join(os.getcwd(), 'cogs', 'utils', 'database.db')


class LeaderboardDB(db.Table, table_name='leaderboard'):
    id = db.PrimaryKeyColumn

    user_id = db.Column(db.Integer(big=True))
    guild_id = db.Column(db.Integer(big=True))
    game = db.Column(db.String)
    attempts = db.Column(db.String)
    wrong = db.Column(db.String)
    correct = db.Column(db.String)
    games = db.Column(db.String)
    record = db.Column(db.Numeric)



class Leaderboard:
    def __init__(self, bot):
        self.bot = bot
        self.games = ['guess', 'reacttest', 'hangman', 'trivia', 'clashtrivia', 'riddle']

    @commands.group(invoke_without_command=True)
    async def leaderboard(self, ctx, game: str = None):
        """Sends leaderboard for a specific game. Server and game specific.
            PARAMETERS: [game] - name of the game you want leaderboard for
            EXAMPLE: `leaderboard guess`
            RESULT: Leaderboard for the `guess` command"""
        if not game:
            games = '\n{},'.join(self.games)
            return await ctx.send(f"Please choose a game type. These include: {games}\n...more coming soon!")

        return await self.get_leaderboard_guild(game, ctx)

    @leaderboard.command()
    async def all(self, ctx, game: str = None):
        """Gives leaderboard for all servers the bot is in/whom play the game
            PARAMETERS: [game] - name of the game you want leaderboard for
            EXAMPLE: `leaderboard all guess`
            RESULT: Leaderboard for all servers who have played the `guess` game"""
        if not game:
            # need to choose a game
            games = '\n{},'.join(self.games)
            return await ctx.send(f"Please choose a game type. These include: {games}\n...more coming soon!")

        return await self.get_leaderboard_all(game, ctx)

    @commands.command()
    async def gamestats(self, ctx, user: discord.Member = None):
        """Gives stats for games a user has played.
            PARAMETERS: [user] - @mention, nick#discrim, id
            EXAMPLE: `gamestats @mathsman`
            RESULT: Returns @mathsman's stats for games he has played"""
        if not user:
            user = ctx.author

        send = await self.get_leaderboard_user(user, ctx)

    async def get_leaderboard_all(self, gamecom, ctx):
        # emojis we're gonna use for leaderboard. This one is for
        # all guilds
        lookup = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{CLAPPING HANDS SIGN}',
            '\N{CLAPPING HANDS SIGN}'
        )
        embed = discord.Embed(colour=discord.Colour.dark_gold())

        query = """
                SELECT user_id, record FROM leaderboard 
                WHERE game = $1 ORDER BY record ASC LIMIT 5;
                """
        records = await self.bot.pool.fetch(query, gamecom)

        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT userid, record FROM leaderboard "
        #                          "WHERE game = :game ORDER BY record ASC LIMIT 5",
        #                          {'game': gamecom})
        #     records = await c.fetchall()

        value = '\n'.join(f'{lookup[i]} <@{users[i]}>: {record[i]}'
                          for (index, (users, record)) in enumerate(records)) or 'No Records'
        embed.add_field(name="Top Records", value=value, inline=True)

        query = """
                SELECT user_id, games FROM leaderboard 
                WHERE game = $1 ORDER BY games DESC LIMIT 5;
                """
        games = await self.bot.pool.fetch(query, gamecom)

        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT userid, games FROM leaderboard "
        #                          "WHERE game = :game ORDER BY games DESC LIMIT 5",
        #                          {'game': gamecom})
        #     games = await c.fetchall()

        value = '\n'.join(f'{lookup[index]} <@{users}>: {game}'
                          for (index, (users, game)) in enumerate(games)) or 'No Records'
        embed.add_field(name="Top games played", value=value, inline=True)

        query = """
                SELECT user_id, attempts FROM leaderboard 
                WHERE game = $1 ORDER BY attempts DESC LIMIT 5;
                """
        attempts = await self.bot.pool.fetch(query, gamecom)

        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT userid, attempts FROM leaderboard "
        #                          "WHERE game = :game ORDER BY attempts DESC LIMIT 5",
        #                          {'game': gamecom})
        #     attempts = await c.fetchall()

        value = '\n'.join(f'{lookup[index]} <@{users}>: {attempt}'
                          for (index, (users, attempt)) in enumerate(attempts)) or 'No Records'

        # fix embed formatting so attempts + correct + incorrect on seperate line from records and games played
        embed.add_field(name='\u200b', value='\u200b', inline=False)
        embed.add_field(name="Total attempts", value=value, inline=True)

        query = """
                SELECT user_id, correct FROM leaderboard 
                WHERE game = $1 ORDER BY correct DESC LIMIT 5;
                """
        correct = await self.bot.pool.fetch(query, gamecom)

        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT userid, correct FROM leaderboard "
        #                          "WHERE game = :game ORDER BY correct DESC LIMIT 5",
        #                          {'game': gamecom})
        #     correct = await c.fetchall()

        value = '\n'.join(f'{lookup[index]} <@{users}>: {corrects}'
                          for (index, (users, corrects)) in enumerate(correct)) or 'No Records'
        embed.add_field(name="Total correct answers", value=value, inline=True)

        query = """
                SELECT user_id, wrong FROM leaderboard 
                WHERE game = $1 ORDER BY wrong DESC LIMIT 5;
                """
        wrong = await self.bot.pool.fetch(query, gamecom)

        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT userid, wrong FROM leaderboard "
        #                          "WHERE game = :game ORDER BY wrong DESC LIMIT 5",
        #                          {'game': gamecom})
        #     wrong = await c.fetchall()

        value = '\n'.join(f'{lookup[index]} <@{users}>: {wrongs}'
                          for (index, (users, wrongs)) in enumerate(wrong)) or 'No Records'

        embed.add_field(name="Total incorrect answers", value=value, inline=True)
        embed.set_author(name=f"Leaderboard - {gamecom}")
        await ctx.send(embed=embed)

    async def get_leaderboard_guild(self, gamecom, ctx):
        # same but for a guild rather than global (all guilds)
        lookup = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{CLAPPING HANDS SIGN}',
            '\N{CLAPPING HANDS SIGN}'
        )
        embed = discord.Embed(colour=discord.Colour.dark_gold())

        query = """
                SELECT user_id, record FROM leaderboard 
                WHERE game = $1 AND guild_id = $2 ORDER BY record ASC LIMIT 5;
                """
        records = await self.bot.pool.fetch(query, gamecom, ctx.guild.id)

        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT userid, record FROM leaderboard "
        #                          "WHERE game = :game AND guildid = :id ORDER BY record ASC LIMIT 5",
        #                          {'game': gamecom, 'id': ctx.guild.id})
        #     records = await c.fetchall()

        value = '\n'.join(f'{lookup[index]} <@{users}>: {record}'
                          for (index, (users, record)) in enumerate(records)) or 'No Records'
        embed.add_field(name="Top Records", value=value, inline=True)

        query = """
                SELECT user_id, games FROM leaderboard 
                WHERE game = $1 AND guild_id = $2 ORDER BY games DESC LIMIT 5;
                """
        games = await self.bot.pool.fetch(query, gamecom, ctx.guild.id)

        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT userid, games FROM leaderboard "
        #                          "WHERE game = :game AND guildid = :id ORDER BY games DESC LIMIT 5",
        #                          {'game': gamecom, 'id': ctx.guild.id})
        #     games = await c.fetchall()

        value = '\n'.join(f'{lookup[index]} <@{users}>: {game}'
                          for (index, (users, game)) in enumerate(games)) or 'No Records'
        embed.add_field(name="Top games played", value=value, inline=True)

        query = """
                SELECT user_id, attempts FROM leaderboard 
                WHERE game = $1 AND guild_id = $2 ORDER BY attempts DESC LIMIT 5;
                """
        attempts = await self.bot.pool.fetch(query, gamecom, ctx.guild.id)

        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT userid, attempts FROM leaderboard "
        #                          "WHERE game = :game AND guildid = :id ORDER BY attempts DESC LIMIT 5",
        #                          {'game': gamecom, 'id': ctx.guild.id})
        #     attempts = await c.fetchall()

        value = '\n'.join(f'{lookup[index]} <@{users}>: {attempt}'
                          for (index, (users, attempt)) in enumerate(attempts)) or 'No Records'
        embed.add_field(name='\u200b', value='\u200b', inline=False)
        embed.add_field(name="Total attempts", value=value, inline=True)

        query = """
                SELECT user_id, correct FROM leaderboard 
                WHERE game = $1 AND guild_id = $2 ORDER BY correct DESC LIMIT 5;
                """
        correct = await self.bot.pool.fetch(query, gamecom, ctx.guild.id)


        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT userid, correct FROM leaderboard "
        #                          "WHERE game = :game AND guildid = :id ORDER BY correct DESC LIMIT 5",
        #                          {'game': gamecom, 'id': ctx.guild.id})
        #     correct = await c.fetchall()

        value = '\n'.join(f'{lookup[index]} <@{users}>: {corrects}'
                          for (index, (users, corrects)) in enumerate(correct)) or 'No Records'
        embed.add_field(name="Total correct answers", value=value, inline=True)

        query = """
                SELECT user_id, wrong FROM leaderboard 
                WHERE game = $1 AND guild_id = $2 ORDER BY wrong DESC LIMIT 5;
                """
        wrong = await self.bot.pool.fetch(query, gamecom, ctx.guild.id)

        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT userid, wrong FROM leaderboard "
        #                          "WHERE game = :game AND guildid = :id ORDER BY wrong DESC LIMIT 5",
        #                          {'game': gamecom, 'id': ctx.guild.id})
        #     wrong = await c.fetchall()

        value = '\n'.join(f'{lookup[index]} <@{users}>: {wrongs}'
                          for (index, (users, wrongs)) in enumerate(wrong)) or 'No Records'
        embed.add_field(name="Total incorrect answers", value=value, inline=True)
        embed.set_author(name=f"Leaderboard - {gamecom}")
        await ctx.send(embed=embed)

    async def get_leaderboard_user(self, user, ctx):
        # same but for a user
        lookup = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{CLAPPING HANDS SIGN}',
            '\N{CLAPPING HANDS SIGN}'
        )
        embed = discord.Embed(colour=discord.Colour.dark_gold())

        query = """
                SELECT game, record FROM leaderboard 
                WHERE user_id = $1 GROUP BY game ORDER BY record ASC LIMIT 5;
                """
        records = await self.bot.pool.fetch(query, user.id)

        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT game, record FROM leaderboard "
        #                          "WHERE userid = :id GROUP BY game ORDER BY record ASC LIMIT 5",
        #                          {'id': user.id})
        #     records = await c.fetchall()

        value = '\n'.join(f'{lookup[index]} {users}: {record}'
                          for (index, (users, record)) in enumerate(records)) or 'No Records'
        embed.add_field(name="Top Records", value=value, inline=True)

        query = """
                SELECT game, games FROM leaderboard 
                WHERE user_id = $1 GROUP BY game ORDER BY games DESC LIMIT 5;
                """
        games = await self.bot.pool.fetch(query, user.id)

        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT game, games FROM leaderboard "
        #                          "WHERE userid = :id GROUP BY game ORDER BY games DESC LIMIT 5",
        #                          {'id': user.id})
        #     games = await c.fetchall()

        value = '\n'.join(f'{lookup[index]} {users}: {game}'
                          for (index, (users, game)) in enumerate(games)) or 'No Records'
        embed.add_field(name="Top games played", value=value, inline=True)

        query = """
                SELECT game, attempts FROM leaderboard 
                WHERE user_id = $1 GROUP BY game ORDER BY attempts DESC LIMIT 5;
                """
        attempts = await self.bot.pool.fetch(query, user.id)

        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT game, attempts FROM leaderboard "
        #                          "WHERE userid = :id GROUP BY game ORDER BY attempts DESC LIMIT 5",
        #                          {'id': user.id})
        #     attempts = await c.fetchall()

        value = '\n'.join(f'{lookup[index]} {users}: {attempt}'
                          for (index, (users, attempt)) in enumerate(attempts)) or 'No Records'
        embed.add_field(name='\u200b', value='\u200b', inline=False)
        embed.add_field(name="Total attempts", value=value, inline=True)

        query = """
                SELECT game, correct FROM leaderboard 
                WHERE user_id = $1 GROUP BY game ORDER BY correct DESC LIMIT 5;
                """
        correct = await self.bot.pool.fetch(query, user.id)

        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT game, correct FROM leaderboard "
        #                          "WHERE userid = :id GROUP BY game ORDER BY correct DESC LIMIT 5",
        #                          {'id': user.id})
        #     correct = await c.fetchall()

        value = '\n'.join(f'{lookup[index]} {users}: {corrects}'
                          for (index, (users, corrects)) in enumerate(correct)) or 'No Records'
        embed.add_field(name="Total correct answers", value=value, inline=True)

        query = """
                SELECT game, wrong FROM leaderboard 
                WHERE user_id = $1 GROUP BY game ORDER BY wrong DESC LIMIT 5;
                """
        wrong = await self.bot.pool.fetch(query, user.id)

        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT game, wrong FROM leaderboard "
        #                          "WHERE userid = :id GROUP BY game ORDER BY wrong DESC LIMIT 5",
        #                          {'id': user.id})
        #     wrong = await c.fetchall()

        value = '\n'.join(f'{lookup[index]} {users}: {wrongs}'
                          for (index, (users, wrongs)) in enumerate(wrong)) or 'No Records'
        embed.add_field(name="Total incorrect answers", value=value, inline=True)
        embed.set_author(name=f"Leaderboard - {user.display_name}#{user.discriminator}")
        await ctx.send(embed=embed)

    async def into_leaderboard(self, game, record, attempts, wrong, correct,
                               guildid, id):
        # insert stuff into leaderboard table in db. Any command that is on the leaderboard will insert stuff into here
        # on completion of command
        # author id
        # string to return. will add record if applicable
        ret = ''
        # async with aiosqlite.connect(db_path) as db:
        #     # get record for a user in current guild for current game
        #
        #     c = await db.execute("SELECT record, games, attempts, wrong, correct"
        #                          " FROM leaderboard WHERE userid = :id AND game = :game"
        #                          " AND guildid = :guildid",
        #                          {'id': id, 'game': game, 'guildid': guildid})
        #     dump = await c.fetchall()
        #     # if there is a record

        query = """
                SELECT record, games, attempts, wrong, correct 
                FROM leaderboard WHERE user_id = $1 AND game = $2 
                AND guild_id = $3;
                """
        dump = await self.bot.pool.fetch(query, id, game, guildid)

        if len(dump) != 0:
            for prev in dump:
                try:
                    # if the record is less than old one in db
                    if prev[0] > record:
                        query = """
                                UPDATE leaderboard SET record = $1 
                                WHERE user_id = $2 AND game = $3 AND guild_id = $4;
                                """
                        await self.bot.pool.execute(query, record, id, game, guildid)

                        # await db.execute("UPDATE leaderboard SET record = :record "
                        #                  "WHERE userid = :id AND game = :game AND guildid = :guildid",
                        #                  {'record': record, 'id': id, 'game': game, 'guildid': guildid})
                        # add to return string
                        ret += f'Congratulations! You have broken your previous record of {prev[0]} seconds :tada:'

                except TypeError:
                    pass
            # update a player's game in leaderboard adding corrects/attempts/games etc
            if isinstance(attempts, int):
                attempts = dump[0][2] + attempts
            else:
                attempts = 0
            if isinstance(wrong, int):
                wrong = dump[0][3] + wrong
            else:
                wrong = 0
            if isinstance(correct, int):
                correct = dump[0][4] + correct
            else:
                correct = 0
            if not isinstance(record, int):
                record = 0

            query = """
                    UPDATE leaderboard SET games = $1,
                    attempts = $2, wrong = $3, correct = $4 
                    WHERE user_id = $5 AND game = $6 AND guild_id = $7;
                    """
            await self.bot.pool.execute(query, dump[0][1] + 1, attempts,
                                        wrong, correct, id, game, guildid)

            # await db.execute("UPDATE leaderboard SET games = :games,"
            #                  " attempts = :att, wrong = :wrong, correct = :corr "
            #                  "WHERE userid = :id AND game = :game AND guildid = :guildid",
            #                  {'id': id, 'games': dump[0][1] + 1, 'guildid': guildid,
            #                   'att': attempts,
            #                   'wrong': wrong,
            #                   'corr': correct, 'game': game})
            # await db.commit()
            # return the return string (if applicable else returns empty string)
            return ret
        else:
            if not isinstance(attempts, int):
                attempts = 0
            if not isinstance(wrong, int):
                wrong = 0
            if not isinstance(correct, int):
                correct = 0
            if not isinstance(record, int):
                record = 0
            # if first time playing add userid with stuff to game to db
            query = """
                    INSERT INTO leaderboard VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
                    """
            await self.bot.pool.execute(query, id, guildid, game,
                                        record, 1, attempts, wrong, correct)
            # await db.execute("INSERT INTO leaderboard VALUES "
            #                  "(:game, :id, :record, :attempts, :wrong, :correct, :games, :guildid)",
            #                  {'game': game, 'id': id, 'record': record,
            #                   'attempts': attempts, 'wrong': wrong,
            #                   'correct': correct, 'games': 1, 'guildid': guildid})
            # await db.commit()
            ret += f'This must be your first time playing! Congratulations, your record was recorded.' \
                   f' Check the leaderboard to see if you got anywhere'
            return ret


def setup(bot):
    bot.add_cog(Leaderboard(bot))
