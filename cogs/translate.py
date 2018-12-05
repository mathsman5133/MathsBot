import discord
from discord.ext import commands
from googletrans import Translator, LANGUAGES
import functools

class Translation:
    def __init__(self, bot):
        self.bot = bot
        self.codes = LANGUAGES

    def translate_text(self, source=None, dest=None, text=None):
        print(source)
        if dest is None:
            dest = 'en'
        if not source:
            print(Translator().translate(text=text, dest=dest))
            return Translator().translate(text, dest=dest)
        return Translator().translate(text, dest=dest)

    @commands.command(aliases=['tr'])
    async def translate(self, ctx, dest, *text):
        try:
            self.codes[dest]
        except:
            raise commands.BadArgument('That wasnt a correct language code!')
        fctn = functools.partial(self.translate_text, None, dest, text)
        translated = await self.bot.loop.run_in_executor(None, fctn)
        await ctx.send(translated)







def setup(bot):
    bot.add_cog(Translation(bot))