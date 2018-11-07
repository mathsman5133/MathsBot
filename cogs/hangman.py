from discord.ext import commands
import discord
import re
import random
from cogs.games import Leaderboard
import os

db_path = os.path.join(os.getcwd(), 'cogs', 'utils', 'database.db')

# phrases i copied from somewhere. need to find more/new/dif ones too
phrases = [
    'Eat My Hat', 'Par For the Course', 'Raining Cats and Dogs', 'Roll With the Punches', 'Curiosity Killed The Cat',
    'Man of Few Words', 'Cry Over Spilt Milk', 'Scot-free', 'Rain on Your Parade', 'Go For Broke', 'Shot In the Dark',
    'Mountain Out of a Molehill', 'Jaws of Death', 'A Dime a Dozen', 'Jig Is Up', 'Elvis Has Left The Building',
    'Wake Up Call', 'Jumping the Gun', 'Up In Arms', 'Beating Around the Bush', 'Flea Market', 'Playing For Keeps',
    'Cut To The Chase', 'Fight Fire With Fire', 'Keep Your Shirt On', 'Poke Fun At', 'Everything But The Kitchen Sink',
    'Jaws of Life', 'What Goes Up Must Come Down', 'Give a Man a Fish', 'Plot Thickens - The',
    'Not the Sharpest Tool in the Shed', 'Needle In a Haystack', 'Right Off the Bat', 'Throw In the Towel',
    'Down To Earth', 'Lickety Split', 'I Smell a Rat', 'Long In The Tooth', "You Can't Teach an Old Dog New Tricks",
    'Back To the Drawing Board', 'Down For The Count', 'On the Same Page', 'Under Your Nose', 'Cut The Mustard',
    "If You Can't Stand the Heat, Get Out of the Kitchen", 'Knock Your Socks Off', 'Playing Possum', 'No-Brainer',
    "Money Doesn't Grow On Trees", 'In a Pickle', 'In the Red', 'Fit as a Fiddle', 'Hear, Hear', 'Hands Down',
    "Off One's Base", 'Wild Goose Chase', 'Keep Your Eyes Peeled', 'A Piece of Cake', 'Foaming At The Mouth',
    'Go Out On a Limb', 'Quick and Dirty', 'Hit Below The Belt', 'Birds of a Feather Flock Together',
    "Wouldn't Harm a Fly", 'Son of a Gun', 'Between a Rock and a Hard Place', 'Down And Out', 'Cup Of Joe',
    'Down To The Wire', "Don't Look a Gift Horse In The Mouth", 'Talk the Talk', 'Close But No Cigar',
    'Jack of All Trades Master of None', 'High And Dry', 'A Fool and His Money are Soon Parted',
    'Every Cloud Has a Silver Lining', 'Tough It Out', 'Under the Weather', 'Happy as a Clam', 'An Arm and a Leg',
    "Read 'Em and Weep", 'Right Out of the Gate', 'Know the Ropes', "It's Not All It's Cracked Up To Be",
    'On the Ropes', 'Burst Your Bubble', 'Mouth-watering', 'Swinging For the Fences', "Fool's Gold", 'On Cloud Nine',
    'Fish Out Of Water', 'Ring Any Bells?', "There's No I in Team", 'Ride Him, Cowboy!', 'Top Drawer',
    'No Ifs, Ands, or Buts', "You Can't Judge a Book By Its Cover", "Don't Count Your Chickens Before They Hatch",
    'Cry Wolf', 'Beating a Dead Horse', 'Goody Two-Shoes', 'Heads Up', 'Drawing a Blank', "Keep On Truckin'",
    'Tug of War', 'Short End of the Stick', 'Hard Pill to Swallow', 'Back to Square One', 'Love Birds',
    'Dropping Like Flies', 'Break The Ice', 'Knuckle Down', 'Lovey Dovey', 'Greased Lightning', 'Let Her Rip',
    'All Greek To Me', 'Two Down, One to Go', 'What Am I, Chopped Liver?', "It's Not Brain Surgery",
    'Like Father Like Son', 'Easy As Pie', 'Elephant in the Room', 'Quick On the Draw', 'Barking Up The Wrong Tree',
    'A Chip on Your Shoulder', 'Put a Sock In It', 'Quality Time', 'Yada Yada', 'Head Over Heels', 'My Cup of Tea',
    'Ugly Duckling', 'Drive Me Nuts', 'When the Rubber Hits the Road', 'A penny for your thoughts',
    'A picture is worth a thousand words', 'A plague on both your houses', 'A red rag to a bull',
    'A rolling stone gathers no moss', 'A sight for sore eyes', "Beggars can't be choosers", 'Behind the eight ball',
    'Bells and whistles', 'Bet your bottom dollar', 'Better late than never', 'Bang for your buck',
    'Big fish in a small pond', 'Blow your own trumpet', 'Blown to smithereens', "Bob's your uncle",
    'Too big for your boots', 'Break the ice', 'Break a leg', "If it ain't broke, don't fix it",
    'Burn the candle at both ends', 'Burning the midnight oil', 'Cat got your tongue?', 'Chalk and cheese',
    'Cheap at half the price', 'Children should be seen and not heard', 'Climb on the bandwagon',
    'Cool as a cucumber', 'Cost an arm and a leg', 'Counting sheep', "Dog's breakfast", "Double whammy",
    'Dropping like flies', 'Eeny, meeny, miny, mo', 'Even at the turning of the tide', 'Everybody out',
    'Faff about', 'Face the music', 'Fair dinkum', 'Famous last words', 'Fight fire with fire',
    'Filthy rich', 'Finger lickin good', "As fit as a butcher's dog", 'For whom the bell tolls', 'Forbidden fruit',
    'Higgledy-piggledy', 'Hit the ground running', 'Hit the nail on the head', 'Hit the hay', 'Hunky-dory',
    'I will wear my heart upon my sleeve', 'In a nutshell', "In the bad books", 'Jump the gun',
    'Jump on the bandwagon', 'Keep your chin up', 'Keep your distance', 'Let sleeping dogs lie',
    'Let the cat out of the bag', 'Let them eat cake', 'Let there be light', 'Let your hair down',
    'Okey-dokey', 'Old as Methuselah', 'Old as the hills', 'The jury is still out', 'Zig-zag'

]


