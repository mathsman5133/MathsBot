from discord.ext import commands
import discord
import webcolors
import asyncio

class Roles:
    def __init__(self, bot):
        self.bot = bot

    async def __error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(error)

    @commands.group(name='colour', alias='color', invoke_without_command=True)
    @commands.guild_only()
    async def _colour(self, ctx):
        pass

    @_colour.command()
    @commands.guild_only()
    async def add(self, ctx, *, colour):
        if not self.bot.get_config(ctx.guild.id, 'allow_colours'):
            return await ctx.send(f'Please enable colours with `colours allow`')

        try:
            rgb = webcolors.name_to_rgb(colour)
        except:
            try:
                rgb = tuple(int(colour.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
            except:
                try:
                    rgb = webcolors.rgb_percent_to_rgb(colour)
                except:
                    try:
                        col = colour.split(',')
                        numbers = []
                        for n in col:
                            try:
                                s = n.replace("(", "")
                                s = s.replace(")", "")
                                int(s)
                                numbers.append(int(s))
                            except:
                                pass
                        tup = tuple(numbers)
                        rgb = webcolors.rgb_to_name(tup)
                        rgb = tup
                    except Exception as e:
                        print(e)
                        raise commands.BadArgument(f"Colour hex, name, RGB or RGB percent {colour} not found.")
        try:
            colourname = webcolors.rgb_to_name(rgb)
            colourhex = webcolors.rgb_to_hex(rgb)
        except:
            colourname = 'No Name'
            colourhex = 'No Hex'
        existing = self.bot.get_colour(ctx.guild.id, rgb)
        if existing:
            role = self.bot.get_role(existing['roleid'])
            return await ctx.author.add_roles(role, reason="MathsBot colour command")
        if self.bot.get_config(ctx.guild.id, 'colour_hoisted'):
            hoist = ctx.me.top_role.position - 1
            desc = f'Role hoisted below {ctx.me.top_role.name}.'
        else:
            hoist = 1
            desc = 'Role not hoisted. To enable hoisting use `colour hoist`'

        try:
            role = await ctx.guild.create_role(name=f"MB: {colourname} - {colourhex} ",
                                               colour=discord.Colour.from_rgb(rgb[0], rgb[1], rgb[2]),
                                               reason=f"New MathsBot colour role: {colourname} - {colourhex}"
                                                      f" by user {ctx.author.display_name}#{ctx.author.discriminator}")
            await role.edit(mentionable=False,
                            position=hoist)
        except:
            raise commands.BotMissingPermissions("I need `manage_roles` permission to do this!")

        e = discord.Embed(colour=discord.Colour.from_rgb(rgb[0], rgb[1], rgb[2]))
        e.description = f'Colour: {colourname}\n' \
                        f'Hex: {colourhex}\n' \
                        f'RGB: {rgb}\n'\
                        f'{desc}'
        e.set_footer(text="If you want colours hoisted higher/lower, change my top role hoisting "
                          "and run `colour refresh`")
        await ctx.send(embed=e)
        await asyncio.sleep(1)
        await ctx.author.add_roles(role, reason="MathsBot colour command")

    @_colour.command()
    @commands.guild_only()
    async def remove(self, ctx, colour: str):
        try:
            rgb = webcolors.name_to_rgb(colour)[0]
        except:
            try:
                rgb = webcolors.hex_to_rgb(colour)
            except:
                try:
                    rgb = webcolors.rgb_percent_to_rgb(colour)
                except:
                    try:
                        rgb = webcolors.rgb_to_name(colour)
                        rgb = colour
                    except:
                        raise commands.BadArgument("Colour hex, name, RGB or RGB percent not found.")


def setup(bot):
    bot.add_cog(Roles(bot))
