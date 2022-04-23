import time
import typing
from datetime import timedelta

import discord
import psutil
from discord.ext import commands

import config
import database
from utils import check_tier_matches

process = psutil.Process()
init_cpu_time = process.cpu_percent()


class DevCommands(commands.Cog, name="Developer"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="stats", aliases=["botstats", "botinfo", "info"])
    async def view_stats(self, ctx):
        """
        Returns bot statistics and technical data.
        """
        app_info = await ctx.bot.application_info()
        embed = discord.Embed(title="Bot Stats", description="Running on Server-Miku 8GB of RAM.")

        dev1 = ctx.bot.get_user(252297314394308608) or await ctx.bot.fetch_user(252297314394308608)
        dev2 = ctx.bot.get_user(532123382280355860) or await ctx.bot.fetch_user(532123382280355860)

        embed.add_field(name="**__General Info__**", inline=False, value="\u200b")
        embed.add_field(name="Developers", value=f"{dev1}, {dev2}")
        embed.add_field(name="Latency", value=f"{ctx.bot.latency*1000:.03f} ms")
        embed.add_field(name="Guild Count", value=f"{len(ctx.bot.guilds):,}")
        embed.add_field(name="User Count", value=f"{len(ctx.bot.users):,}")
        embed.add_field(name="Current Shard", value=f"{ctx.guild.shard_id}")
        embed.add_field(name="Environment", value=f"{'Dev' if config.DEV_MODE else 'Prod'}")
        embed.add_field(name="Commit SHA", value=config.GIT_SHA)
        embed.add_field(name="Build Version", value=config.BUILD_VERSION)
        embed.add_field(name="Build Date", value=config.BUILD_DATE)

        embed.add_field(name="**__Technical Info__**", inline=False, value="\u200b")
        embed.add_field(name="System CPU Usage", value=f"{psutil.cpu_percent():.02f}%")
        embed.add_field(
            name="System RAM Usage",
            value=f"{psutil.virtual_memory().used/1048576:.02f} MB",
        )
        embed.add_field(
            name="System Uptime",
            value=str(timedelta(seconds=int(time.time() - psutil.boot_time()))),
        )
        embed.add_field(name="Bot CPU Usage", value=f"{process.cpu_percent():.02f}%")
        embed.add_field(name="Bot RAM Usage", value=f"{process.memory_info().rss/1048576:.02f} MB")
        embed.add_field(
            name="Bot Uptime",
            value=str(timedelta(seconds=int(time.time() - process.create_time()))),
        )

        embed.add_field(name="**__Links__**", inline=False, value="\u200b")
        embed.add_field(
            name="Donate",
            value="[https://patreon.com/RandomGhost](https://patreon.com/RandomGhost)",
        )
        embed.add_field(
            name="Website", value="[https://pinocchiobot.xyz](https://pinocchiobot.xyz)"
        )
        embed.add_field(
            name="Discord Bots",
            value="[https://dbots.pinocchiobot.xyz](https://dbots.pinocchiobot.xyz)",
        )
        embed.add_field(
            name="Support Server",
            value="[https://support.pinocchiobot.xyz](https://support.pinocchiobot.xyz)",
        )
        embed.add_field(
            name="Invite",
            value="[https://invite.pinocchiobot.xyz](https://invite.pinocchiobot.xyz)",
        )
        embed.add_field(
            name="Add Waifus",
            value="[https://waifu.pinocchiobot.xyz](https://waifu.pinocchiobot.xyz)",
        )
        embed.set_footer(
            text=f"Running on Miku • Made by {app_info.owner}",
            icon_url=app_info.owner.avatar_url_as(size=128),
        )
        await ctx.send(embed=embed)

    @commands.command(name="ping")
    async def ping(self, ctx):
        """
        Checks bot latency.
        """
        await ctx.send(f"Pong! {ctx.bot.latency * 1000:.03f}ms")

    @commands.command(name="getmoney", hidden=True)
    @commands.check(check_tier_matches(5))
    async def get_money(self, ctx, amount: int):
        """
        Only for developer to use.
        """
        amount = int(amount)
        balance = await database.add_money(ctx.author, amount)
        await ctx.send(f"Gave `{amount}` coins. You now have `{balance}` coins in your wallet.")

    @commands.command(name="removemoney", hidden=True)
    @commands.check(check_tier_matches(5))
    async def remove_money(self, ctx, user: typing.Union[discord.Member, int], amount: int):
        """
        Remove money from a user. Dev only
        """
        if not isinstance(user, discord.Member):
            user = self.bot.get_user(user)

        amount = int(amount)
        balance = await database.remove_money(user, amount)
        await ctx.send(
            f"Removed `{amount}` coins. {user} now has `{balance}` coins in their wallet."
        )

    @commands.command(name="awhois", hidden=True)
    @commands.check(check_tier_matches(5))
    async def whois_admin(self, ctx, user: typing.Union[discord.Member, str]):
        """
        Get details about an user. Dev only.
        """
        engine = await database.prepare_engine()

        if not isinstance(user, discord.Member):
            if not user.isdigit():
                query = """
SELECT member from members
                """

                found = False
                results = await engine.fetch_all(query=query)
                for result in results:
                    member = self.bot.get_user(result["member"])
                    if str(member) == user:
                        found = True
                        user = member
                        break
                if not found:
                    user = None
            else:
                user = self.bot.get_user(int(user))

        if not user:
            return await ctx.send("User not found!")

        query = database.Member.select().where(database.Member.c.member == user.id)
        dbuser = await engine.fetch_one(query=query)

        last_dailies = dbuser[database.Member.c.last_dailies]
        if last_dailies:
            last_dailies = last_dailies.strftime(r"%A, %d %B, %Y - %I:%M:%S %p")
        last_reward = dbuser[database.Member.c.last_reward]
        if last_reward:
            last_reward = last_reward.strftime(r"%A, %d %B, %Y - %I:%M:%S %p")

        guilds = []
        for i in ctx.bot.guilds:
            try:
                member = i.get_member(user.id) or await i.fetch_member(user.id)
            except discord.NotFound:
                member = None
            if member:
                guilds.append(
                    f"{'**[Owner]** ' if (member == i.owner) else ''}{i.name} ({len(i.members)})"
                )

        embed = discord.Embed(title=f"{user}", color=user.colour)
        embed.set_thumbnail(url=user.avatar_url_as(size=1024))
        embed.add_field(name="User ID", value=user.id)
        embed.add_field(name="Is Bot", value=user.bot)
        embed.add_field(name="Wallet", value=dbuser[database.Member.c.wallet])
        embed.add_field(name="Tier", value=dbuser[database.Member.c.tier])
        embed.add_field(name="Last Dailies", value=last_dailies)
        embed.add_field(name="Last Reward", value=last_reward)
        embed.add_field(
            name="Account Created On",
            inline=False,
            value=user.created_at.strftime(r"%A, %d %B, %Y - %I:%M:%S %p"),
        )
        embed.add_field(name="In Guilds", inline=False, value=", ".join(guilds))

        await ctx.send(embed=embed)
