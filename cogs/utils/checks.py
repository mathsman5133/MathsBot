from discord.ext import commands


async def check_perms(ctx, perms, *, check=all):
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    resolved = ctx.channel.permissions_for(ctx.author)
    return check(getattr(resolved, name, None) == value for name, value in perms.items())


def has_perms(*, check=all, **perms):
    async def pred(ctx):
        return await check_perms(ctx, perms, check=check)
    return commands.check(pred)


async def check_guild_perms(ctx, perms, *, check=all):
    owner = await ctx.bot.is_owner(ctx.author)
    if owner:
        return True
    if ctx.guild is None:
        return False

    resolved = ctx.channel.permissions_for(ctx.author)
    return check(getattr(resolved, name, None) == value for name, value in perms.items())


def has_guild_perms(*, check=all, **perms):
    async def pred(ctx):
        return await check_guild_perms(ctx, perms, check=check)
    return commands.check(pred)


def check_roles(ctx, modperms=False, adminperms=False):
    roles = ctx.bot.mod_roles[ctx.guild.id]
    if not roles:
        return False
    modroles = [n['roleid'] for n in roles if n['mod']]
    adminroles = [n['roleid'] for n in roles if n['admin']]
    if modperms:
        for rid in adminroles:
            if ctx.bot.get_role(rid) in ctx.author.roles:
                return True

        for rid in modroles:
            if ctx.bot.get_role(rid) in ctx.author.roles:
                return True
        return False

    if adminperms:
        for rid in adminroles:
            if ctx.bot.get_role(rid) in ctx.author.roles:
                return True
        return False


def is_mod():
    async def predict(ctx):
        owner = await ctx.bot.is_owner(ctx.author)
        if owner:
            return True

        check_roles(ctx, modperms=True)

    checkpredict = commands.check(predict)
    if checkpredict:
        return checkpredict

    async def pred(ctx):
        await check_guild_perms(ctx, {'manage_guild': True})

    return commands.check(pred)


def is_admin():
    async def predict(ctx):
        owner = await ctx.bot.is_owner(ctx.author)
        if owner:
            return True

        check_roles(ctx, adminperms=True)

    checkpredict = commands.check(predict)
    if checkpredict:
        return True

    async def pred(ctx):
        await check_guild_perms(ctx, {'administrator': True})

    return commands.check(pred)

