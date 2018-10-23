from discord.ext import commands
import asyncio
import discord
import aiosqlite
import random
import time
import os

db_path = os.path.join(os.getcwd(), 'cogs', 'utils', 'database.db')


class Leaderboard:
    def __init__(self, ctx):
        self.ctx = ctx

    async def get_leaderboard_all(self, gamecom):
        # emojis we're gonna use for leaderboard. It looks similar to leaderboard in StatsCommands. this one is for
        # all guilds
        lookup = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{CLAPPING HANDS SIGN}',
            '\N{CLAPPING HANDS SIGN}'
        )
        embed = discord.Embed(colour=discord.Colour.dark_gold())
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT userid, record FROM leaderboard "
                                 "WHERE game = :game ORDER BY record ASC LIMIT 5",
                                 {'game': gamecom})
            records = await c.fetchall()
        # turn shitty db output into nice list
        users = []
        record = []
        for indiv in records:
            users.append(indiv[0])
            record.append(indiv[1])
        value = '\n'.join(f'{lookup[index]} <@{users}>: {record}'
                      for (index, (users, record)) in enumerate(records)) or 'No Records'
        embed.add_field(name="Top Records", value=value, inline=True)

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT userid, games FROM leaderboard "
                                 "WHERE game = :game ORDER BY games DESC LIMIT 5",
                                 {'game': gamecom})
            games = await c.fetchall()
        users = []
        game = []
        for indiv in games:
            users.append(indiv[0])
            game.append(indiv[1])

        value = '\n'.join(f'{lookup[index]} <@{users}>: {game}'
                          for (index, (users, game)) in enumerate(games)) or 'No Records'
        embed.add_field(name="Top games played", value=value, inline=True)

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT userid, attempts FROM leaderboard "
                                 "WHERE game = :game ORDER BY attempts DESC LIMIT 5",
                                 {'game': gamecom})
            attempts = await c.fetchall()

        users = []
        attempt = []
        for indiv in attempts:
            users.append(indiv[0])
            attempt.append(indiv[1])
        value = '\n'.join(f'{lookup[index]} <@{users}>: {attempt}'
                          for (index, (users, attempt)) in enumerate(attempts)) or 'No Records'
        # fix embed formatting so attempts + correct + incorrect on seperate line from records and games played
        embed.add_field(name='\u200b', value='\u200b', inline=False)
        embed.add_field(name="Total attempts", value=value, inline=True)

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT userid, correct FROM leaderboard "
                                 "WHERE game = :game ORDER BY correct DESC LIMIT 5",
                                 {'game': gamecom})
            correct = await c.fetchall()

        users = []
        corrects = []
        for indiv in correct:
            users.append(indiv[0])
            corrects.append(indiv[1])
        value = '\n'.join(f'{lookup[index]} <@{users}>: {corrects}'
                          for (index, (users, corrects)) in enumerate(correct)) or 'No Records'
        embed.add_field(name="Total correct answers", value=value, inline=True)

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT userid, wrong FROM leaderboard "
                                 "WHERE game = :game ORDER BY wrong DESC LIMIT 5",
                                 {'game': gamecom})
            wrong = await c.fetchall()

        users = []
        wrongs = []
        for indiv in wrong:
            users.append(indiv[0])
            wrongs.append(indiv[1])
        value = '\n'.join(f'{lookup[index]} <@{users}>: {wrongs}'
                          for (index, (users, wrongs)) in enumerate(wrong)) or 'No Records'
        embed.add_field(name="Total incorrect answers", value=value, inline=True)
        embed.set_author(name=f"Leaderboard - {gamecom}")
        await self.ctx.send(embed=embed)

    async def get_leaderboard_guild(self, gamecom):
        # same but for a guild rather than global (all guilds)
        lookup = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{CLAPPING HANDS SIGN}',
            '\N{CLAPPING HANDS SIGN}'
        )
        embed = discord.Embed(colour=discord.Colour.dark_gold())
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT userid, record FROM leaderboard "
                                 "WHERE game = :game AND guildid = :id ORDER BY record ASC LIMIT 5",
                                 {'game': gamecom, 'id': self.ctx.guild.id})
            records = await c.fetchall()
        users = []
        record = []
        for indiv in records:
            users.append(indiv[0])
            record.append(indiv[1])
        value = '\n'.join(f'{lookup[index]} <@{users}>: {record}'
                      for (index, (users, record)) in enumerate(records)) or 'No Records'
        embed.add_field(name="Top Records", value=value, inline=True)

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT userid, games FROM leaderboard "
                                 "WHERE game = :game AND guildid = :id ORDER BY games DESC LIMIT 5",
                                 {'game': gamecom, 'id': self.ctx.guild.id})
            games = await c.fetchall()
        users = []
        game = []
        for indiv in games:
            users.append(indiv[0])
            game.append(indiv[1])

        value = '\n'.join(f'{lookup[index]} <@{users}>: {game}'
                          for (index, (users, game)) in enumerate(games)) or 'No Records'
        embed.add_field(name="Top games played", value=value, inline=True)

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT userid, attempts FROM leaderboard "
                                 "WHERE game = :game AND guildid = :id ORDER BY attempts DESC LIMIT 5",
                                 {'game': gamecom, 'id': self.ctx.guild.id})
            attempts = await c.fetchall()

        users = []
        attempt = []
        for indiv in attempts:
            users.append(indiv[0])
            attempt.append(indiv[1])
        value = '\n'.join(f'{lookup[index]} <@{users}>: {attempt}'
                          for (index, (users, attempt)) in enumerate(attempts)) or 'No Records'
        embed.add_field(name='\u200b', value='\u200b', inline=False)
        embed.add_field(name="Total attempts", value=value, inline=True)

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT userid, correct FROM leaderboard "
                                 "WHERE game = :game AND guildid = :id ORDER BY correct DESC LIMIT 5",
                                 {'game': gamecom, 'id': self.ctx.guild.id})
            correct = await c.fetchall()

        users = []
        corrects = []
        for indiv in correct:
            users.append(indiv[0])
            corrects.append(indiv[1])
        value = '\n'.join(f'{lookup[index]} <@{users}>: {corrects}'
                          for (index, (users, corrects)) in enumerate(correct)) or 'No Records'
        embed.add_field(name="Total correct answers", value=value, inline=True)

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT userid, wrong FROM leaderboard "
                                 "WHERE game = :game AND guildid = :id ORDER BY wrong DESC LIMIT 5",
                                 {'game': gamecom, 'id': self.ctx.guild.id})
            wrong = await c.fetchall()

        users = []
        wrongs = []
        for indiv in wrong:
            users.append(indiv[0])
            wrongs.append(indiv[1])
        value = '\n'.join(f'{lookup[index]} <@{users}>: {wrongs}'
                          for (index, (users, wrongs)) in enumerate(wrong)) or 'No Records'
        embed.add_field(name="Total incorrect answers", value=value, inline=True)
        embed.set_author(name=f"Leaderboard - {gamecom}")
        await self.ctx.send(embed=embed)

    async def get_leaderboard_user(self, user):
        # same but for a user
        lookup = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{CLAPPING HANDS SIGN}',
            '\N{CLAPPING HANDS SIGN}'
        )
        embed = discord.Embed(colour=discord.Colour.dark_gold())
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT game, record FROM leaderboard "
                                 "WHERE userid = :id GROUP BY game ORDER BY record ASC LIMIT 5",
                                 {'id': user.id})
            records = await c.fetchall()
        users = []
        record = []
        for indiv in records:
            users.append(indiv[0])
            record.append(indiv[1])
        value = '\n'.join(f'{lookup[index]} {users}: {record}'
                      for (index, (users, record)) in enumerate(records)) or 'No Records'
        embed.add_field(name="Top Records", value=value, inline=True)

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT game, games FROM leaderboard "
                                 "WHERE userid = :id GROUP BY game ORDER BY games DESC LIMIT 5",
                                 {'id': user.id})
            games = await c.fetchall()
        users = []
        game = []
        for indiv in games:
            users.append(indiv[0])
            game.append(indiv[1])

        value = '\n'.join(f'{lookup[index]} {users}: {game}'
                          for (index, (users, game)) in enumerate(games)) or 'No Records'
        embed.add_field(name="Top games played", value=value, inline=True)

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT game, attempts FROM leaderboard "
                                 "WHERE userid = :id GROUP BY game ORDER BY attempts DESC LIMIT 5",
                                 {'id': user.id})
            attempts = await c.fetchall()

        users = []
        attempt = []
        for indiv in attempts:
            users.append(indiv[0])
            attempt.append(indiv[1])
        value = '\n'.join(f'{lookup[index]} {users}: {attempt}'
                          for (index, (users, attempt)) in enumerate(attempts)) or 'No Records'
        embed.add_field(name='\u200b', value='\u200b', inline=False)
        embed.add_field(name="Total attempts", value=value, inline=True)

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT game, correct FROM leaderboard "
                                 "WHERE userid = :id GROUP BY game ORDER BY correct DESC LIMIT 5",
                                 {'id': user.id})
            correct = await c.fetchall()

        users = []
        corrects = []
        for indiv in correct:
            users.append(indiv[0])
            corrects.append(indiv[1])
        value = '\n'.join(f'{lookup[index]} {users}: {corrects}'
                          for (index, (users, corrects)) in enumerate(correct)) or 'No Records'
        embed.add_field(name="Total correct answers", value=value, inline=True)

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT game, wrong FROM leaderboard "
                                 "WHERE userid = :id GROUP BY game ORDER BY wrong DESC LIMIT 5",
                                 {'id': user.id})
            wrong = await c.fetchall()

        users = []
        wrongs = []
        for indiv in wrong:
            users.append(indiv[0])
            wrongs.append(indiv[1])
        value = '\n'.join(f'{lookup[index]} {users}: {wrongs}'
                          for (index, (users, wrongs)) in enumerate(wrong)) or 'No Records'
        embed.add_field(name="Total incorrect answers", value=value, inline=True)
        embed.set_author(name=f"Leaderboard - {user.display_name}#{user.discriminator}")
        await self.ctx.send(embed=embed)

    async def into_leaderboard(self, game=None, record=None, attempts=None, wrong=None, correct=None,
                               guildid=None):
        # insert stuff into leaderboard table in db. Any command that is on the leaderboard will insert stuff into here
        # on completion of command
        # author id
        id = self.ctx.author.id
        # string to return. will add record if applicable
        ret = ''
        async with aiosqlite.connect(db_path) as db:
            # get record for a user in current guild for current game
            c = await db.execute("SELECT record, games, attempts, wrong, correct"
                                 " FROM leaderboard WHERE userid = :id AND game = :game"
                                 " AND guildid = :guildid",
                                 {'id': id, 'game': game, 'guildid': guildid})
            dump = await c.fetchall()
            # if there is a record
            if len(dump) != 0:
                # once again shitty db return and I've obv learnt a lot since did this one
                for prev in dump:
                    try:
                        # if the record is less than old one in db
                        if prev[0] > record:
                            await db.execute("UPDATE leaderboard SET record = :record "
                                             "WHERE userid = :id AND game = :game AND guildid = :guildid",
                                             {'record': record, 'id': id, 'game': game, 'guildid': guildid})
                            # add to return string
                            ret += f'Congratulations! You have broken your previous record of {prev[0]} seconds :tada:'
                    # this catches something I cant remember
                    except TypeError:
                        pass
                # update a player's game in leaderboard adding corrects/attempts/games etc.
                if not attempts:
                    attempts = None
                else:
                    attempts = dump[0][2] + attempts
                if not wrong:
                    wrong = None
                else:
                    wrong = dump[0][3] + wrong
                if not correct:
                    correct = None
                else:
                    correct = dump[0][4] + correct
                await db.execute("UPDATE leaderboard SET games = :games,"
                                 " attempts = :att, wrong = :wrong, correct = :corr "
                                 "WHERE userid = :id AND game = :game AND guildid = :guildid",
                                 {'id': id, 'games': dump[0][1] + 1, 'guildid': guildid,
                                  'att': attempts,
                                  'wrong': wrong,
                                  'corr': correct, 'game': game})
                await db.commit()
                # return the return string (if applicable else returns empty string)
                return ret
            else:
                # if first time playing add userid with stuff to game to db
                await db.execute("INSERT INTO leaderboard VALUES "
                                 "(:game, :id, :record, :attempts, :wrong, :correct, :games, :guildid)",
                                 {'game': game, 'id': id, 'record': record,
                                  'attempts': attempts, 'wrong': wrong,
                                  'correct': correct, 'games': 1, 'guildid': guildid})
                await db.commit()
                ret += f'This must be your first time playing! Congratulations, your record was recorded.' \
                       f' Check the leaderboard to see if you got anywhere'
                return ret


