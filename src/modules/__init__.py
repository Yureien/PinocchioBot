import logging
import traceback

import discord
from discoin import Client as Discoin
from discord.ext import commands

import config
import database
import errors

from . import handlers
from .admin import AdminCommands
from .anime import AnimeCommands
from .currency import CurrencyCommands
from .dev import DevCommands
from .fun import FunCommands
from .general import GeneralCommands
from .help import Help
from .reactions import ReactionCommands
from .topgg import TopGGCog
from .waifu import WaifuCommands

intents = discord.Intents.default()
intents.members = True  # pylint: disable=assigning-non-slot

bot = commands.AutoShardedBot(
    command_prefix=config.PREFIX,
    activity=discord.Activity(
        type=discord.ActivityType.playing,
        name=f"{config.PREFIX}help | Bot is still loading, some commands might not work!",
    ),
    intents=intents,
    case_insensitive=True,
)

bot.discoin_client = None


async def before_start():
    # Actions to execute before bot starts.
    database.prepare_tables()
    if config.DISCOIN_TOKEN:
        bot.discoin_client = Discoin(config.DISCOIN_TOKEN, config.DISCOIN_SELF_CURRENCY)


@bot.event
async def on_ready():
    logging.info("Logged in as %s - %s.", bot.user, bot.user.id)
    await database.make_guild_entry(bot.guilds)
    await database.make_member_profile(bot.get_all_members())
    logging.info("All done, bot is ready to go!")


@bot.event
async def on_member_join(member):
    await database.make_member_profile([member])
    await handlers.send_on_member_join(member)


@bot.event
async def on_member_remove(member):
    await database.make_member_profile([member])
    await handlers.send_on_member_leave(member)


@bot.event
async def on_guild_join(guild):
    await database.make_guild_entry([guild])
    await database.make_member_profile(guild.members)


@bot.event
async def on_command_error(ctx, error):
    # This prevents any commands with local handlers being handled here in on_command_error.
    if hasattr(ctx.command, "on_error"):
        return

    # This prevents any cogs with an overwritten cog_command_error being handled here.
    cog = ctx.cog
    if cog:
        method = cog._get_overridden_method(  # pylint: disable=protected-access
            cog.cog_command_error
        )
        if method is not None:
            return

    ignored = (commands.CommandNotFound,)

    # Allows us to check for original exceptions raised and sent to CommandInvokeError.
    # If nothing is found. We keep the exception passed to on_command_error.
    error = getattr(error, "original", error)

    # Anything in ignored will return and prevent anything happening.
    if isinstance(error, ignored):
        return

    if isinstance(error, commands.DisabledCommand):
        await ctx.send(f"{ctx.command} has been disabled.")
    elif isinstance(
        error,
        (
            commands.MissingRequiredArgument,
            commands.BadArgument,
            commands.MissingPermissions,
            commands.CommandOnCooldown,
        ),
    ):
        parent = ctx.command.full_parent_name
        alias = ctx.invoked_with if not parent else f"{parent} {ctx.invoked_with}"
        cmd_usage = (
            ctx.command.usage or f"{ctx.prefix}{alias} {ctx.command.signature}"
            if ctx.command
            else None
        )
        cmd_usage = f"Usage: `{cmd_usage}`" if cmd_usage else "No usage found!"
        return await ctx.send(f"{error}\n{cmd_usage}")
    elif isinstance(error, commands.NoPrivateMessage):
        try:
            await ctx.author.send(f"{ctx.command} can not be used in Private Messages.")
        except discord.HTTPException:
            pass
    elif isinstance(error, errors.BotNotReady):
        await ctx.send(
            "The bot is still loading internal cache, so this command is unavailable for now.\n"
            "Please try again later! Blame Discord for making cache load slow for big bots :)"
        )
    elif isinstance(error, errors.LockedCommand):
        await ctx.send(
            "You are already performing some other action! "
            "Please exit any ongoing actions by typing `exit`."
        )
    else:
        etype = type(error)
        trace = error.__traceback__
        lines = traceback.format_exception(etype, error, trace, 3)
        logging.error("".join(lines))


bot.add_cog(handlers.TasksCog(bot))

if config.DBL_TOKEN:
    bot.add_cog(TopGGCog(bot, config.DBL_TOKEN))

bot.add_cog(GeneralCommands(bot))
bot.add_cog(WaifuCommands(bot))
bot.add_cog(FunCommands(bot))
bot.add_cog(ReactionCommands(bot))
bot.add_cog(AnimeCommands(bot))
bot.add_cog(CurrencyCommands(bot))
bot.add_cog(AdminCommands(bot))
bot.add_cog(DevCommands(bot))
bot.add_cog(Help(bot))
