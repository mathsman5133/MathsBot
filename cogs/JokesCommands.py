from discord.ext import commands
import aiosqlite
import random
import discord
import asyncio
import GamesCommands
db_path = 'C:/py/maths-util-bot/database.db'


class Jokes:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def dadjoke(self, ctx, jokeid: str = None):
        """Gives you a dad joke
            PARAMETERS: optional: [joke id] - for getting a previous joke you liked via id.
            EXAMPLE: `dadjoke` or `dadjoke 432`
            RESULT: Shows a random dad-joke or the joke with id `432`"""
        # if no joke id
        if not jokeid:
            # random number b/w 1 and 334 (number of dadjokes) obv before I knew sql rand func
            number = random.randint(1, 344)
            async with aiosqlite.connect(db_path) as db:
                c = await db.execute("SELECT * FROM dadjokes WHERE `unique` = :id", {'id': number})
                dump = await c.fetchall()
        # otherwise get joke with specific id
        else:
            async with aiosqlite.connect(db_path) as db:
                c = await db.execute("SELECT * FROM dadjokes WHERE `id` = :id", {'id': jokeid})
                dump = await c.fetchall()
        embed = discord.Embed(colour=0x00ffff)
        embed.set_author(name=dump[0][0], icon_url=ctx.author.avatar_url)
        embed.set_footer(text=f"Like that dad joke? The ID was: {dump[0][1]}. Powered by https://icanhazdadjoke.com/")
        await ctx.send(embed=embed)

    @commands.command()
    async def joke(self, ctx, *, category: str=None):
        """Gives you a random joke. Can include category - find these with `joke categories`
            PARAMETERS: optional: [category] - a joke with that category
            EXAMPLE: `joke` or `joke Knock Knock`
            RESULT: Random joke or random Knock Knock joke"""
        # if no category get random joke
        if not category:
            async with aiosqlite.connect(db_path) as db:
                c = await db.execute("SELECT * FROM jokes ORDER BY RANDOM() LIMIT 1")
                dump = await c.fetchall()
        # else get joke with category
        else:
            # if they want to know available categories
            if category == 'category':
                async with aiosqlite.connect(db_path) as db:
                    c = await db.execute("SELECT category FROM jokes")
                    dump = list(set(await c.fetchall()))
                    embed = discord.Embed(colour=0x00ff00)
                    embed.set_author(name="Categories for the joke commands", icon_url=ctx.author.avatar_url)
                    desc = ''
                    for cat in dump:
                        desc += cat[0] + '\n'
                    embed.add_field(name='\u200b', value=desc)
                    embed.set_footer(text="Type `.joke [category]` to get a joke of that category!",
                                     icon_url=self.bot.user.avatar_url)
                    await ctx.send(embed=embed)
                    return
            # otherwise get joke with category
            async with aiosqlite.connect(db_path) as db:
                c = await db.execute("SELECT * FROM jokes WHERE category = :cat ORDER BY RANDOM() LIMIT 1",
                                     {'cat': category})
                dump = await c.fetchall()

        # category not found in db (returned nothing)

        if len(dump) == 0:
            embed = discord.Embed(colour=0xff0000)
            embed.set_author(name="Category not found", icon_url=ctx.author.avatar_url)
            embed.description = 'Find all categories with .joke categories command'
            await ctx.send(embed=embed)
            return
        # otherwise post joke
        embed = discord.Embed(colour=0x00ffff)
        embed.set_author(name=f"{dump[0][2]}", icon_url=ctx.author.avatar_url)
        embed.description = dump[0][3]
        embed.set_footer(text=f"Category: {dump[0][1]}, ID: {dump[0][0]}. Like this joke? "
                              f"React with :star: emoji in next 10min to add it to liked jokes!",
                         icon_url=self.bot.user.avatar_url)
        msg = await ctx.send(embed=embed)

        # idk why this is here since jokes are that shitty all over anyways
        def check(reaction, user):
            # check if reacter is author and emoji is star
            return user.id != self.bot.user.id and str(reaction.emoji) == '\N{WHITE MEDIUM STAR}'
        await msg.add_reaction('\N{WHITE MEDIUM STAR}')
        score = 0
        while True:
            try:
                # 10min timeout to get a like for the joke
                reaction = await self.bot.wait_for('reaction_add', check=check, timeout=600)
                score += 1
                print(score)
            except asyncio.TimeoutError:
                # when timeout if it has been liked
                if score > 0:
                    # i dont have a command to get this yet but w/e
                    async with aiosqlite.connect(db_path) as db:
                        await db.execute("INSERT INTO savedjokes VALUES (Null, :cat, :tit, :body, :jokeid, :score)",
                                         {'cat': dump[0][1], 'tit': dump[0][2], 'body': dump[0][3], 'jokeid': dump[0][0],
                                          'score': score})
                        await db.commit()
                    embed = discord.Embed(colour=0x00ff00)
                    embed.set_author(name=f"Joke ID {dump[0][0]} was saved with {score} votes!",
                                     icon_url=self.bot.avatar_url)
                    await ctx.send(embed=embed)
                    break

    @commands.command()
    async def insult(self, ctx, user: discord.Member = None):
        """Insults someone
            PARAMETERS: [user] - @mention, nick#discrim, id
            EXAMPLE: `insult @mathsman`
            RESULT: @mathsman would recieve a gutwrenching insult"""
        # if they didnt ping someone I will insult them
        if not user:
            user = ctx.author
        # get random joke with category 'insult'
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT * FROM jokes WHERE category = 'Insults' "
                                 "AND title = 'Stupid Stuff' ORDER BY RANDOM() LIMIT 1")
            dump = await c.fetchall()
        embed = discord.Embed(colour=0x00ffff)
        embed.set_author(name=f'{user.display_name}#{user.discriminator}, {dump[0][3]}', icon_url=ctx.author.avatar_url)
        embed.set_thumbnail(url=user.avatar_url)
        embed.set_footer(text=f"Category: {dump[0][1]}, ID: {dump[0][0]}. "
                              f"Like this insult? React with :star: emoji in next 10min to add it to liked jokes!",
                         icon_url=self.bot.user.avatar_url)
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('\N{WHITE MEDIUM STAR}')

        #same as joke. insults are pretty trash tbh too
        def check(reaction, user):
            return user.id != self.bot.user.id and str(reaction.emoji) == '\N{WHITE MEDIUM STAR}'

        score = 0
        while True:
            try:
                reaction = await self.bot.wait_for('reaction_add', check=check, timeout=600)
                score += 1
                print(score)
            except asyncio.TimeoutError:
                if score > 0:
                    async with aiosqlite.connect(db_path) as db:
                        await db.execute("INSERT INTO savedjokes VALUES (Null, :cat, :tit, :body, :jokeid, :score)",
                                         {'cat': dump[0][1], 'tit': dump[0][2], 'body': dump[0][3], 'jokeid': dump[0][0],
                                          'score': score})
                        await db.commit()
                    embed = discord.Embed(colour=0x00ff00)
                    embed.set_author(name=f"Insult ID {dump[0][0]} was saved with {score} votes!",
                                     icon_url=ctx.author.avatar_url)
                    await ctx.send(embed=embed)
                    break

    @commands.command()
    async def riddle(self, ctx, number: int=None):
        """Gives you a riddle. You can get a riddle with the id. You have 60sec or can give up with `idk` (no prefix).
            PARAMETERS: optional: [number] - id of a riddle
            EXAMPLE: `riddle` or `riddle 1325`
            RESULT: Gives you a random or number 1325 riddle. You have 60sec to type correct answer (no prefix/command)"""
        counter = 0
        # if no riddle number/id get random riddle
        if not number:
            number = random.randint(1, 1478)
        else:
            number = number
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT * FROM riddles WHERE `unique`=:uni", {'uni':number})
            riddle = await c.fetchall()

        # check if reply is author
        def check(user):
            if (user is None) or (user.author.id != ctx.author.id):
                return False
            else:
                return True
        # send the riddle
        lb = GamesCommands.Leaderboard(ctx)
        embed = discord.Embed(colour=0x00ffff)
        embed.set_author(name=riddle[0][0], icon_url=ctx.author.avatar_url)
        embed.set_footer(text="You have 60 seconds to type the correct answer. If you give up, type `idk`")
        send = await ctx.send(embed=embed)
        while True:
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                # wait for a reply + add to counter (attempts) if reply
                counter += 1
                # if correct
                if msg.content == riddle[0][1]:
                    embed = discord.Embed(colour=0x00ff00)
                    embed.set_author(name="Correct!", icon_url=ctx.author.avatar_url)
                    embed.title = riddle[0][0]
                    embed.description = riddle[0][1]
                    embed.set_footer(text=f"Like this riddle? The number was {riddle[0][2]}. "
                                          f"Type `.riddle {riddle[0][2]}` to get it again, "
                                          f"or save it with `.riddlesave {riddle[0][2]}`")
                    # put into leaderboard
                    intolb = await lb.into_leaderboard(game='riddle', record=counter, attempts=counter,
                                                       wrong=counter - 1, correct=1, guildid=ctx.guild.id)
                    # if there is something them set empty title and response value
                    if intolb:
                        embed.add_field(name='\u200b', value=intolb)
                    await ctx.send(embed=embed)
                    # exit command
                    return
                # if they throw in the towel exit while true
                if msg.content == 'idk':
                    break
                else:
                    # wrong answer
                    await ctx.send("Eh, I don't think it was that. Try again!")
            # timeout
            except asyncio.TimeoutError:
                break
        # give them the answer and insert fails into leaderboard
        embed = discord.Embed(colour=0xff0000)
        embed.set_author(name="The answer was: ")
        embed.title = riddle[0][1]
        embed.set_footer(text=f"Like this riddle? The number was {riddle[0][2]}. "
                              f"Type `.riddle {riddle[0][2]}` to get it again, "
                              f"or save it with `.riddlesave {riddle[0][2]}`", icon_url=ctx.author.avatar_url)
        intolb = await lb.into_leaderboard(game='riddle', record=counter, attempts=counter,
                                           wrong=counter, correct=0, guildid=ctx.guild.id)
        if intolb:
            embed.description = intolb
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Jokes(bot))
