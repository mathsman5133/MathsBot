import discord
from discord.ext import commands
import asyncio

class Admin:
    @commands.command()
    async def load(self, ctx, *, module):
        """Load a cog/extension. Available cogs to reload: `ClaimCommands`, `PlayerCommands`, `ClanCommands`, `DownloadCommands`, `DatabaseCommands`.
                PARAMETERS: [extension name]
                EXAMPLE: `load DownloadCommands`
                RESULT: Loads commands: dl and stopdl. These will now work. Returns result"""
        try:
            self.bot.load_extension(module)
        except Exception as e:
            await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @commands.command()
    async def unload(self, ctx, *, module):
        """Unloads a cog/extension. Available cogs to unload: `ClaimCommands`, `PlayerCommands`, `ClanCommands`, `DownloadCommands`.
                PARAMETERS: [extension name]
                EXAMPLE: `unload DownloadCommands`
                RESULT: Unloads commands: dl and stopdl. These will now not work. Returns result"""
        try:
            self.bot.unload_extension(module)
        except Exception as e:
            await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        else:
            await ctx.send('\N{OK HAND SIGN}')