class Game:
    def __init__(self, word):
        # setup attributes for the start of a game
        self.attempts = 0
        self.word = word
        self.blanks = ''.join((letter if (not re.search('[a-zA-Z0-9]', letter)) else '_' for letter in word))
        self.failed_letters = []
        self.guessed_letters = []
        self.fails = 0

    def guess_letter(self, letter):
        # +1 to total attempts
        self.attempts += 1
        # add letter to guesses
        self.guessed_letters.append(letter)
        # if its in word
        if letter.lower() in self.word.lower():
            # change letter in word from _ to the letter
            self.blanks = ''.join((word_letter if letter.lower() == word_letter.lower() else self.blanks[i]
                                   for (i, word_letter) in enumerate(self.word)))
            return True
        else:
            # increase fails
            self.fails += 1
            # add to failed letters (what comes up as guesses)
            self.failed_letters.append(letter)
            return False

    def guess_word(self, word):
        # add one to total attempts
        self.attempts += 1
        # if its a match
        if word.lower() == self.word.lower():
            # change blanks to reflect word
            self.blanks = self.word
            return True
        else:
            # increase fails
            self.fails += 1
            return False

    def win(self):
        # if guessed blanks/letters = word
        return self.word == self.blanks

    def failed(self):
        # 7 attempts means the dudes leg is on and game over
        return self.fails == 7

    def __str__(self):
        # idk how this formatting works
        man = '     ——\n'
        man += '    |  |\n'
        man += '    {}  |\n'.format('o' if self.fails > 0 else ' ')
        man += '   {}{}{} |\n'.format('/' if self.fails > 1 else ' ', '|' if self.fails > 2 else ' ', '\\'
                                      if self.fails > 3 else ' ')
        man += '    {}  |\n'.format('|' if self.fails > 4 else ' ')  # This converts everything but spaces to a blank
        man += '   {} {} |\n'.format('/' if self.fails > 5 else ' ', '\\' if self.fails > 6 else ' ')
        man += '       |\n'
        man += '    ———————\n'
        fmt = '```\n{}```'.format(man)
        fmt += '```\nGuesses: {}\nWord: {}```'.format(', '.join(self.failed_letters), ' '.join(self.blanks))
        return fmt


