import discord
from discord.ext import commands
import aiosqlite
from cogs.utils import checks
import os
import asyncio
import webcolors
from cogs.actionlog import ChannelConverter
db_path = os.path.join(os.getcwd(), 'cogs', 'utils', 'database.db')

class Announcements:
    def __init__(self, bot):
        self.bot = bot

    async def __error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(error)

    @commands.group(name="notify", invoke_without_command=True)
    @checks.is_mod()
    async def _notify(self, ctx):
        if not ctx.me.guild_permissions.manage_roles:
            return await ctx.send("I don't have `manage_roles` permissions!")
        e = discord.Embed(colour=discord.Colour.green())
        e.set_footer(text="Exit by typing `quit`")
        e.add_field(name="What roles do you want to mention?",
                    value='\u200b')
        await ctx.send(embed=e)

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel
        while True:
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=120)
                roles = await commands.RoleConverter().convert(msg, msg.content)
                break
            except asyncio.TimeoutError:
                return

        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT MAX(notifyid) FROM notify")
            msgno = await c.fetchall()

        fail_roles = ''
        for irole in roles:
            try:
                await irole.edit(mentionable=True, reason=f"Notify message {msgno[0][0] + 1}")
            except discord.Forbidden:
                fail_roles += f'{irole.name}\n'
        if len(fail_roles) != 0:
            await ctx.send(f"I'm missing permissions to edit the following roles: \n{fail_roles}."
                           f" We will continue, but if these roles will not be mentioned (if currently disabled)."
                           f" Type `quit` to restart")

        e.clear_fields()
        e.add_field(name="What channel(s) would you like me to send the message to?",
                    value='\u200b')
        await ctx.send(embed=e)
        while True:
            try:
                msg2 = await self.bot.wait_for('message', check=check, timeout=120)
                if msg2.content.lower() == 'quit':
                    return
                channels = msg2.channel_mentions
                break
            except asyncio.TimeoutError:
                return

        no_perms_channels = ''
        for chan in channels:
            if not chan.permissions_for(ctx.me).send_messages:
                no_perms_channels += f'{chan.mention}\n'
        if len(no_perms_channels) != 0:
            await ctx.send("I'm missing permissions in the following channels: \n{no_perms_channels}."
                           " We will continue, but I need `send_messages` for it to work there.")

        e.clear_fields()
        e.add_field(name="What would you like the message to be?",
                    value='\u200b')
        await ctx.send(embed=e)
        while True:
            try:
                msg2 = await self.bot.wait_for('message', check=check, timeout=600)
                if msg2.content.lower() == 'quit':
                    return
                message = msg2.clean_content
                break
            except asyncio.TimeoutError:
                return

        mtnstring = ' '.join(n.mention for n in roles)
        msg = [await channel.send(f"{mtnstring}\n{message}") for channel in channels]

        for irole in roles:
            try:
                await irole.edit(mentionable=False, reason=f"Notify message {msgno[0][0] + 1}")
            except discord.Forbidden:
                pass

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        async with aiosqlite.connect(db_path) as db:
            for n in msg:
                await db.execute("INSERT INTO notify VALUES (:mid, :aid, :msg, :mno)",
                                 {'mid': n.id, 'aid': ctx.author.id, 'msg': n.clean_content, 'mno': msgno[0][0] + 1})
                await db.commit()
        e.clear_fields()
        e.description = msg
        e.add_field(name="Notify ID",
                    value=msgno[0][0] + 1,
                    inline=False)
        e.add_field(name="Roles Mentioned:",
                    value='\n'.join(n.name for n in roles))
        e.add_field(name="Message IDs",
                    value='\n'.join([str(n.id) for n in msg]),
                    inline=False)

        e.set_footer(text=f"Edit these messages with `notify edit {msgno[0][0] + 1} [new_msg]`")
        user = self.bot.get_user(ctx.author.id)
        await user.send(embed=e)

    @_notify.command()
    @checks.is_mod()
    async def edit(self, ctx, msgid: int, new_msg):
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT * FROM notify WHERE msgid = :id",
                                 {'id': msgid})
            dump = await c.fetchall()
        if dump[0][1] != ctx.author.id:
            return await ctx.send("You need to be the author of the original message command to edit it!")
        for m in dump[0]:
            ogmsg = await ctx.get_message(m[0])
            msg = await ogmsg.edit(content=new_msg)
        await ctx.message.delete()
        embed = discord.Embed(colour=discord.Colour.green())
        embed.description = new_msg
        embed.add_field(name="Notify ID",
                        value=dump[0][4],
                        inline=False)
        embed.add_field(name="Message IDs",
                        value='\n'.join(dump[0]),
                        inline=False)
        embed.set_footer(text=f"Edit this message again with `notify edit {dump[0][4]} [new_msg]`")
        await ctx.author.send(embed=embed)

    @commands.group(invoke_without_command=True, name='announce')
    @commands.has_permissions(manage_messages=True)
    async def _announce(self, ctx, *, msg):
        """Setup announcing messages to specific channels in the server.
                Invoked without a command it will announce the message to set channels, or repeat in current channel if none have been set up.

                    PARAMETERS: [Message to announce]
                    EXAMPLE: `announce This is my cool bot!`
                    RESULT: Sends *This is my cool bot!* to all channels the bot has permissions for in the server

                """
        error_channels = ''
        successful = 0
        async with aiosqlite.connect(db_path) as db:
            c = await db.execute("SELECT * FROM announce_config WHERE guildid = :id",
                                 {'id': ctx.guild.id})
            dump = await c.fetchall()

        if len(dump) == 0:
            return await ctx.send(msg)
        channels = []
        [channels.append(c[1]) for c in dump]
        # get all channels in guild
        for channel in channels:
            try:
                # try to send the message supplied
                d = await self.bot.get_channel(channel).send(msg)
                successful += 1
            # no send msg permissions
            except discord.errors.Forbidden:
                error_channels += f'<#{channel}>\n'
        embed = discord.Embed()
        if error_channels == '':
            embed.color = (0x00ff00)
        else:
            embed.colour = (0xff0000)
        # tell them how many successful channels and which channels didnt work
        # (should be as intended by their discord perms)
        embed.set_author(name=f"Successful number of channels sent in: {successful}\n",
                         icon_url=self.bot.user.avatar_url)
        if error_channels:
            embed.title = f"I'm missing permissions in the following channels:\n"
            embed.description = error_channels
        c = await ctx.send(embed=embed)
        # delete the message after 5 seconds
        await asyncio.sleep(10)
        return await c.delete()

    @_announce.command()
    async def add(self, ctx, *channels: ChannelConverter):
        error_channels = ''
        chan = []
        for channel in channels:
            if isinstance(channel, discord.CategoryChannel):
                chan.extend(channel.channels)
            else:
                chan.append(channel)
        for channel in chan:
            if channel.permissions_for(ctx.guild.me).send_messages is False:
                error_channels += f'<#{channel.id}>\n'
                continue
            async with aiosqlite.connect(db_path) as db:
                c = await db.execute("SELECT * FROM announce_config WHERE guildid = :id AND channelid = :cid",
                                     {'id': ctx.guild.id, 'cid':channel.id})
                dump = await c.fetchall()
                if len(dump) == 0:
                    await db.execute('INSERT INTO announce_config VALUES (:id, :channelid)',
                                     {'id': ctx.guild.id, 'channelid': channel.id})
                    await db.commit()
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name="All done!", icon_url=ctx.author.avatar_url)
        if len(error_channels) != 0:
            e.title = 'I need send_message permissions in the following channels to add these to' \
                      ' the list, however. These channels were not added:'
            e.description = error_channels
        await ctx.send(embed=e)

    @_announce.command()
    async def remove(self, ctx, *channels: ChannelConverter):
        chan = []
        for channel in channels:
            if isinstance(channel, discord.CategoryChannel):
                chan.extend(channel.channels)
            else:
                chan.append(channel)
        for channel in chan:
            async with aiosqlite.connect(db_path) as db:
                await db.execute("DELETE FROM announce_config WHERE channelid = :id",
                                 {'id': channel.id})
                await db.commit()
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name="All done!", icon_url=ctx.author.avatar_url)
        await ctx.send(embed=e)

    @_announce.command()
    async def sendtemp(self, ctx, *channels: ChannelConverter):
        def check(user):
            if (user is None) or (user.author.id != ctx.author.id):
                return False
            else:
                return True
        error_channels = ''
        chan_to_send = []
        for channel in channels:
            if channel.permissions_for(ctx.guild.me).send_messages is False:
                error_channels += f'<#{channel.id}>\n'
                continue
            else:
                chan_to_send.append(channel)
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(name="Gotcha, those channels have been recorded. \n"
                          "What would you like the message to be? (120 sec timeout)",
                     icon_url=ctx.author.avatar_url)
        if len(error_channels) != 0:
            e.title = f"Hm...seems like I don't have `send_messages` permission in the following channels:"
            e.description = error_channels
        await ctx.send(embed=e)
        while True:
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=120.0)
                for channel in chan_to_send:
                    try:
                        await channel.send(msg.content)
                    except discord.Forbidden:
                        continue
                return await ctx.send('All done. Thanks!')

            except asyncio.TimeoutError:
                await ctx.send("You took too long. Try again (120 second timeout)")
                return

    @commands.command()
    async def makeembed(self, ctx):
        # work in progress
        def check(user):
            if (user is None) or (user.author.id != ctx.author.id):
                return False
            else:
                return True

        await ctx.send("Welcome to the interactive embed maker. We are going to make an embed; and then send it to"
                       " a channel. I will time out if you do not reply to a step within 60 seconds. "
                       "If you want to skip a step, type `None`. Let's begin.")

        await ctx.send(f"What would you like the colour to be? Type a name (eg. `navy`) "
                       f"and I will attempt to convert it, or any hex (ie. 0x00ff00 is green). Find a list here:"
                       f"https://www.w3schools.com/cssref/css_colors.asp")
        while True:
            try:
                colour = await self.bot.wait_for('message', check=check, timeout=60.0)
                try:
                    r = webcolors.name_to_rgb(colour.content)[0]
                    g = webcolors.name_to_rgb(colour.content)[1]
                    b = webcolors.name_to_rgb(colour.content)[2]
                    embed = discord.Embed(colour=discord.Colour.from_rgb(r, g, b))
                    break
                except ValueError:
                    await ctx.send("That's not a valid colour! You can find the full list at: "
                                   "https://www.w3schools.com/cssref/css_colors.asp")
                    pass
            except asyncio.TimeoutError:
                await ctx.send("I give up. You took too long")
                return
        await ctx.send(embed=embed)
        await ctx.send("What would you like the author field to contain? Max. 256 characters")
        while True:
            try:
                author = await self.bot.wait_for('message', check=check, timeout=60.0)
                if author.content == 'quit':
                    return
                if author.content == 'None':
                    pass
                else:
                    embed.set_author(name=author.content)
                    break
            except asyncio.TimeoutError:
                await ctx.send("I give up. You took too long")
                return
        await ctx.send('What would you like the title to be? Max characters: 256')
        while True:
            try:
                title = await self.bot.wait_for('message', check=check, timeout=60.0)
                if author.content == 'quit':
                    return
                if author.content == 'None':
                    pass
                if chr(author.content) > 256:
                    await ctx.send("This is more than the allowed 256 characters! Please try again")
                    pass
                else:
                    embed.title = title.content
                    break
            except asyncio.TimeoutError:
                await ctx.send("I give up. You took too long")
                return
        embed.description = 'This is your embed so far.'
        await ctx.send(embed=embed)
        await ctx.send("What would you like the description to be?")
        try:
            description = await self.bot.wait_for('message', check=check, timeout=60.0)
        except asyncio.TimeoutError:
            pass
        embed.description = description
        embed.add_field(name="This is your embed so far",
                        value="These 2 are the first field. What do you want to fill them with?")
        field1 = await self.bot.wait_for('message', check=check, timeout=60.0)
    # to finish



def setup(bot):
    bot.add_cog(Announcements(bot))
