import asyncio
import typing

import discord
import sqlalchemy as sa
from discord.ext import commands

import database
import utils


class AdminCommands(commands.Cog, name="Admin"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="clean", aliases=["purge", "clear"])
    @commands.has_permissions(manage_messages=True)
    async def clean(self, ctx, limit: int):
        """
        Purge messages from a channel
        """
        await ctx.channel.purge(limit=limit)

        msg = await ctx.send(f"Successfully deleted {limit} messages. :thumbsup:")
        await asyncio.sleep(3)
        await msg.delete()

    @commands.group(name="settings", invoke_without_command=True)
    @commands.guild_only()
    async def settings_menu(self, ctx):
        desc = """
`wlchannel`: Set the channel to post welcome or leave messages to.
`welcometext`: Set the welcome text.
`leavetext`: Set the leave text.
`coindrops`: Enable or disable coin drops. (Options: `yes`/`no`)
            """
        embed = discord.Embed(
            title="Settings",
            color=ctx.author.color,
            description=f"Manage the settings for the bot! Available settings:\n{desc}",
        )
        embed.add_field(
            name="To get the value of a setting",
            value=f"`{ctx.prefix}{ctx.invoked_with} get <option name>`",
            inline=False,
        )
        embed.add_field(
            name="To set the value of a setting",
            value=f"`{ctx.prefix}{ctx.invoked_with} set <option name>`",
            inline=False,
        )
        embed.set_footer(text="You need admin permissions to set a setting!")

        await ctx.send(embed=embed)

    @settings_menu.command(name="get")
    @commands.guild_only()
    async def get_settings(self, ctx, setting: str):
        setting = setting.lower().strip()

        engine = await database.prepare_engine()

        query = database.Guild.select().where(database.Guild.c.guild == ctx.guild.id)
        db_guild = await engine.fetch_one(query=query)

        if setting == "wlchannel":
            wlchannel = db_guild[database.Guild.c.join_leave_channel]
            wlchannel = ctx.guild.get_channel(wlchannel) if wlchannel is not None else None
            wlchannel = wlchannel.mention if wlchannel is not None else "`Disabled`"
            return await ctx.send(
                f"Current channel to post welcome/leave messages is: {wlchannel}"
            )

        if setting == "welcometext":
            text = db_guild[database.Guild.c.welcome_str] or "`Disabled`"
            return await ctx.send(f"Current welcome text: {text}")

        if setting == "leavetext":
            text = db_guild[database.Guild.c.leave_str] or "`Disabled`"
            return await ctx.send(f"Current leave text: {text}")

        if setting == "coindrops":
            text = "`Enabled`" if db_guild[database.Guild.c.coin_drops] else "`Disabled`"
            return await ctx.send(f"Coin drop status: {text}")

        return await ctx.send("Setting not found!")

    @settings_menu.command(name="set")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def set_settings(
        self, ctx, setting: str, value: typing.Union[discord.TextChannel, bool, str]
    ):
        setting = setting.lower().strip()

        engine = await database.prepare_engine()
        query = database.Guild.update(None).where(database.Guild.c.guild == ctx.guild.id)

        if setting == "wlchannel":
            if not isinstance(value, discord.TextChannel):
                return await ctx.send("Invalid value! Enter a channel.")
            await engine.execute(query=query, values={"join_leave_channel": value.id})
            return await ctx.send(f"Welcome/leave channel set to {value.mention}")

        if setting == "welcometext":
            if not isinstance(value, str):
                return await ctx.send("Invalid value! Enter text.")
            await engine.execute(query=query, values={"welcome_str": value})
            return await ctx.send(f"Welcome text set to {value}")

        if setting == "leavetext":
            if not isinstance(value, str):
                return await ctx.send("Invalid value! Enter text.")
            await engine.execute(query=query, values={"leave_str": value})
            return await ctx.send(f"Leave text set to {value}")

        if setting == "coindrops":
            if not isinstance(value, bool):
                return await ctx.send("Invalid value! Enter yes or no.")
            await engine.execute(query=query, values={"coin_drops": value})
            return await ctx.send(f"Coin drops set to {value}")

        return await ctx.send("Setting not found!")

    @commands.command(name="rescuewaifus")
    @utils.ensure_bot_ready()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @utils.typing_indicator()
    async def rescue_waifus(self, ctx):
        """
        Removes waifus/husbandos from people who have left the server
        """
        await ctx.send(
            ":skull_crossbones: This will remove waifus from those who have left the server\n"
            "Note that this will take some time to complete, especially if there a lot of users.\n"
            "Type `confirm` to confirm within 15s, or `exit` to cancel."
        )

        try:
            confirmed = await utils.wait_for_confirm(ctx, timeout=15)
            if not confirmed:
                return
        except asyncio.TimeoutError:
            return await ctx.send("Error: Timed out.")

        engine = await database.prepare_engine()

        query = sa.select([sa.distinct(database.PurchasedWaifu.c.member)]).where(
            database.PurchasedWaifu.c.guild == ctx.guild.id
        )
        waifu_owners = await engine.fetch_all(query)

        query = database.PurchasedWaifu.delete(None).where(
            database.PurchasedWaifu.c.guild == ctx.guild.id
        )

        all_member_ids = {i[database.PurchasedWaifu.c.member] for i in waifu_owners}
        for member_id in all_member_ids:
            if ctx.guild.get_member(member_id) is not None:
                continue  # User still in guild
            await engine.execute(query=query.where(database.PurchasedWaifu.c.member == member_id))

        await ctx.send(":skull_crossbones: Removed waifus from everyone who left the server!")

    @commands.command(name="divorcewaifus")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def divorce_waifus(self, ctx, who: typing.Union[discord.Member, str]):
        """
        Divorce all waifus from a mentioned member, or all members in the server. Admin only.
        """
        if not isinstance(who, discord.Member) and who != "all":
            return await ctx.send(
                f"{who} is not a valid user.\n"
                "Please enter `all` to remove waifus from everyone, "
                "or otherwise mention a valid user."
            )

        if isinstance(who, discord.Member):
            await ctx.send(
                f":skull_crossbones: This will forcefully remove all waifus from {who}\n"
                "Type `confirm` to confirm within 15s, or `exit` to cancel."
            )
        else:
            await ctx.send(
                ":skull_crossbones: This will forcefully remove all waifus from "
                "everyone in the server\nType `confirm` to confirm within 15s, or `exit` to cancel."
            )

        try:
            confirmed = await utils.wait_for_confirm(ctx, timeout=15)
            if not confirmed:
                return
        except asyncio.TimeoutError:
            return await ctx.send("Error: Timed out.")

        engine = await database.prepare_engine()

        query = database.PurchasedWaifu.delete(None).where(
            database.PurchasedWaifu.c.guild == ctx.guild.id
        )
        if isinstance(who, discord.Member):
            query = query.where(database.PurchasedWaifu.c.member == who.id)

        await engine.execute(query=query)

        if isinstance(who, discord.Member):
            await ctx.send(f":skull_crossbones: Removed waifus from {who}!")
        else:
            await ctx.send(":skull_crossbones: Removed waifus from everyone!")
