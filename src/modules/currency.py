import asyncio
import datetime
import random
import string
import time
import typing

import aiohttp
import discord
from discoin import DiscoinError
from discord.ext import commands

import config
import database
import errors
import utils


class CurrencyCommands(commands.Cog, name="Financial"):
    def __init__(self, bot):
        self.bot = bot
        self.passive_money_users = {}
        self.free_money_channels = {}
        self.session = aiohttp.ClientSession()

    @commands.command(name="wallet")
    async def get_wallet(self, ctx, member: typing.Optional[discord.Member]):
        """
        Check your own wallet or others' wallet
        """
        member = member or ctx.author

        wallet = await database.fetch_wallet(member)

        if member == ctx.author:
            await ctx.send(f"You have {wallet:,} <:PIC:668725298388271105> in your wallet.")
        else:
            await ctx.send(
                f"{member.name} has {wallet:,} <:PIC:668725298388271105> in their wallet."
            )

    @commands.command(name="daily", aliases=["dailies"])
    async def dailies(self, ctx):
        """
        Get your daily money and become riiiich.
        """
        engine = await database.prepare_engine()
        fetch_query = database.Member.select().where(database.Member.c.member == ctx.author.id)
        db_member = await engine.fetch_one(fetch_query)

        last_dailies = db_member[database.Member.c.last_dailies]
        if last_dailies is not None:
            last_dailies = datetime.datetime.fromisoformat(str(last_dailies))
        member_tier = db_member[database.Member.c.tier]

        now = datetime.datetime.now()
        if last_dailies is not None and (now - last_dailies).days < 1:
            next_reset = datetime.datetime.utcfromtimestamp(
                (last_dailies + datetime.timedelta(days=1) - now).total_seconds()
            ).strftime("%H hours %M minutes")

            return await ctx.send(f"Please wait for {next_reset} more to get dailies.")

        update_query = (
            database.Member.update(None)
            .where(database.Member.c.member == ctx.author.id)
            .values(last_dailies=now)
        )
        await engine.execute(update_query)

        amount = config.DAILIES_AMOUNT
        jackpot = ""

        if random.randint(1, 100) >= 90:
            amount *= 10
            jackpot = (
                "Congratulations, you have hit the jackpot :money_mouth:\n"
                "You get 10x the amount!\n"
            )

        if member_tier >= config.DONATOR_TIER_2:
            amount *= 4
            await database.add_money(ctx.author, amount)
            await ctx.send(
                f"{jackpot}Recieved {amount} <:PIC:668725298388271105>! "
                "4 times the usual amount for being a Tier 2 donator! <:uwu:575372762583924757>"
            )
        elif member_tier >= config.DONATOR_TIER_1:
            amount *= 2
            await database.add_money(ctx.author, amount)
            await ctx.send(
                f"{jackpot}Recieved {amount} <:PIC:668725298388271105>! "
                "Twice the usual amount for being a Tier 1 donator! <:uwu:575372762583924757>"
            )
        else:
            await database.add_money(ctx.author, amount)
            await ctx.send(
                f"{jackpot}Recieved {amount} <:PIC:668725298388271105>! "
                "<:SataniaThumb:575384688714317824>"
            )

    @commands.command(name="hourly", aliases=["hourlies"])
    @commands.check(utils.check_tier_matches(1))
    async def hourlies(self, ctx):
        """
        Get your hourly money and become riiiicher. Only for donators.
        """
        engine = await database.prepare_engine()
        fetch_query = database.Member.select().where(database.Member.c.member == ctx.author.id)
        db_member = await engine.fetch_one(fetch_query)

        last_hourlies = db_member[database.Member.c.last_hourlies]
        if last_hourlies is not None:
            last_hourlies = datetime.datetime.fromisoformat(str(last_hourlies))
        member_tier = db_member[database.Member.c.tier]

        now = datetime.datetime.now()
        if last_hourlies is not None and (now - last_hourlies).total_seconds() < 3600:
            next_reset = datetime.datetime.utcfromtimestamp(
                (last_hourlies + datetime.timedelta(hours=1) - now).total_seconds()
            ).strftime("%H hours %M minutes")

            return await ctx.send(f"Please wait for {next_reset} to get hourlies.")

        update_query = (
            database.Member.update(None)
            .where(database.Member.c.member == ctx.author.id)
            .values(last_hourlies=now)
        )
        await engine.execute(update_query)

        amount = config.HOURLIES_AMOUNT

        if member_tier >= config.DONATOR_TIER_2:
            amount *= 2
            await database.add_money(ctx.author, amount)
            await ctx.send(
                f"Recieved {amount} <:PIC:668725298388271105>! "
                "2 times the usual amount for being a Tier 2 donator! <:uwu:575372762583924757>"
            )
        elif member_tier >= config.DONATOR_TIER_1:
            await database.add_money(ctx.author, amount)
            await ctx.send(f"Recieved {amount} <:PIC:668725298388271105>!")

    @commands.command(
        name="claimreward",
        aliases=["claimrewards"],
        enabled=(config.DBL_TOKEN is not None),
    )
    @commands.cooldown(rate=59, per=60)
    @utils.typing_indicator()
    async def claim_vote_rewards(self, ctx):
        engine = await database.prepare_engine()

        headers = {"Authorization": config.DBL_TOKEN}

        query = database.Member.select().where(database.Member.c.member == ctx.author.id)
        member = await engine.fetch_one(query=query)
        member_tier = member[database.Member.c.tier]
        last_reward = member[database.Member.c.last_reward]
        already_claimed = (last_reward is not None) and (
            (datetime.datetime.now() - last_reward).total_seconds() < 3600 * 12
        )
        if already_claimed:
            interval = datetime.timedelta(seconds=3600 * 12) - (
                datetime.datetime.now() - last_reward
            )
            return await ctx.send(
                f"You have already claimed your rewards! "
                f"Please wait for {interval} before next claim."
            )

        async with self.session.get(
            f"https://top.gg/api/bots/{ctx.bot.user.id}/check?userId={ctx.author.id}",
            headers=headers,
        ) as resp:
            resp_data = await resp.json()
            has_voted = bool(resp_data["voted"])
        if not has_voted:
            return await ctx.send(f"You have not voted yet! Vote with `{ctx.prefix}vote`.")

        msgtxts = ["Thanks for voting! Here, have some coins."]
        coins = config.VOTE_REWARD

        async with self.session.get("https://top.gg/api/weekend", headers=headers) as resp:
            resp_data = await resp.json()
            is_weekend = resp_data["is_weekend"]

        if is_weekend:
            coins *= 2
            msgtxts.append("Thanks for voting on weekend! You get 2x coins.")
        if member_tier >= config.DONATOR_TIER_2:
            coins *= 4
            msgtxts.append(
                "You get 4 times the usual amount for being a tier 2 donator! "
                "<:AilunaHug:575373643551473665>"
            )
        elif member_tier >= config.DONATOR_TIER_1:
            coins *= 2
            msgtxts.append(
                "You get 2 times the usual amount for being a tier 1 donator! "
                "<:AilunaHug:575373643551473665>"
            )
        update_query = (
            database.Member.update(None)
            .where(database.Member.c.member == ctx.author.id)
            .values(last_reward=datetime.datetime.now())
        )
        await engine.execute(update_query)
        await database.add_money(ctx.author, coins)

        msgtxts.append(f"{ctx.author} has got {coins} coins. <:SataniaThumb:575384688714317824>")
        await ctx.send("\n".join(msgtxts))

    @commands.command(name="transfer", aliases=["transfermoney"])
    async def transfer_money(self, ctx, user: discord.Member, amount: int):
        """
        Transfer some money to someone in need.
        """
        if amount <= 0:
            return await ctx.send("Don't try to cheat me, amount must be positive!")

        if user.id == ctx.author.id:
            return await ctx.send("Cannot send to yourself!")

        try:
            await database.remove_money(ctx.author, amount)
            await database.add_money(user, amount)
            await ctx.send("Done <:SataniaThumb:575384688714317824>")
        except errors.NotEnoughBalance:
            await ctx.send("You do not have enough money to transfer! <:smug:575373306715439151>")

    @commands.command(name="exchange", enabled=(config.DISCOIN_TOKEN is not None))
    @utils.typing_indicator()
    async def exchange_money(self, ctx, currency: str, amount: int):
        """
        Exchange currency with other bots with <:Discoin:357656754642747403> Discoin. WIP.
        """
        currency = currency.upper()
        try:
            await database.remove_money(ctx.author, amount)
            transaction = await ctx.bot.discoin_client.create_transaction(
                currency, amount, ctx.author.id
            )
        except DiscoinError as err:
            return await ctx.send(
                f"Hit an error :exploding_head: {type(err).__name__}\nMessage: {err}"
            )
        except errors.NotEnoughBalance:
            return await ctx.send(
                "You do not have enough money to transfer! <:smug:575373306715439151>"
            )

        embed = discord.Embed(
            title="<:Discoin:357656754642747403> Exchange Successful!",
            description=(
                "Your Pino-coins <:PIC:668725298388271105> "
                "are being sent via the top-secret Agent Wumpus. "
                "He usually delivers the coins within 5 minutes.\n"
                f"See `{ctx.prefix}discoin` for more info."
            ),
        )

        embed.add_field(
            name="Pinocchio Coins <:PIC:668725298388271105> (PIC) Exchanged",
            value=amount,
        )
        embed.add_field(name=f"{currency} To Recieve", value=transaction.payout)
        embed.add_field(
            name="Transaction Receipt",
            inline=False,
            value=(
                "Keep this code in case Agent Wumpus fails to deliver the coins."
                f"[```{transaction.id}```]"
                f"(https://dash.discoin.zws.im/#/transactions/{transaction.id}/show)"
            ),
        )
        embed.set_footer(
            text=str(ctx.author),
            icon_url=ctx.author.avatar_url_as(size=64),
        )
        await ctx.send(embed=embed)

    @commands.command(name="discoin", enabled=(config.DISCOIN_TOKEN is not None))
    async def discoin_info(self, ctx):
        embed = discord.Embed(
            title="<:Discoin:357656754642747403> Discoin Information",
            description=f"""
Discoin is a platform with which participating bots can exchange money with each other.
Dashboard for Discoin is here: https://dash.discoin.zws.im
Usage: ```{ctx.prefix}exchange <Currency> <Pinocchio Coins>```
where `currency` is the receiving bot's currency name.
            """,
        )
        currencies = await ctx.bot.discoin_client.fetch_currencies()
        currencies = [
            f"{i.name:<19}({i.id}) - {float(i.value):07.4f} - {i.reserve}" for i in currencies
        ]
        txt = f"{'Name':<19}{'(ID)':<3}  - {'Value':<7} - Reserve"
        currencies.insert(0, txt)
        currencies.insert(1, max([len(i) for i in currencies]) * "-")
        embed.add_field(
            name="**Discoin Currency Table**",
            inline=False,
            value="```" + "\n".join(currencies) + "```",
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener("on_message")
    async def passive_money_generator(self, message: discord.Message):
        user = message.author
        bot = self.bot

        if user.bot or message.guild is None:
            return

        now = time.monotonic()

        last = self.passive_money_users.setdefault(user.id, now)
        if now - last > 60:
            self.passive_money_users[user.id] = now
            await database.add_money(user, random.randint(1, 5))

        _n = config.FREE_MONEY_SPAWN_LIMIT
        _e = self.free_money_channels.setdefault(message.channel.id, random.randint(1, _n))
        if _e != random.randint(1, _n):
            return
        self.free_money_channels[message.channel.id] = random.randint(1, _n)

        engine = await database.prepare_engine()

        query = database.Guild.select().where(database.Guild.c.guild == message.guild.id)
        db_guild = await engine.fetch_one(query=query)

        coin_drops_enabled = db_guild[database.Guild.c.coin_drops]
        if not coin_drops_enabled:
            return

        code = "".join(random.choices(string.ascii_letters + string.digits, k=4))
        amount = random.randint(10, 200)
        coin_message = f"collect-coins {code}"

        drop_msg = await message.channel.send(
            f"{amount} <:PIC:668725298388271105> has appeared <:AilunaHug:575373643551473665>! "
            f"To collect, enter `collect-coins <code>`. Code is `{code}`. Hurry, 20s left."
        )

        def check(_m):
            return (
                _m.channel == message.channel and not _m.author.bot and _m.content == coin_message
            )

        try:
            msg = await bot.wait_for("message", check=check, timeout=20)
        except asyncio.TimeoutError:
            fail_msg = await message.channel.send("Error: Timeout")
            await asyncio.sleep(3)
            await message.channel.delete_messages([drop_msg, fail_msg])
            return

        await database.add_money(msg.author, amount)
        gain_msg = await message.channel.send(
            f"User {msg.author.mention} has gained {amount} <:PIC:668725298388271105>!"
        )
        await asyncio.sleep(3)
        await message.channel.delete_messages([drop_msg, msg, gain_msg])
