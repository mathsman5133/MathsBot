from discord.ext import commands
import asyncio
import discord
import random
import time
from cogs.leaderboard import Leaderboard
from cogs.utils import db


class ClashTrivia(db.Table, table_name='clash_trivia'):
    id = db.PrimaryKeyColumn()

    category = db.Column(db.String)
    question = db.Column(db.String)
    answers = db.Column(db.String)
    correct = db.Column(db.String)
    explanation = db.Column(db.String)
    icon_url = db.Column(db.String)


class TriviaQuestions(db.Table, table_name='trivia'):
    id = db.PrimaryKeyColumn()

    category = db.Column(db.String)
    difficulty = db.Column(db.String)
    question = db.Column(db.String)
    answers = db.Column(db.String)
    correct = db.Column(db.String)
    used = db.Column(db.Integer, default=0)


class Games:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def clashtrivia(self, ctx, *people_to_play: discord.Member):
        """Play a game of clash of clans trivia with friends and/or yourself

        PARAMETERS: optional: [ping friends to play] - play a multiplayer game with friends
        EXAMPLE: `clashtrivia` or `clashtrivia @friend1 @friend2 @friend3`
        RESULT: Initiates a COC trivia game with yourself or with friends 1, 2, 3 and yourself"""
        info = {ctx.author.id: {"user": ctx.author,
                                "attempts": 0,
                                "correct": 0,
                                "turn": 0}}
        for user in people_to_play:
            info[user.id] = {"user": user,
                             "attempts": 0,
                             "correct": 0,
                             "turn": 0}

        current_turn_id = 0

        def check(ctx):
            if (ctx is None) or (ctx.author.id != current_turn_id):
                return False
            if ctx.content.lower() in ['a', 'b', 'c', 'd']:
                return True
            else:
                return False

        query = """SELECT * FROM clash_trivia ORDER BY RANDOM() LIMIT $1
                """
        questions = await self.bot.pool.fetch(query, len(info) * 5)

        # async with aiosqlite.connect(db_path) as db:
        #     c = await db.execute("SELECT * FROM clash_trivia ORDER BY RANDOM() LIMIT :lim",
        #                          {'lim': len(info) * 5})
        #     questions = await c.fetchall()

        def turn():
            for entry in info:
                if info[entry]['turn'] == 0:
                    info[entry]['turn'] = 1
                    return info[entry]
            for entry in info:
                info[entry]['turn'] = 0
            for entry in info:
                return info[entry]

        for trivia in questions:
            user = turn()
            current_turn_id = user['user'].id
            e = discord.Embed(colour=discord.Colour.blue())
            e.set_author(name=f"{user['user'].display_name}#{user['user'].discriminator}'s turn",
                         icon_url=user['user'].avatar_url)
            e.set_thumbnail(url=trivia['icon_url'])
            e.title = trivia['question']
            e.description = trivia['answers']
            e.set_footer(text="Multiple Choice! Type the letter of the answer you think it is.")
            send = await ctx.send(embed=e)
            while True:
                info[user['user'].id]['attempts'] += 1
                try:
                    # wait for a response which satisfies our check function
                    msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                    e = discord.Embed()
                    e.add_field(name="Explanation", value=trivia[5])

                    if msg.content.lower() == trivia['correct'].lower():
                        info[user['user'].id]['correct'] += 1

                        e.colour = discord.Colour.green()
                        e.set_author(name="Correct!", icon_url=user['user'].avatar_url)

                    else:
                        e.colour = discord.Colour.red()
                        e.set_author(name="Incorrect!", icon_url=user['user'].avatar_url)

                    uuser = info[user['user'].id]

                    e.description = f"You are currently {uuser['correct']}/{uuser['attempts']}"
                    await send.edit(embed=e)
                    break
                except asyncio.TimeoutError:
                    embed = discord.Embed(colour=0xff0000)
                    embed.set_author(name="You took too long. Your turn has been skipped!",
                                     icon_url=user['user'].avatar_url)
                    await send.edit(embed=embed)
                    if len(info) == 1:
                        return
                    break

        e = discord.Embed(colour=discord.Colour.green())
        for user in info:
            base = info[user]
            lb = Leaderboard(ctx)
            intolb = await lb.into_leaderboard(game='clashtrivia', record="N/A",
                                               attempts=base['attempts'],
                                               wrong=base['attempts'] - base['correct'],
                                               correct=base['correct'],
                                               guildid=ctx.guild.id,
                                               id=base['user'].id)
            e.add_field(name=f"{base['user'].display_name}#{base['user'].discriminator}:",
                        value=f"{base['correct']}/{base['attempts']}\n"
                              f"{intolb or ''}",
                        inline=False)
        e.add_field(name="\u200b",
                    value="Thanks for playing!\n"
                          "Check the leaderboard for updated standings!",
                    inline=False)
        e.set_author(name="Game Over; y'all made it!",
                     icon_url=ctx.author.avatar_url)
        e.set_footer(text="Images and explanations courtesy of Clash of Clans Wiki. ",
                     icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=e)

    async def trivia_category(self, ctx, difficulty_topic, limit):
        # return question with category or difficulty for trivia games

        # if msg content is easy, med, hard then look for that:
        if difficulty_topic in ['easy', 'medium', 'hard']:
            query = """SELECT * FROM trivia WHERE used = $1 AND difficulty = $2"
                       ORDER BY RANDOM() LIMIT $3
                       """
            return await self.bot.pool.fetch(query, 0, difficulty_topic, limit)

            # async with aiosqlite.connect(db_path) as db:
            #     c = await db.execute("SELECT * FROM trivia WHERE used = 0 AND difficulty = :dif"
            #                          " ORDER BY RANDOM() LIMIT :lim",
            #                          {'dif': difficulty_topic,
            #                           'lim': limit})
            #     # return 10 questions with difficulty specified
            #     return await c.fetchall()

        # if no topic then get 10 random ones
        if difficulty_topic == 'all':
            query = """SELECT * FROM trivia WHERE used = $1 ORDER BY RANDOM() LIMIT $2
                    """
            return await self.bot.pool.fetch(query, 0, limit)
            # async with aiosqlite.connect(db_path) as db:
            #     c = await db.execute("SELECT * FROM trivia WHERE used = 0 ORDER BY RANDOM() LIMIT :lim",
            #                          {'lim': limit})
            #     return await c.fetchall()

        # if it is 'categories' then they want to know what categories available
        else:
            if difficulty_topic == 'categories':
                # async with aiosqlite.connect(db_path) as db:
                #
                #     c = await db.execute("SELECT category FROM trivia")
                #     # unique ones as a list
                #     dump = list(set(await c.fetchall()))
                #     # send them
                #
                # get all categories for all questions
                query = """SELECT category FROM trivia
                        """
                dump = list(set(await self.bot.pool.fetch(query)))
                desc = '\n'.join(n[0] for n in dump)

                e = discord.Embed(colour=0x00ff00)
                e.set_author(name="Categories for trivia games", icon_url=ctx.author.avatar_url)
                e.add_field(name='\u200b', value=desc)
                e.set_footer(text=f"Type `{ctx.prefix}trivia [category]` to get a trivia game of that category!",
                             icon_url=self.bot.user.avatar_url)

                await ctx.send(embed=e)
                # return False
                return False
            # otherwise get 10 questions with that category
            query = """
                    SELECT * FROM trivia WHERE used = $1
                    AND category = $2 ORDER BY RANDOM() LIMIT $3
                    """
            return await self.bot.pool.fetch(query, 0, difficulty_topic, limit)

            # async with aiosqlite.connect(db_path) as db:
            #     c = await db.execute("SELECT * FROM trivia WHERE used = 0 AND category = :cat"
            #                          " ORDER BY RANDOM() LIMIT :lim",
            #                          {'cat': difficulty_topic,
            #                           'lim': limit})
            #     # return results (could be none)
            #     return await c.fetchall()

    @commands.group(name="trivia", invoke_without_command=True)
    async def _trivia(self, ctx, *, difficulty_or_topic: str=None):
        """
        Group: Play a trivia game with friends and/or yourself, or find available catagories.
        Invoke without a command to play solo

        PARAMETERS: optional: [difficulty or topic]
        EXAMPLE: `trivia easy` or `trivia Politics`
        RESULT: Initiates an easy game of trivia or one with the topic Politics
        """
        cmd = self.bot.get_command("trivia solo")
        await cmd.invoke(ctx=ctx)

    @_trivia.command(aliases=['category'])
    async def categories(self, ctx):
        """
        Find available categories for a trivia game

        PARAMETERS: None
        EXAMPLE: `trivia categories`
        RESULT: Returns available trivia categories to select from
        """
        send = await self.trivia_category(ctx, 'categories', 10)
        if send:
            e = discord.Embed(colour=0xff0000)
            e.set_author(name="Category not found", icon_url=ctx.author.avatar_url)
            e.description = f'Find all categories with {ctx.prefix}trivia categories. ' \
                            'Difficulties are: easy, medium, hard.'
            await ctx.send(embed=e)

    @_trivia.command()
    async def solo(self, ctx, *, difficulty_or_topic: str = None):
        """
        Start a game of trivia with yourself. Select the difficulty or topic.
        There is 10 questions and I will timeout after 15 seconds

        PARAMETERS: optional: [difficulty or topic] - easy, medium, hard, or any topic found with `trivia categories`
        EXAMPLE: `trivia solo easy` or `trivia solo Politics`
        RESULT: Initiates an easy game of trivia or one with the topic Politics
        """
        if not difficulty_or_topic:
            difficulty_or_topic = 'all'
        dump = await self.trivia_category(ctx, difficulty_or_topic, 10)
        # if I sent a category list:
        if dump is False:
            return

        # if category not found
        if len(dump) == 0:
            embed = discord.Embed(colour=0xff0000)
            embed.set_author(name="Category not found", icon_url=ctx.author.avatar_url)
            embed.description = f'Find all categories with {ctx.prefix}trivia categories. ' \
                                'Difficulties are: easy, medium, hard.'
            return await ctx.send(embed=embed)


        correct = 0
        attempts = 0

        # otherwise:

        def check(user):
            # same check as clash trivia
            if (user is None) or (user.author.id != ctx.author.id):
                return False
            else:
                if user.content.lower() in ['a', 'b', 'c', 'd']:
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

                    query = "UPDATE trivia SET used = 1 WHERE id = $1"
                    await self.bot.pool.execute(query, trivia[0])

                    # async with aiosqlite.connect(db_path) as db:
                    #     await db.execute("UPDATE trivia SET used = 1 WHERE id = :id",
                    #                      {'id': trivia[0]})
                    #     await db.commit()

                    if msg.content.lower() == trivia[4][0].lower():
                        correct += 1
                        embed.colour = discord.Colour.green()
                        embed.set_author(name="Correct!", icon_url=ctx.message.author.avatar_url)

                    else:
                        embed.colour = discord.Colour.red()
                        embed.set_author(name="Incorrect!", icon_url=ctx.message.author.avatar_url)

                    embed.title = trivia[3]
                    embed.description = trivia[5]
                    embed.add_field(name="Correct Answer:", value=trivia[4])
                    embed.add_field(name='\u200b',
                                    value=f'You are currently {correct}/{attempts}',
                                    inline=False)
                    await send.edit(embed=embed)
                    break

                except asyncio.TimeoutError:
                    e = discord.Embed(colour=0xff0000)
                    e.set_author(name="You took too long! Game over", icon_url=ctx.author.avatar_url)
                    await send.edit(embed=e)
                    return

        lb = Leaderboard(self.bot)
        intolb = await lb.into_leaderboard(game='trivia', record="N/A",
                                           attempts=attempts,
                                           wrong=attempts - correct,
                                           correct=correct,
                                           guildid=ctx.guild.id,
                                           id=ctx.author.id)

        e = discord.Embed(colour=0x00ff00)

        if intolb:
            e.description = intolb

        e.set_author(name="Game Over!", icon_url=ctx.author.avatar_url)
        e.add_field(name="\u200b",
                    value=f"You got {correct}/{attempts} "
                          f"({round(correct/attempts, 2)*100}%)")
        e.add_field(name='\u200b',
                    value="Thanks for playing\n"
                          "Check the leaderboard for updated standings!")

        await ctx.send(embed=e)

    @_trivia.command()
    async def game(self, ctx, difficulty_topic, *people_to_play: discord.Member):
        """Start a trivia game with multiple friend(s)! Specify the difficulty or topic.
        There are 10 questions each; your turn will be skipped if you do not respond within 15 seconds.

        PARAMETERS: [difficulty or topic] [@mention friends]. If difficulty or topic is more than 1 word, you MUST surround it in " ".`
        EXAMPLE: `trivia game all @friend1` or `trivia game "General Knowledge" @friend1 @friend2 @friend3`
        RESULT: Starts a trivia game with friend 1, or a trivia game with friends 1, 2 and 3 and category General Knowledge
        """

        member = await commands.MemberConverter().convert(ctx, difficulty_topic)

        if member:
            difficulty_topic = 'all'

        dump = await self.trivia_category(ctx, difficulty_topic, (len(people_to_play) + 1)*2)
        if dump is False:
            return
        # if category not found
        if len(dump) == 0:
            embed = discord.Embed(colour=0xff0000)
            embed.set_author(name="Category not found", icon_url=ctx.author.avatar_url)
            embed.description = f'Find all categories with `{ctx.prefix}trivia categories` command. ' \
                                'Difficulties are: easy, medium, hard.'
            await ctx.send(embed=embed)
            return

        info = {ctx.author.id: {"user": ctx.author,
                                "attempts": 0,
                                "correct": 0,
                                "turn": 0}}

        for user in people_to_play:
            info[user.id] = {"user": user,
                             "attempts": 0,
                             "correct": 0,
                             "turn": 0}
        if member:
            info[member.id] = {"user": member,
                               "attempts": 0,
                               "correct": 0,
                               "turn": 0}

        current_turn_id = 0

        def check(ctx):
            if (ctx is None) or (ctx.author.id != current_turn_id):
                return False
            if ctx.content.lower() in ['a', 'b', 'c', 'd']:
                return True
            else:
                return False

        def turn():
            for entry in info:
                if info[entry]['turn'] == 0:
                    info[entry]['turn'] = 1
                    return info[entry]
            for entry in info:
                info[entry]['turn'] = 0
            for entry in info:
                return info[entry]

        for trivia in dump:
            user = turn()
            current_turn_id = user['user'].id

            embed = discord.Embed(colour=0x0000ff)
            embed.set_author(name=f"{user['user'].display_name}#{user['user'].discriminator}'s Turn!",
                             icon_url=user['user'].avatar_url)
            embed.title = trivia[3]
            embed.set_thumbnail(url=user['user'].avatar_url)
            embed.description = trivia[5]
            embed.set_footer(text="Multiple Choice! Type the letter of the answer you think it is.")
            await ctx.send(embed=embed)

            while True:
                info[user['user'].id]['attempts'] += 1

                try:
                    msg = await self.bot.wait_for('message', check=check, timeout=15.0)

                    embed.title = trivia[3]
                    embed.description = trivia[5]
                    embed.add_field(name="Correct Answer:", value=trivia[4], inline=False)

                    query = "UPDATE trivia SET used = 1 WHERE id = $1"
                    await self.bot.pool.execute(query, trivia[0])

                    # async with aiosqlite.connect(db_path) as db:
                    #     await db.execute("UPDATE trivia SET used = 1 WHERE id = :id",
                    #                      {'id': trivia[0]})
                    #     await db.commit()

                    if msg.content.lower() == trivia[4].lower():
                        info[user['user'].id]['correct'] += 1

                        embed.colour = discord.Colour.green()
                        embed.set_author(name="Correct!", icon_url=user['user'].avatar_url)

                    else:
                        embed.colour = discord.Colour.red()
                        embed.set_author(name="Incorrect!", icon_url=user['user'].avatar_url)

                    uuser = info[user['user'].id]

                    embed.add_field(name='\u200b',
                                    value=f"You are currently {uuser['correct']}/{uuser['attempts']}")
                    await ctx.send(embed=embed)
                    break

                except asyncio.TimeoutError:
                    embed = discord.Embed(colour=0xff0000)
                    embed.set_author(name="You took too long. Your turn has been skipped!",
                                     icon_url=user['user'].avatar_url)
                    await ctx.send(embed=embed)
                    break

        def winner():
            to_beat_score = 0
            to_beat_user = ''
            for entry in info:
                if info[entry]['correct'] >= to_beat_score:
                    to_beat_score = info[entry]['correct']
                    to_beat_user = info[entry]['user']
            return to_beat_user

        winner = winner()

        e = discord.Embed(colour=0x00ff00)
        e.set_author(name=f"Game Over! {winner.display_name}#{winner.discriminator} is the Winner!",
                     icon_url=winner.avatar_url)
        e.set_thumbnail(url=winner.avatar_url)

        for user in info:
            base = info[user]
            lb = Leaderboard(ctx)
            intolb = await lb.into_leaderboard(game='trivia', record="N/A",
                                               attempts=base['attempts'],
                                               wrong=base['attempts'] - base['correct'],
                                               correct=base['correct'],
                                               guildid=ctx.guild.id,
                                               id=base['user'].id)

            e.add_field(name=f"{base['user'].display_name}#{base['user'].discriminator}:",
                        value=f"{base['correct']}/{base['attempts']}\n"
                              f"{intolb or ''}",
                        inline=False)

        e.add_field(name="\u200b",
                    value="Thanks for playing!\n"
                          "Check the leaderboard for updated standings!",
                    inline=False)

        await ctx.send(embed=e)

    @commands.command()
    async def reacttest(self, ctx):
        """
        Test you reaction speed! Hit the emoji when the embed turns green

        PARAMETERS: None
        EXAMPLE: `reacttest`
        RESULT: Wait for the embed to turn green and whack the emoji
        """

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
        while True:
            try:
                # wait for check. timeout is random delay time. If check returns true then they cheated
                await self.bot.wait_for('reaction_add', check=check, timeout=delaytime)
                e = discord.Embed(colour=0xff0000)
                e.set_author(name="No Cheating!",
                             icon_url='https://cdn.shopify.com/s/files/1/1061/1924/products/'
                                      'Very_Angry_Emoji_7f7bb8df-d9dc-4cda-b79f-5453e764d4ea_large.png?v=1480481058')
                await send.edit(embed=embed)
                # insert into leaderboard that they cheated
                lb = Leaderboard(self.bot)
                await lb.into_leaderboard(game='reacttest', record=3,
                                          attempts=1, wrong="N/A",
                                          correct="N/A", guildid=ctx.guild.id,
                                          id=ctx.author.id)
                return
                # end game
            except asyncio.TimeoutError:
                break
                # continue
        e = discord.Embed(colour=0x00ff00)
        e.set_author(name="GO!", icon_url=ctx.author.avatar_url)
        # start timer
        start = time.perf_counter()
        await send.edit(embed=e)
        while True:
            try:
                # wait for reaction add. timeout 3 seconds
                await self.bot.wait_for('reaction_add', check=check, timeout=3.0)
                # finish timer
                end = time.perf_counter()
                # subtract bot latency coz that's not fair to factor in my slowness.
                # still has delay from when start to finish check which is apparantly for some a lot and annoying
                dif = round((end - start - self.bot.latency), 4)
                # didnt cheat
                # insert into leaderboard stuff

                lb = Leaderboard(self.bot)
                leader = await lb.into_leaderboard(game='reacttest', record=round(dif, 4),
                                                   attempts=1, wrong="N/A",
                                                   correct="N/A", guildid=ctx.guild.id,
                                                   id=ctx.author.id)

                # reaction time
                desc = f'**{dif}** seconds'
                # if leaderboard returned (a record)
                if leader:
                    desc += f'\n{leader}'

                e = discord.Embed(colour=0x0000ff)
                e.set_author(name="Your reaction time is....", icon_url=ctx.author.avatar_url)
                e.description = desc
                # send results
                await send.edit(embed=e)
                break
            # took longer than 3 sec
            except asyncio.TimeoutError:
                e = discord.Embed(colour=0xff0000)
                e.set_author(name="You took too long!", icon_url=ctx.author.avatar_url)
                await send.edit(embed=e)
                break

    @commands.command(name='guess')
    async def guess_number(self, ctx, limit: int=None):
        """
        I choose a number and you have to guess! Default limit is 1000. I will tell you if you are too small or too big.

        PARAMETERS: optional: [limit] - the limit of the range I choose my number
        EXAMPLE: `guess` or `guess 500`
        RESULT: Starts a guessing game with a number between 1000 or 500
        """
        # if limit is not specified set to default 1000. I should just change it to that next to limit hey

        if not limit:
            limit = 1000
        # try:
        #     int(limit)
        # except:
        #     return await ctx.send("Please enter an integer parameter, or none at all (will default to 1000)")

        async def check_send():
            # if its first round dont give them a difference
            if counter == 1:
                dif = "First round. I ain't that stupid"
            else:
                # otherwise give average difference
                dif = int(sum(diflist) / len(diflist))
            # if msg number bigger than actual number

            e = discord.Embed()

            if int(msg.content) >= number:
                e.colour = 0xffa500
                e.set_author(name="Too large!", icon_url=ctx.author.avatar_url)

            else:
                e.colour = 0x0000ff
                e.set_author(name="Too small!", icon_url=ctx.author.avatar_url)

            e.set_footer(text=f"Average difference: {dif}")

            await ctx.send(embed=e)

        def check(user):
            # user is original author
            if (user is None) or (user.author.id != ctx.author.id):
                return False

            try:
                int(user.content)
                return True
            except:
                return False

        # start guessing game
        await ctx.send(f"I have chosen a number between 1 and {str(limit)}. You have 15 seconds to try a "
                       "number before I time out. I will tell you if you are too big or too small")

        number = random.randint(1, limit)  # choose number
        counter = 1
        diflist = []

        while True:
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                # if it isnt the number, go thru checks
                if int(msg.content) != number:

                    diflist.append(abs(number - int(msg.content)))
                    counter += 1

                    await check_send()

                else:

                    dif = int(sum(diflist) / len(diflist))

                    e = discord.Embed(colour=0x00ff00)
                    e.set_author(name="You got it!", icon_url=ctx.author.avatar_url)
                    e.add_field(name=f'Attempts: {counter}', value='\u200B')
                    e.add_field(name=f'Average Difference: {dif}', value='\u200B')
                    e.set_footer(text=f"`{ctx.prefix}leaderboard guess` to show leaders for "
                                      "1k challenge")

                    # if it is 1k challenge then insert into leaderboard
                    if limit == 1000:
                        lb = Leaderboard(self.bot)
                        leaderboard = await lb.into_leaderboard(game='guess', record=counter,
                                                                attempts=counter, wrong='N/A',
                                                                correct='N/A', guildid=ctx.guild.id,
                                                                id=ctx.author.id)

                        if leaderboard:
                            e.description = leaderboard

                    await ctx.send(embed=e)
                    break

            except asyncio.TimeoutError:
                await ctx.send(f'You took too long! The number was {number}')

                if limit == 1000:
                    lb = Leaderboard(self.bot)
                    await lb.into_leaderboard(game='guess', record=500,
                                              attempts=counter, wrong='N/A',
                                              correct='N/A', guildid=ctx.guild.id,
                                              id=ctx.author.id)

                break


def setup(bot):
    bot.add_cog(Games(bot))