class Games:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def leaderboard(self, ctx, game: str = None):
        """Sends leaderboard for a specific game. Server and game specific.
            PARAMETERS: [game] - name of the game you want leaderboard for
            EXAMPLE: `leaderboard guess`
            RESULT: Leaderboard for the `guess` command"""
        if not game:
            # they didn't choose a game
            await ctx.send("Please choose a game type. These include: "
                           "\n`guess`\n`reacttest`\n`hangman`\n`clashtrivia`\n`trivia`\n`riddle`\nmore coming soon...")
            return
        leaderboard = Leaderboard(ctx)
        # get leaderboard for a game
        send = await leaderboard.get_leaderboard_guild(game)

    @leaderboard.command()
    async def all(self, ctx, game: str=None):
        """Gives leaderboard for all servers the bot is in/whom play the game
            PARAMETERS: [game] - name of the game you want leaderboard for
            EXAMPLE: `leaderboard all guess`
            RESULT: Leaderboard for all servers who have played the `guess` game"""
        if not game:
            # need to choose a game
            await ctx.send("Please choose a game type. These include: \n`guess`\n`reacttest`\nmore coming soon...")
            return
        leaderboard = Leaderboard(ctx)
        # get and send leaderboard for a game
        send = await leaderboard.get_leaderboard_all(game)

    @commands.command()
    async def gamestats(self, ctx, user: discord.Member=None):
        """Gives stats for games a user has played.
            PARAMETERS: [user] - @mention, nick#discrim, id
            EXAMPLE: `gamestats @mathsman`
            RESULT: Returns @mathsman's stats for games he has played"""
        if not user:
            user = ctx.author
        # same thing for a user different command tho coz need to work out how to use group commands in my help
        leaderboard = Leaderboard(ctx)
        send = await leaderboard.get_leaderboard_user(user)

    @commands.command()
    async def clashtrivia(self, ctx):
        """Play a game of clash of clans trivia. There are 5 questions and I will timeout after 15 seconds
            PARAMETERS: None
            EXAMPLE: `clashtrivia`
            RESULT: Starts a game of clash trivia. You have 5 questions and 15 seconds to answer each"""
        # choose random 5 numbers to get question for. before I realised you could do it in sql statement
        numbers = random.sample(range(1, 52), 5)
        dump = []
        correct = 0
        attempts = 0
        avgatt = 0
        avgcor = 0

        # check function when we are waiting for an answer to make sure its author and either A, B, C, D
        def check(user):
            # if no user (?) ir user id isnt same as original author id
            if (user is None) or (user.author.id != ctx.author.id):
                return False
            else:
                # otherwise test to see if message is in list of answers
                if user.content in ['A', 'B', 'C', 'D']:
                    return True
                else:
                    return False

        async with aiosqlite.connect(db_path) as db:
            # get questions and turn each question/answers etc. stuff from db into list we can use
            for num in numbers:
                c = await db.execute("SELECT * FROM clash_trivia WHERE number = :num", {'num': num})
                fetch = await c.fetchall()
                dump.append(fetch[0])
        # for each trivia question in the list from our db
        for trivia in dump:
            # send trivia question
            embed = discord.Embed(colour=0x0000ff)
            embed.set_author(name=trivia[2], icon_url=ctx.message.author.avatar_url)
            embed.set_thumbnail(url=trivia[8])
            embed.description = trivia[3]
            embed.set_footer(text="Multiple Choice! Type the letter of the answer you think it is.")
            send = await ctx.send(embed=embed)
            while True:
                try:
                    # wait for a response which satisfies our check function
                    msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                    # add one to attempts
                    attempts += 1
                    # update clash trivia stats as we go (ie. tells you % of people who on average get that
                    # specific question right. need to make it nicer
                    async with aiosqlite.connect(db_path) as db:
                        await db.execute("UPDATE clash_trivia SET attempts = :att WHERE number = :num",
                                         {'att': trivia[7] + 1, 'num': trivia[0]})
                        await db.commit()
                    # add average trivia score for that question to total average for these questions
                    avgatt += int(trivia[7])
                    avgcor += int(trivia[6])
                    # if correct answer
                    if msg.content == trivia[4]:
                        async with aiosqlite.connect(db_path) as db:
                            # add 1 to correct answers for that question in db
                            await db.execute("UPDATE clash_trivia SET correct = :att WHERE number = :num",
                                             {'att': trivia[6] + 1, 'num': trivia[0]})
                            await db.commit()
                        # add 1 to correct answers for this game
                        correct += 1
                        # embed formatting stuff
                        embed = discord.Embed(colour=0x00ff00)
                        embed.set_author(name="Correct!", icon_url=ctx.message.author.avatar_url)
                        embed.description = f'You are currently {correct}/{attempts}' \
                                            f'\n{trivia[6]}/{trivia[7]} ({round(trivia[6]/trivia[7], 2)*100}%) ' \
                                            f'typically get this question correct.'
                        embed.add_field(name="Explanation", value=trivia[5])
                        # edit original message with either correct/incorrect.
                        # partly why I didnt just send a new msg was coz didn't want people cheating as
                        # only have 50 questions (not 2k+ like other cmds)
                        await send.edit(embed=embed)
                        # exit while true statement
                        break
                    else:
                        # embed format for incorrect
                        embed = discord.Embed(colour=0xff0000)
                        embed.set_author(name="Incorrect!", icon_url=ctx.message.author.avatar_url)
                        embed.description = f'You are currently {correct}/{attempts}' \
                                            f'\n{trivia[6]}/{trivia[7]} ({100 - round(trivia[6]/trivia[7], 2)*100}%) ' \
                                            f'typically get this question wrong.'
                        embed.add_field(name="Explanation", value=trivia[5])
                        await send.edit(embed=embed)
                        break
                except asyncio.TimeoutError:
                    # timed out + game over - longer than 15sec
                    embed = discord.Embed(colour=0xff0000)
                    embed.set_author(name="You took too long! Game over", icon_url=ctx.author.avatar_url)
                    await send.edit(embed=embed)
                    return
        # having iterated through list of questions game is now over. Do stuff accordingly
        embed = discord.Embed(colour=0x00ff00)
        # enter stats into leaderboard
        lb = Leaderboard(ctx)
        intolb = await lb.into_leaderboard(game='clashtrivia', record=None, attempts=attempts,
                                           wrong=attempts - correct, correct=correct, guildid=ctx.guild.id)
        # if record broken tell in description
        if intolb:
            embed.description = intolb
        # shitty stats
        embed.set_author(name="Congratulations; you made it.", icon_url=ctx.author.avatar_url)
        embed.add_field(name="Your stats", value=f"{correct}/{attempts} "
                                                 f"({round(correct/attempts, 2)*100}%)")

        embed.add_field(name="Average stats", value=f"{avgcor}/{avgatt} "
                                                    f"({round(avgcor/avgatt, 2)*100}%)")
        embed.set_footer(text="Images and explanations courtesy of Clash of Clans Wiki",
                         icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=embed)

    async def trivia_category(self, ctx, difficulty_topic: str=None):
        # return question with category or difficulty for trivia games

        # if msg content is easy, med, hard then look for that:
        if difficulty_topic in ['easy', 'medium', 'hard']:
            async with aiosqlite.connect(db_path) as db:
                c = await db.execute("SELECT * FROM trivia WHERE used = 0 AND difficulty = :dif"
                                     " ORDER BY RANDOM() LIMIT 10",
                                     {'dif': difficulty_topic})
                # return 10 questions with difficulty specified
                return await c.fetchall()
        # if no topic then get 10 random ones
        if not difficulty_topic:
            async with aiosqlite.connect(db_path) as db:
                c = await db.execute("SELECT * FROM trivia WHERE used = 0 ORDER BY RANDOM() LIMIT 10")
                return await c.fetchall()
        # if it is 'categories' then they want to know what categories available
        else:
            if difficulty_topic == 'categories':
                async with aiosqlite.connect(db_path) as db:
                    # get all categories for all questions
                    c = await db.execute("SELECT category FROM trivia")
                    # unique ones as a list
                    dump = list(set(await c.fetchall()))
                    # send them
                    embed = discord.Embed(colour=0x00ff00)
                    embed.set_author(name="Categories for trivia games", icon_url=ctx.author.avatar_url)
                    desc = ''
                    for cat in dump:
                        desc += cat[0] + '\n'
                    embed.add_field(name='\u200b', value=desc)
                    embed.set_footer(text="Type `.trivia [category]` to get a trivia game of that category!",
                                     icon_url=self.bot.user.avatar_url)
                    await ctx.send(embed=embed)
                    # return False
                    return False
            # otherwise get 10 questions with that category
            async with aiosqlite.connect(db_path) as db:
                c = await db.execute("SELECT * FROM trivia WHERE used = 0 AND category = :cat"
                                     " ORDER BY RANDOM() LIMIT 10",
                                     {'cat': difficulty_topic})
                # return results (could be none)
                return await c.fetchall()

    @commands.command()
    async def trivia(self, ctx, *, difficulty_or_topic: str=None):
        """Start a game of trivia with yourself. Select the difficulty or topic. There is 10 questions and I will timeout after 15 seconds

            PARAMETERS: optional: [difficulty or topic] - easy, medium, hard, or any topic found with `trivia categories`
            EXAMPLE: `trivia easy` or `trivia Politics`
            RESULT: Initiates an easy game of trivia or one with the topic Politics"""
        dump = await self.trivia_category(ctx, difficulty_or_topic)
        # if I sent a category list:
        if dump is False:
            return
        # if category not found
        if len(dump) == 0:
            embed = discord.Embed(colour=0xff0000)
            embed.set_author(name="Category not found", icon_url=ctx.author.avatar_url)
            embed.description = 'Find all categories with .trivia categories. ' \
                                'Difficulties are: easy, medium, hard.'
            await ctx.send(embed=embed)
            return

        correct = 0
        attempts = 0
        # otherwise:

        def check(user):
            # same check as clash trivia
            if (user is None) or (user.author.id != ctx.author.id):
                return False
            else:
                if user.content in ['A', 'B', 'C', 'D']:
                    return True
                else:
                    return False
        # same idea as clash trivia
        for trivia in dump:
            embed = discord.Embed(colour=0x0000ff)
            embed.set_author(name=trivia[3], icon_url=ctx.message.author.avatar_url)
            embed.set_thumbnail(url='https://is2-ssl.mzstatic.com/'
                                    'image/thumb/Purple118/v4/96/c7/cc/'
                                    '96c7cccf-42e3-33c8-4b12-aa12e0049c8a/source/256x256bb.jpg')

            embed.description = trivia[5]
            embed.set_footer(text="Multiple Choice! Type the letter of the answer you think it is.")
            send = await ctx.send(embed=embed)
            while True:
                try:
                    msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                    attempts += 1
                    async with aiosqlite.connect(db_path) as db:
                        await db.execute("UPDATE trivia SET used = 1 WHERE id = :id",
                                         {'id': trivia[0]})
                        await db.commit()
                    if msg.content == trivia[4][0]:
                        correct += 1
                        embed = discord.Embed(colour=0x00ff00)
                        embed.set_author(name="Correct!", icon_url=ctx.message.author.avatar_url)
                        embed.title = trivia[3]
                        embed.description = trivia[5]
                        embed.add_field(name="Correct Answer:", value=trivia[4])
                        embed.add_field(name=f'You are currently:',
                                        value=f'{correct}/{attempts} ({round(((correct / attempts)*100), 2)}%)',
                                        inline=False)
                        await send.edit(embed=embed)
                        break
                    else:
                        embed = discord.Embed(colour=0xff0000)
                        embed.set_author(name="Incorrect!", icon_url=ctx.message.author.avatar_url)
                        embed.title = trivia[3]
                        embed.description = trivia[5]
                        embed.add_field(name="Correct Answer:", value=trivia[4])
                        embed.add_field(name=f'You are currently:',
                                        value=f'{correct}/{attempts} ({round(((correct / attempts)*100), 2)}%)',
                                        inline=False)
                        await send.edit(embed=embed)
                        break
                except asyncio.TimeoutError:
                    embed = discord.Embed(colour=0xff0000)
                    embed.set_author(name="You took too long! Game over", icon_url=ctx.author.avatar_url)
                    await send.edit(embed=embed)
                    return
        embed = discord.Embed(colour=0x00ff00)
        lb = Leaderboard(ctx)
        intolb = await lb.into_leaderboard(game='trivia', record=None, attempts=attempts,
                                           wrong=attempts - correct, correct=correct, guildid=ctx.guild.id)
        if intolb:
            embed.description = intolb
        embed.set_author(name="Game Over!", icon_url=ctx.author.avatar_url)
        embed.add_field(name="Your stats", value=f"{correct}/{attempts} "
                                                 f"({round(correct/attempts, 2)*100}%)")

        await ctx.send(embed=embed)

    @commands.command()
    async def triviagame(self, ctx, ping: discord.Member = None, *, difficulty_topic: str=None):
        """Start a trivia game with a friend! Specify the difficulty or topic. There are 5 questions each, and I will timeout if you do not respond within 15 seconds.

            PARAMETERS: [user] - @mention/nick#discrim/id, optional:[difficulty or topic] - easy, medium, hard, or a topic in `trivia categories`
            EXAMPLE: `triviagame @mathsman` or `triviagame @mathsman easy`
            RESULT: Starts a trivia game with @mathsman, or an easy trivia game with @mathsman"""
        # tell them they need to ping someone
        if not ping:
            embed = discord.Embed(colour=0xff0000)
            embed.set_author(name="You need a friend to play with!", icon_url=ctx.author.avatar_url)
            embed.description = 'If you want to play by yourself, use command `.trivia`'
            await ctx.send(embed=embed)
            return
        dump = await self.trivia_category(ctx, difficulty_topic)
        # if I sent category list
        if dump is False:
            return
        # if category not found
        if len(dump) == 0:
            embed = discord.Embed(colour=0xff0000)
            embed.set_author(name="Category not found", icon_url=ctx.author.avatar_url)
            embed.description = 'Find all categories with .trivia categories command. ' \
                                'Difficulties are: easy, medium, hard.'
            await ctx.send(embed=embed)
            return
        # same idea as normal game but with excess code I probs dont need
        # this records what turn it is. Lets me see whether I need to do stuff for which person
        # (works on even having no remainder and odd having remainer where odd and even are each person
        counter = 0
        correctauthor = 0
        attemptsauthor = 0
        correctping = 0
        attemptsping = 0

        def check(user):
            # if counter is even ie. second person go ie. ping's turn
            if counter % 2 == 0:
                if (user is None) or user.author.id != ping.id:
                    return False
            else:
                if (user is None) or user.author.id != ctx.author.id:
                    return False
            if user.content in ['A', 'B', 'C', 'D']:
                return True
            else:
                return False
        # you get the idea same as trivia but with 2 arguments mostly for everything, one for author one for ping
        for trivia in dump:
            counter += 1
            if counter % 2 == 0:
                user = ping
                ouser = ctx.author

            else:
                user = ctx.author
                ouser = ping

            embed = discord.Embed(colour=0x0000ff)
            embed.set_author(name=f"{user.display_name}#{user.discriminator}'s Turn!", icon_url=user.avatar_url)
            embed.title = trivia[3]
            embed.set_thumbnail(url=user.avatar_url)
            embed.description = trivia[5]
            embed.set_footer(text="Multiple Choice! Type the letter of the answer you think it is.")
            send = await ctx.send(embed=embed)
            while True:
                try:
                    msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                    if counter % 2 == 0:
                        attemptsping += 1
                    else:
                        attemptsauthor += 1

                    async with aiosqlite.connect(db_path) as db:
                        await db.execute("UPDATE trivia SET used = 1 WHERE id = :id",
                                         {'id': trivia[0]})
                        await db.commit()
                    if msg.content == trivia[4][0]:
                        if counter % 2 == 0:
                            correctping += 1
                        else:
                            correctauthor += 1
                    if counter % 2 == 0:
                        correctuser = correctping
                        attemptsuser = attemptsping
                        correctother = correctauthor
                        attemptsother = attemptsauthor
                    else:
                        correctuser = correctauthor
                        attemptsuser = attemptsauthor
                        correctother = correctping
                        attemptsother = attemptsping
                    if msg.content == trivia[4][0]:
                        try:
                            other = f"{correctother}/{attemptsother}" \
                                    f" ({round(((correctother / attemptsother)*100),2)}%)"
                        except ZeroDivisionError:
                            other = "Hasn't had a turn yet!"
                        embed = discord.Embed(colour=0x00ff00)
                        embed.set_author(name="Correct!", icon_url=user.avatar_url)
                        embed.title = trivia[3]
                        embed.description = trivia[5]
                        embed.add_field(name="Correct Answer:", value=trivia[4], inline=False)
                        embed.add_field(name=f'You are currently:',
                                        value=f'{correctuser}/{attemptsuser} '
                                              f'({round(((correctuser / attemptsuser)*100), 2)}%)',
                                        inline=True)
                        embed.add_field(name=f"{ouser.display_name}#{ouser.discriminator} is currently: ",
                                        value=other,
                                        inline=True)
                        await send.edit(embed=embed)
                        break
                    else:
                        try:
                            other = f"{correctother}/{attemptsother}" \
                                    f" ({round(((correctother / attemptsother)*100),2)}%)"
                        except ZeroDivisionError:
                            other = "Hasn't had a turn yet!"
                        embed = discord.Embed(colour=0xff0000)
                        embed.set_author(name="Incorrect!", icon_url=user.avatar_url)
                        embed.title = trivia[3]
                        embed.description = trivia[5]
                        embed.add_field(name="Correct Answer:", value=trivia[4], inline=False)
                        embed.add_field(name=f'You are currently:',
                                        value=f'{correctuser}/{attemptsuser} '
                                              f'({round(((correctuser / attemptsuser)*100), 2)}%)',
                                        inline=True)
                        embed.add_field(name=f"{ouser.display_name}#{ouser.discriminator} is currently: ",
                                        value=other,
                                        inline=True)
                        await send.edit(embed=embed)
                        break
                except asyncio.TimeoutError:
                    embed = discord.Embed(colour=0xff0000)
                    embed.set_author(name="You took too long! Game over", icon_url=user.avatar_url)
                    await send.edit(embed=embed)
                    return
        # this part confused the shit outta me with different names and stuff
        if correctauthor > correctping:
            winner = ctx.author
            loser = ping
            winnercorrect = correctauthor
            winnerattempts = attemptsauthor
            losercorrect = correctping
            loserattempts = attemptsping
        else:
            winner = ping
            loser = ctx.author
            winnercorrect = correctping
            winnerattempts = attemptsping
            losercorrect = correctauthor
            loserattempts = attemptsauthor

        embed = discord.Embed(colour=0x00ff00)
        embed.set_author(name=f"Game Over! {winner.display_name}#{winner.discriminator} is the Winner!",
                         icon_url=loser.avatar_url)
        embed.set_thumbnail(url=winner.avatar_url)
        embed.add_field(name=f"{winner.display_name}#{winner.discriminator} stats: ",
                        value=f"{winnercorrect}/{winnerattempts} "
                              f"({round(winnercorrect/winnerattempts, 2)*100}%)")
        embed.add_field(name=f"{loser.display_name}#{loser.discriminator} stats: ",
                        value=f"{losercorrect}/{loserattempts} "
                              f"({round(losercorrect/loserattempts, 2)*100}%)")
        await ctx.send(embed=embed)
        # we're not gonna put games into db coz idk why not but they're just for fun

    @commands.command()
    async def reacttest(self, ctx):
        """Test you reaction speed! Hit the emoji when the embed turns green
            PARAMETERS: None
            EXAMPLE: `reacttest`
            RESULT: Wait for the embed to turn green and whack the emoji"""
        # check if reaction is same reaction and reacter is author
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '\N{OCTAGONAL SIGN}'
        embed = discord.Embed(colour=0x0000ff)
        embed.set_author(name="Press the reaction when the embed turns green", icon_url=ctx.author.avatar_url)
        send = await ctx.send(embed=embed)
        await send.add_reaction('\N{OCTAGONAL SIGN}')
        # random delay time
        delaytime = random.randint(10, 30) / 10
        # cheating or worked ok
        wrong = 0
        ok = 0
        while True:
            try:
                # wait for check. timeout is random delay time. If check returns true then they cheated
                reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=delaytime)
                wrong += 1
                embed = discord.Embed(colour=0xff0000)
                embed.set_author(name="No Cheating!",
                                 icon_url='https://cdn.shopify.com/s/files/1/1061/1924/products/'
                                          'Very_Angry_Emoji_7f7bb8df-d9dc-4cda-b79f-5453e764d4ea_large.png?v=1480481058')
                await send.edit(embed=embed)
                # insert into leaderboard that they cheated
                lb = Leaderboard(ctx)
                intolb = await lb.into_leaderboard(game='clashtrivia', record=None, attempts=wrong,
                                                   wrong=wrong, correct=ok, guildid=ctx.guild.id)
                return
                # end game
            except asyncio.TimeoutError:
                break
                # continue
        embed = discord.Embed(colour=0x00ff00)
        embed.set_author(name="GO!", icon_url=ctx.author.avatar_url)
        # start timer
        start = time.perf_counter()
        await send.edit(embed=embed)
        while True:
            try:
                # wait for reaction add. timeout 3 seconds
                reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=3.0)
                # finish timer
                end = time.perf_counter()
                # subtract bot latency coz that's not fair to factor in my slowness.
                # still has delay from when start to finish check which is apparantly for some a lot and annoying
                dif = round((end - start - self.bot.latency), 4)
                # didnt cheat
                ok += 1
                embed = discord.Embed(colour=0x0000ff)
                # insert into leaderboard stuff
                lb = Leaderboard(ctx)
                leader = await lb.into_leaderboard(game='reacttest', record=dif, attempts=ok,
                                                   wrong=wrong, correct=ok, guildid=ctx.guild.id)
                # reaction time
                desc = f'**{dif}** seconds'
                # if leaderboard returned (a record)
                if leader:
                    desc += f'\n{leader}'
                embed.set_author(name="Your reaction time is....", icon_url=ctx.author.avatar_url)
                embed.description = desc
                # send results
                await send.edit(embed=embed)
                # eh why bother needing more perms not that important
                # await send.remove_reaction('\N{OCTAGONAL SIGN}', ctx.author)
                # await send.remove_reaction('\N{OCTAGONAL SIGN}', bot.user)
                break
            # took longer than 3 sec
            except asyncio.TimeoutError:
                embed = discord.Embed(colour=0xff0000)
                embed.set_author(name="You took too long!", icon_url=ctx.author.avatar_url)
                await send.edit(embed=embed)
                break

    @commands.command(name='guess')
    async def guess_number(self, ctx, limit=None):
        """I choose a number and you have to guess! Default limit is 1000. I will tell you if you are too small or too big.

            PARAMETERS: optional: [limit] - the limit of the range I choose my number
            EXAMPLE: `guess` or `guess 500`
            RESULT: Starts a guessing game with a number between 1000 or 500"""
        # if limit is not specified set to default 1000. I should just change it to that next to limit hey
        if not limit:
            limit = 1000
        else:
            # see if its integer and tell them if not
            try:
                int(limit)
            except:
                await ctx.send("Please enter an integer parameter, or none at all (will default to 1000)")
                return

        # checks
        async def check_send():
            # if its first round dont give them a difference
            if counter == 1:
                dif = "First round. I ain't that stupid"
            else:
                # otherwise give average difference
                dif = int(sum(diflist) / len(diflist))
            # if msg number bigger than actual number
            if int(msg.content) >= number:
                embed = discord.Embed(colour=0xffa500)
                embed.set_author(name="Too large!", icon_url=ctx.author.avatar_url)
                embed.set_footer(text=f"Average difference: {dif}")
                await ctx.send(embed=embed)

            else:
                embed = discord.Embed(colour=0x0000ff)
                embed.set_author(name="Too small!", icon_url=ctx.author.avatar_url)
                embed.set_footer(text=f"Average difference: {dif}")
                await ctx.send(embed=embed)

        #check
        def check(user):
            # user is original author
            if (user is None) or (user.author.id != ctx.author.id):
                return False
            else:
                try:
                    # content is integer
                    int(user.content)
                    return True
                except:
                    return False
        # start guessing game
        await ctx.send(f"I have chosen a number between 1 and {str(limit)}. You have 15 seconds to try a "
                       "number before I time out. I will tell you if you are too big or too small")
        # choose number
        number = random.randint(1, int(limit))
        # attempts
        counter = 1
        # list of differences for each round
        diflist = []
        while True:
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                # if it isnt the number, go thru checks
                if int(msg.content) != number:
                    await check_send()
                    counter += 1
                    # difference is absolute value (no negative dif)
                    dif = abs(number - int(msg.content))
                    # add to difference list
                    diflist.append(dif)
                else:
                    # got it correct and tell them
                    dif = int(sum(diflist) / len(diflist))
                    embed = discord.Embed(colour=0x00ff00)
                    embed.set_author(name="You got it!", icon_url=ctx.author.avatar_url)
                    embed.add_field(name=f'Attempts: {counter}', value='\u200B')
                    embed.add_field(name=f'Average Difference: {dif}', value='\u200B')
                    embed.set_footer(text=f"`leaderboard` to show leaders for "
                                          "1k challenge")
                    # if it is 1k challenge then insert into leaderboard
                    if limit == 1000:
                        lb = Leaderboard(ctx)
                        leaderboad = await lb.into_leaderboard(game='guess', record=counter, attempts=counter,
                                                               wrong=None, correct=None, guildid=ctx.guild.id)
                    # otherwise leaderboard is false
                    else:
                        leaderboad = False
                    # if record
                    if leaderboad:
                        embed.description = leaderboad
                    await ctx.send(embed=embed)
                    break
            # timeout error
            except asyncio.TimeoutError:
                await ctx.send(f'You took too long! The number was {number}')
                # insert all their fails into db
                if limit == 1000:
                    lb = Leaderboard(ctx)
                    intolb = await lb.into_leaderboard(game='guess', record=None, attempts=counter,
                                                       wrong=None, correct=None, guildid=ctx.guild.id)
                break


def setup(bot):
    bot.add_cog(Games(bot))