class Hangman:
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

    def create_game(self, word, ctx):
        # make a game
        game = Game(word)
        self.games[ctx.author.id] = game
        # add game to list of games with author id
        return game

    @commands.group(invoke_without_command=True, aliases=['hm'])
    async def hangman(self, ctx, *, guess):
        """Makes a guess on your currently running hangman game.
            PARAMETERS: [a guess] - letter or phrase
            EXAMPLE: `hangman a` or `hangman My Little Pony`
            RESULT: Guesses the letter `A` or the phrase `My Little Pony`"""
        game = self.games.get(ctx.author.id)
        embed = discord.Embed()
        # no game running
        if not game:
            embed.colour = 0x0000ff
            embed.set_author(name='There are currently no hangman games running!', icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
            return
        # if its a letter
        if len(guess) == 1:
            # letter already guessed
            if guess in game.guessed_letters:
                embed.set_author(name='That letter has already been guessed!', icon_url=ctx.author.avatar_url)
                embed.colour = 0x0000ff
                await ctx.send(embed=embed)
                return
            if game.guess_letter(guess):  # Here's our fancy formatting for the hangman picture
                embed.colour = 0x00ff00
                embed.set_author(name="That's correct!", icon_url=ctx.author.avatar_url)
                # Each position in the hangman picture is either a space,
                # or part of the man, based on how many fails there are
            else:
                embed.colour = 0xff0000
                embed.set_author(name='Sorry, that letter is not in the phrase......Keep guessing though!', icon_url=ctx.author.avatar_url)
        elif game.guess_word(guess):
            embed.colour = 0x00ff00
            # keep the embed wide so formatting isnt shitty
            embed.set_author(name="That's correct! Now go try another....................", icon_url=ctx.author.avatar_url)
        else:
            embed.colour = 0xff0000
            embed.set_author(name="Sorry that's not the correct phrase......Keep guessing though!", icon_url=ctx.author.avatar_url)
        # you win the game
        if game.win():
            embed.colour = 0x00ff00
            embed.set_author(name=f' You got it! The word was `{game.word}`'
                                  f'. It only took you {game.attempts} attempts!',
                             icon_url=ctx.author.avatar_url)
            # run it through leaderboard class - checks if record, first time etc and responds accordingly,
            # adds attempts and fails etc too
            lb = Leaderboard(ctx)
            intolb = await lb.into_leaderboard(game='hangman', record=game.attempts, attempts=game.attempts,
                                               wrong=game.fails, correct=1, guildid=ctx.guild.id)
            # if it returned something (first time or record)
            if intolb:
                embed.description = intolb
            # remove the game assosiated to id
            del self.games[ctx.author.id]
        # you lose the game
        elif game.failed():
            embed.colour = 0xff0000
            embed.set_author(name=f' Sorry, you failed...the word was `'
                                  f'{game.word}`. It took you {game.attempts} attempts',
                             icon_url=ctx.author.avatar_url)
            # run it through leaderboard class - checks if record, first time etc and responds accordingly
            # adds attempts and fails etc too

            lb = Leaderboard(ctx)
            intolb = await lb.into_leaderboard(game='hangman', record=game.attempts, attempts=game.attempts,
                                               wrong=game.fails, correct=1, guildid=ctx.guild.id)
            # if it returned something (first game or record)
            if intolb:
                embed.description = intolb
            # delete game assosiated with author
            del self.games[ctx.author.id]
        else:
            # otherwise let embed description be the fancy hangman formatting
            embed.description = str(game)

        await ctx.send(embed=embed)

    @hangman.command(aliases=['start'], no_pm=True)
    async def create(self, ctx):
        """Create a new hangman game. A random phrase will be selected.
            PARAMETERS: None
            EXAMPLE: `hangmancreate` or `hmstart`
            RESULT: Creates a new hangman game"""
        embed = discord.Embed()
        # if already a game assosiated with author id
        if self.games.get(ctx.author.id) is not None:
            embed.colour = 0xff0000
            embed.set_author(name='Sorry but only one Hangman game can be running per person!',
                             icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
            return
        # Create a new game, then save it as the server's game
        game = self.create_game(random.SystemRandom().choice(phrases), ctx)
        embed.colour = 0x00ff00
        embed.set_author(name='Alright, a hangman game has just started, you can start guessing now!',
                         icon_url=ctx.author.avatar_url)
        # description is fancy hangman formatting
        embed.description = str(game)
        await ctx.send(embed=embed)

    @hangman.command(aliases=['stop', 'remove', 'end'], no_pm=True)
    async def delete(self, ctx):
        """Deletes your currently running game of hangman
            PARAMETERS: None
            EXAMPLE: `hangman delete` or `hmstop`
            RESULT: Deletes current game"""
        embed = discord.Embed()
        # if no games currently running
        if self.games.get(ctx.author.id) is None:
            embed.colour = 0xff0000
            embed.set_author(name='You currently have no Hangman games running!',
                             icon_url=ctx.author.avatar_url)

            await ctx.send(embed=embed)
            return
        # delete the game assosiated to author id
        del self.games[ctx.author.id]
        embed.colour = 0x00ff00
        embed.set_author(name='I have just stopped the game of Hangman, '
                              'a new should be able to be started now!',
                         icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Hangman(bot))
