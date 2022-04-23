import asyncio
import re
import typing
from datetime import datetime, timedelta

import discord
import sqlalchemy as sa
from discord.ext import commands

import config
import database
import errors
import utils
from database import add_money

BUY_LOCK = []
LOCKS_MAP = {}


async def lock_command(ctx):
    global LOCKS_MAP
    key = f"{ctx.guild.id}:{ctx.author.id}"
    if LOCKS_MAP.get(key) is not None:
        raise errors.LockedCommand
    LOCKS_MAP[key] = ctx.message.id
    return True


async def unlock_command(ctx):
    global LOCKS_MAP
    key = f"{ctx.guild.id}:{ctx.author.id}"
    if LOCKS_MAP.get(key) == ctx.message.id:
        LOCKS_MAP[key] = None


class WaifuCommands(commands.Cog, name="Waifu"):
    def __init__(self, bot):
        self.bot = bot
        self.gender_table = {
            "m": "husbando",
            "f": "waifu",
        }
        self.random_waifu_counter = {}

    @commands.command("search")
    @commands.guild_only()
    async def search(self, ctx, *, search_str: str):
        """
        Search for a waifu in the Dungeon of Waifus. Don't get lost!
        """
        engine = await database.prepare_engine()

        query = generate_search_query(search_str)
        waifus = await engine.fetch_all(query=query)

        if len(waifus) == 0:
            return await ctx.send(
                "Waifu not found! You can add the waifu yourself, and for that "
                "please join the support server! (`=support`) <a:thanks:699004469610020964>"
            )

        pages = []
        resp_string = ""
        for row in waifus:
            resp_string += (
                f"**{row['name']}**: ID is {row['id']}, from *{row['from_anime']}*. "
                f"Costs **{row['price']:,}** <:PIC:668725298388271105>\n"
            )
            if len(resp_string) > 1900:
                pages.append(resp_string)
                resp_string = ""
        if resp_string != "":
            pages.append(resp_string)

        embed = discord.Embed(
            title=f"{len(waifus)} Waifus Found in the Dungeon!\n",
            description=pages[0],
            color=ctx.author.color,
        )
        embed.set_footer(text=f"To view details, do {ctx.prefix}details <name/id>")

        if len(pages) > 1:
            embed.add_field(name="Page Number", value=f"1/{len(pages)}")

        async def modifier_func(page_num, **kwargs):
            embed.description = pages[page_num]
            embed.set_field_at(index=0, name="Page Number", value=f"{page_num+1}/{len(pages)}")

        await utils.paginate_embed(ctx, embed, len(pages), modifier_func)

    @commands.command("details")
    @commands.guild_only()
    async def details(self, ctx, *, search_str: str):
        """
        Get details (and pictures) of a waifu! (But don't lewd them)
        """
        engine = await database.prepare_engine()

        query = generate_search_query(search_str, limit=1)
        waifu = await engine.fetch_one(query=query)
        if waifu is None:
            return await ctx.send(
                "Waifu not found! You can add the waifu yourself, please join "
                "the support server! (`=support`) <a:thanks:699004469610020964>"
            )

        query = (
            database.PurchasedWaifu.select()
            .where(database.PurchasedWaifu.c.waifu_id == waifu["id"])
            .where(database.PurchasedWaifu.c.guild == ctx.guild.id)
        )
        db_owner = await engine.fetch_one(query=query)
        has_owner = db_owner is not None
        owner = None
        purchased_for = 0
        if has_owner:
            try:
                owner = ctx.guild.get_member(
                    db_owner[database.PurchasedWaifu.c.member]
                ) or await ctx.guild.fetch_member(db_owner[database.PurchasedWaifu.c.member])
            except discord.NotFound:
                owner = None
            purchased_for = db_owner[database.PurchasedWaifu.c.purchased_for]

        waifu = {
            "id": waifu["id"],
            "name": waifu["name"],
            "anime": waifu["from_anime"],
            "price": waifu["price"],
            "desc": waifu["description"],
            "image_url": waifu["image_url"],
            "gender": self.gender_table.get(waifu["gender"], "?????"),
        }

        if not waifu["desc"]:
            waifu["desc"] = f"Hi! I am a {waifu['gender']} from {waifu['anime']}."
        if len(waifu["desc"]) > 1900:
            waifu["desc"] = waifu["desc"][:1900] + "..."
        waifu["desc"] = waifu["desc"].replace("\\n", "\n")

        if not has_owner:
            waifu[
                "desc"
            ] += f"\n\nYou need {waifu['price']} <:PIC:668725298388271105> to buy them."
        else:
            if owner is not None:
                rstatus = "deep" if db_owner[database.PurchasedWaifu.c.favorite] else "casual"
                waifu["desc"] += (
                    f"\n\nThey are already in a {rstatus} " f"relationship with {str(owner)}."
                )
            else:
                waifu["desc"] += (
                    "\n\nThey were purchased and abandoned by someone who left this server. "
                    f"Rescue them with `{ctx.prefix}rescuewaifus`!"
                )

        embed = discord.Embed(
            title=waifu["name"],
            description=waifu["desc"],
            color=ctx.author.color,
        )

        images = []
        if waifu["image_url"] is not None:
            images = waifu["image_url"].split(",")
            embed.set_image(url=images[0])

        embed.add_field(name="From", value=waifu["anime"], inline=False)
        embed.add_field(name="Cost", value=f"{waifu['price']:,} <:PIC:668725298388271105>")
        embed.add_field(name="ID", value=waifu["id"])
        embed.add_field(name="Gender", value=waifu["gender"])
        image_field_id = 4
        if owner and db_owner[database.PurchasedWaifu.c.favorite]:
            embed.add_field(name="Favorite", value="Purchaser's favorite waifu :heart:")
            image_field_id += 1
        if len(images) > 1:
            embed.add_field(name="Image", inline=False, value=f"**Showing: 1/{len(images)}**")
        if has_owner:
            if owner is not None:
                embed.set_footer(
                    text=(f"Purchased by {owner} for {purchased_for} PIC."),
                    icon_url=owner.avatar_url_as(size=128),
                )
            else:
                embed.set_footer(text=f"Purchased by someone who left for {purchased_for} PIC.")

        async def modifier_func(page_num, **kwargs):
            embed.set_image(url=images[page_num])
            embed.set_field_at(
                index=image_field_id,
                name="Image",
                inline=False,
                value=f"**Showing: {page_num+1}/{len(images)}**",
            )

        await utils.paginate_embed(ctx, embed, len(images), modifier_func)

    @commands.command(name="favorite", aliases=["favourite"])
    @commands.guild_only()
    async def favorite(self, ctx, *, search_str: str):
        """
        Mark your waifu as a favorite to show your eternal love!
        """
        await self.toggle_favorite(ctx, search_str, True)

    @commands.command(name="unfavorite", aliases=["unfavourite"])
    @commands.guild_only()
    async def unfavorite(self, ctx, *, search_str: str):
        """
        Unmark a waifu as a favorite because all waifus are equal and deserve equal love!
        """
        await self.toggle_favorite(ctx, search_str, False)

    @commands.command(name="harem", aliases=["waifulist"])
    @commands.guild_only()
    async def harem(self, ctx, user: typing.Optional[discord.Member], *filter_opts):
        """
        Flex your harem, or get jealous of other's!

        Filter options:
        name-desc, series-desc, name-asc, series-asc, id-asc,
        id-desc, price-asc, price-desc, waifu, husbando
        """
        user = user or ctx.author

        engine = await database.prepare_engine()

        query = (
            database.PurchasedWaifu.select()
            .where(database.PurchasedWaifu.c.member == user.id)
            .where(database.PurchasedWaifu.c.guild == ctx.guild.id)
        )
        purchased_waifus = await engine.fetch_all(query=query)
        if len(purchased_waifus) == 0:
            return await ctx.send(f"{user} does not have a harem. What a lonely life!")

        waifu_ids = [x[database.PurchasedWaifu.c.waifu_id] for x in purchased_waifus]
        query = database.Waifu.select().where(database.Waifu.c.id.in_(waifu_ids))
        resp = await engine.fetch_all(query=query)
        waifu_data = {x[database.Waifu.c.id]: x for x in resp}

        purchased_waifus = filter_harem(purchased_waifus, waifu_data, filter_opts)

        if len(purchased_waifus) == 0:
            return await ctx.send("No harem found for specified filters.")

        pages = []
        _n = 0
        n_each_page = 10
        for i in range(0, len(purchased_waifus), n_each_page):
            pages.append(
                [(_n + m + 1, j) for m, j in enumerate(purchased_waifus[i : i + n_each_page])]
            )
            _n += n_each_page

        embed = discord.Embed(
            title=f"{user.name}'s Harem",
            color=user.color,
            description=prepare_harem_page(pages[0], waifu_data),
        )

        embed.add_field(name="Waifus Inside Locker", value=len(purchased_waifus))
        embed.add_field(
            name="Net Harem Value",
            value=str(sum([i[database.PurchasedWaifu.c.purchased_for] for i in purchased_waifus]))
            + " <:PIC:668725298388271105>",
        )
        embed.add_field(
            name="\u200b",
            inline=False,
            value=f"To view details, do `{ctx.prefix}details <name/id>`",
        )
        embed.set_footer(
            text=f"{user} • Page {1}/{len(pages)}",
            icon_url=user.avatar_url_as(size=128),
        )

        async def modifier_func(page_num, **kwargs):
            embed.description = prepare_harem_page(pages[page_num], waifu_data)
            embed.set_footer(
                text=f"{user} • Page {page_num + 1}/{len(pages)}",
                icon_url=user.avatar_url_as(size=128),
            )

        await utils.paginate_embed(ctx, embed, len(pages), modifier_func)

    @commands.command(name="buy")
    @commands.guild_only()
    @commands.check(lock_command)
    async def buy(self, ctx, *, search_str: str):
        """
        Buy your own waifu to prove your love for her!
        (P.S: The waifus have consented. No trafficked waifus, promise!)
        """
        global BUY_LOCK
        engine = await database.prepare_engine()

        query = generate_search_query(search_str, limit=1)
        waifu = await engine.fetch_one(query=query)
        if waifu is None:
            return await ctx.send("Waifu not found!")

        query = (
            database.PurchasedWaifu.select()
            .where(database.PurchasedWaifu.c.waifu_id == waifu["id"])
            .where(database.PurchasedWaifu.c.guild == ctx.guild.id)
        )
        db_purchaser = await engine.fetch_one(query=query)
        if db_purchaser is not None:
            purchaser = ctx.guild.get_member(
                db_purchaser[database.PurchasedWaifu.c.member]
            ) or await ctx.guild.fetch_member(db_purchaser[database.PurchasedWaifu.c.member])
            if purchaser is None:
                return await ctx.send(
                    "This waifu was purchased by someone who has now "
                    "left the server! Rescue them with `=rescuewaifus`."
                )
            if db_purchaser[database.PurchasedWaifu.c.member] == ctx.author.id:
                return await ctx.send(
                    "How many more times do you want to buy "
                    "this waifu? <:smug:575373306715439151>"
                )
            return await ctx.send(
                f"Waifu is already purchased by {purchaser}. "
                "Ask them to sell it or trade with you!"
            )

        wallet = await database.fetch_wallet(ctx.author)
        if wallet - waifu["price"] < 0:
            return await ctx.send(
                "You do not have enough money! <:Eww:575373991640956938>\n"
                f"You need {waifu['price']-wallet:,} <:PIC:668725298388271105> more."
            )

        waifu_id = f"{ctx.guild.id}:{waifu['id']}"
        if waifu_id in BUY_LOCK:
            return await ctx.send("It looks like someone else is trying to buy this waifu already")
        BUY_LOCK.append(waifu_id)
        await ctx.send(
            f"Want to buy {waifu['name']} for sure? Reply with `confirm` in 60s or `exit`."
        )

        try:
            confirmed = await utils.wait_for_confirm(ctx)
            if not confirmed:
                return
        except asyncio.TimeoutError:
            return await ctx.send("Error: Timed out.")
        finally:
            BUY_LOCK.remove(waifu_id)

        try:
            await database.remove_money(ctx.author, waifu["price"])
        except errors.NotEnoughBalance:
            wallet = await database.fetch_wallet(ctx.author)
            return await ctx.send(
                "You do not have enough money! <:Eww:575373991640956938>\n"
                f"You need {waifu['price']-wallet:,} <:PIC:668725298388271105> more."
            )

        query = database.Member.select().where(database.Member.c.member == ctx.author.id)
        buyer = await engine.fetch_one(query)
        await engine.execute(
            query=database.PurchasedWaifu.insert(None),
            values={
                "member_id": buyer[database.Member.c.id],
                "waifu_id": waifu["id"],
                "guild": ctx.guild.id,
                "member": buyer[database.Member.c.member],
                "purchased_for": waifu["price"],
            },
        )

        await ctx.send(
            f"You're now in a relationship with {waifu['name']} "
            "<:SataniaThumb:575384688714317824>\nDon't lewd them! <:uwu:575372762583924757>"
        )

    @commands.command(name="sell")
    @commands.guild_only()
    @commands.check(lock_command)
    async def sell(self, ctx, *, search_str: str):
        """
        Sell a waifu, because you stopped loving them
        """
        engine = await database.prepare_engine()

        query = generate_search_query(search_str, limit=1)
        waifu = await engine.fetch_one(query=query)
        if waifu is None:
            return await ctx.send(
                "Waifu not found! Don't sell your imaginary waifus <:smug:575373306715439151>"
            )

        query = (
            database.PurchasedWaifu.select()
            .where(database.PurchasedWaifu.c.waifu_id == waifu["id"])
            .where(database.PurchasedWaifu.c.guild == ctx.guild.id)
            .where(database.PurchasedWaifu.c.member == ctx.author.id)
        )
        db_purchaser = await engine.fetch_one(query=query)
        if db_purchaser is None:
            return await ctx.send(
                "By what logic are you trying to sell "
                "which you don't own <:Eww:575373991640956938>"
            )

        selling_price = int(
            db_purchaser[database.PurchasedWaifu.c.purchased_for] * config.SELL_WAIFU_DEPRECIATION
        )

        await ctx.send(
            f"Want to break up with {waifu['name']} for sure?"
            f"You will get back {config.SELL_WAIFU_DEPRECIATION * 100}% of the cost, "
            f"{selling_price:,} <:PIC:668725298388271105>\n"
            "Reply with `confirm` in 60s or `exit` to cancel."
        )

        try:
            confirmed = await utils.wait_for_confirm(ctx)
            if not confirmed:
                return
        except asyncio.TimeoutError:
            return await ctx.send("Error: Timed out.")

        query = database.PurchasedWaifu.delete(None).where(
            database.PurchasedWaifu.c.id == db_purchaser[database.PurchasedWaifu.c.id]
        )
        await engine.execute(query=query)
        await add_money(ctx.author, selling_price)

        await ctx.send(
            f"You successfully broke up with {waifu['name']} and they are "
            "being sent back to the Dungeon! <:SataniaThumb:575384688714317824>"
        )

    async def toggle_favorite(self, ctx, search_str: str, favorite: bool = True):
        engine = await database.prepare_engine()

        query = generate_search_query(search_str, limit=1)
        waifu = await engine.fetch_one(query=query)
        if waifu is None:
            return await ctx.send("Waifu not found!")

        query = (
            database.PurchasedWaifu.select()
            .where(database.PurchasedWaifu.c.waifu_id == waifu["id"])
            .where(database.PurchasedWaifu.c.guild == ctx.guild.id)
            .where(database.PurchasedWaifu.c.member == ctx.author.id)
        )
        purchased_waifu = await engine.fetch_one(query=query)
        if purchased_waifu is None:
            await ctx.send(
                "You can't mark a waifu you don't own as a favorite <:smug:575373306715439151>"
            )
            return
        update_query = (
            database.PurchasedWaifu.update(None)
            .where(database.PurchasedWaifu.c.id == purchased_waifu[database.PurchasedWaifu.c.id])
            .values(favorite=favorite)
        )
        await engine.execute(update_query)
        if favorite:
            gender = "him" if waifu["gender"] == "m" else "her"
            await ctx.send(
                f"{waifu['name']} is delighted to hear you made {gender} "
                "your favorite! <:AilunaHug:575373643551473665>"
            )
        else:
            gender = "he" if waifu["gender"] == "m" else "she"
            await ctx.send(
                f"{waifu['name']} is heartbroken but {gender} "
                "respects your decision! <:Eww:575373991640956938>"
            )

    @commands.group(name="trade", invoke_without_command=True)
    @commands.guild_only()
    async def trade(self, ctx):
        """
        Trade a waifu with another user with either money or waifu!
        """
        await ctx.send(
            "**Welcome to Waifu Trade!**\n"
            "\nIf you wish to trade a waifu with another user for "
            f"money, use `{ctx.prefix}trade money <user> <waifu name or ID>`."
            "\nIf you wish to trade a waifu with another user for "
            f"another waifu, use `{ctx.prefix}trade waifu <user> <waifu name or ID>`.\n\n"
            f"Psst, you can use short forms, `{ctx.prefix}trade m` or `{ctx.prefix}trade w`!"
        )

    @trade.group(name="money", aliases=["m"])
    @commands.guild_only()
    @commands.check(lock_command)
    async def money_trade(self, ctx, receiver: discord.Member, *, waifu: str):
        """
        Inorganic Waifu-for-Money trades!
        Your friend wants your waifu but you don't want a waifu from them?
        No issues, trade with money!
        """
        engine = await database.prepare_engine()

        sender = ctx.author

        query = generate_search_query(waifu, limit=1)
        sender_waifu = await engine.fetch_one(query=query)

        if sender_waifu is None:
            return await ctx.send(
                "Waifu not found! Don't trade your imaginary waifus <:smug:575373306715439151>"
            )

        pwaifu_query = (
            database.PurchasedWaifu.select()
            .where(database.PurchasedWaifu.c.waifu_id == sender_waifu["id"])
            .where(database.PurchasedWaifu.c.guild == ctx.guild.id)
            .where(database.PurchasedWaifu.c.member == sender.id)
        )
        sender_pwaifu = await engine.fetch_one(query=pwaifu_query)
        if sender_pwaifu is None:
            return await ctx.send(
                "Hey! You can't trade a waifu which you don't own <:smug:575373306715439151>"
            )

        await ctx.send(
            f"{receiver.mention}, enter the price you want to "
            f"trade {sender_waifu['name']} for "
            "or enter `exit` to cancel trade."
        )

        try:
            price_txt = await utils.wait_for_message(ctx, user=receiver)
            if not price_txt:
                return
            if not price_txt.isdigit():
                return await ctx.send("Invalid input, cancelling trade...")
        except asyncio.TimeoutError:
            return await ctx.send("Error: Timed out.")

        price = int(price_txt)
        receiver_wallet = await database.fetch_wallet(receiver)
        if receiver_wallet < price:
            return await ctx.send(
                "You don't have enough balance to complete this trade! Cancelling trade..."
            )

        await ctx.send(
            f"{sender.mention}, do you confirm the trade "
            f"of your {sender_waifu['name']} "
            f"in exchange for {price} "
            f"<:PIC:668725298388271105> from {receiver.mention}?\n"
            "Enter Yes/No:"
        )

        try:
            confirmed = await utils.wait_for_confirm(ctx, user=sender)
            if not confirmed:
                return await ctx.send("Okay, Exiting...")
        except asyncio.TimeoutError:
            return await ctx.send("Error: Timed out.")

        if (await engine.fetch_one(query=pwaifu_query)) is None:
            return await ctx.send("Hey, don't try to cheat the system! Cancelling trade...")

        try:
            await database.remove_money(receiver, price)
        except errors.NotEnoughBalance:
            return await ctx.send("Hey, don't try to cheat the system! Cancelling trade...")

        query = database.Member.select().where(database.Member.c.member == receiver.id)
        db_receiver = await engine.fetch_one(query=query)

        query = database.PurchasedWaifu.delete(None).where(
            database.PurchasedWaifu.c.id == sender_pwaifu[database.PurchasedWaifu.c.id]
        )
        await engine.execute(query=query)
        await engine.execute(
            query=database.PurchasedWaifu.insert(None),
            values={
                "member_id": db_receiver[database.Member.c.id],
                "waifu_id": sender_waifu["id"],
                "guild": ctx.guild.id,
                "member": db_receiver[database.Member.c.member],
                "purchased_for": 0,
            },
        )
        await database.add_money(sender, price)

        await ctx.send("Trade successful! <:SataniaThumb:575384688714317824>")

    @trade.group(name="waifu")
    @commands.guild_only()
    @commands.check(lock_command)
    async def waifu_trade(self, ctx, receiver: discord.Member, *, send_waifu_txt: str):
        """
        Organic Waifu-for-Waifu trades! Go trade now with your friends (*assuming you have friends)
        """
        engine = await database.prepare_engine()

        sender = ctx.author

        query = generate_search_query(send_waifu_txt, limit=1)
        sender_waifu = await engine.fetch_one(query=query)

        if sender_waifu is None:
            return await ctx.send(
                "Waifu not found! Don't trade your imaginary waifus <:smug:575373306715439151>"
            )

        sender_pwaifu_query = (
            database.PurchasedWaifu.select()
            .where(database.PurchasedWaifu.c.waifu_id == sender_waifu["id"])
            .where(database.PurchasedWaifu.c.guild == ctx.guild.id)
            .where(database.PurchasedWaifu.c.member == sender.id)
        )
        sender_pwaifu = await engine.fetch_one(query=sender_pwaifu_query)
        if sender_pwaifu is None:
            return await ctx.send(
                "Hey! You can't trade a waifu which you don't own <:smug:575373306715439151>"
            )

        await ctx.send(
            f"{receiver.mention}, enter the name or ID of the waifu "
            f"you want to trade in exchange for {sender_waifu['name']} "
            "or enter `exit` to cancel trade."
        )

        try:
            recv_waifu_txt = await utils.wait_for_message(ctx, user=receiver)
        except asyncio.TimeoutError:
            return await ctx.send("Error: Timed out.")

        query = generate_search_query(recv_waifu_txt, limit=1)
        receiver_waifu = await engine.fetch_one(query=query)
        if receiver_waifu is None:
            return await ctx.send(
                "Waifu not found! Don't trade your imaginary waifus <:smug:575373306715439151>"
            )

        receiver_pwaifu_query = (
            database.PurchasedWaifu.select()
            .where(database.PurchasedWaifu.c.waifu_id == receiver_waifu["id"])
            .where(database.PurchasedWaifu.c.guild == ctx.guild.id)
            .where(database.PurchasedWaifu.c.member == receiver.id)
        )
        receiver_pwaifu = await engine.fetch_one(query=receiver_pwaifu_query)
        if receiver_pwaifu is None:
            return await ctx.send(
                "Hey! You can't trade a waifu which you don't own <:smug:575373306715439151>"
            )

        await ctx.send(
            f"{sender.mention}, do you confirm the trade "
            f"of your {sender_waifu['name']} "
            f"in exchange for {receiver.mention}'s "
            f"{receiver_waifu['name']}?\n"
            "Enter Yes/No:"
        )

        try:
            confirmed = await utils.wait_for_confirm(ctx, user=sender)
            if not confirmed:
                return await ctx.send("Okay, Exiting...")
        except asyncio.TimeoutError:
            return await ctx.send("Error: Timed out.")

        if (await engine.fetch_one(query=sender_pwaifu_query)) is None or (
            await engine.fetch_one(query=receiver_pwaifu_query) is None
        ):
            return await ctx.send("Hey, don't try to cheat the system! Cancelling trade...")

        query = database.PurchasedWaifu.delete(None).where(
            database.PurchasedWaifu.c.id.in_(
                [
                    sender_pwaifu[database.PurchasedWaifu.c.id],
                    receiver_pwaifu[database.PurchasedWaifu.c.id],
                ]
            )
        )

        await engine.execute(query=query)
        await engine.execute_many(
            query=database.PurchasedWaifu.insert(None),
            values=[
                {
                    "member_id": sender_pwaifu[database.PurchasedWaifu.c.member_id],
                    "waifu_id": receiver_pwaifu[database.PurchasedWaifu.c.waifu_id],
                    "guild": ctx.guild.id,
                    "member": sender_pwaifu[database.PurchasedWaifu.c.member],
                    "purchased_for": 0,
                },
                {
                    "member_id": receiver_pwaifu[database.PurchasedWaifu.c.member_id],
                    "waifu_id": sender_pwaifu[database.PurchasedWaifu.c.waifu_id],
                    "guild": ctx.guild.id,
                    "member": receiver_pwaifu[database.PurchasedWaifu.c.member],
                    "purchased_for": 0,
                },
            ],
        )

        await ctx.send("Trade successful! <:SataniaThumb:575384688714317824>")

    @commands.command(name="randomroll", aliases=["rr", "randomwaifu"])
    @commands.guild_only()
    async def random_waifu(self, ctx):
        """
        Get a random waifu/husbando at a discounted price.

        Amount of rolls per 3 hours:
        Normal user: 10 rolls
        Tier 1 donator: 30 rolls
        Tier 2 donator: 90 rolls
        """
        engine = await database.prepare_engine()

        fetch_query = database.Member.select().where(database.Member.c.member == ctx.author.id)
        waifu = await engine.fetch_one(query=fetch_query)
        member_tier = waifu[database.Member.c.tier]
        total_rolls = get_total_rolls(member_tier)

        key = f"{ctx.guild.id}:{ctx.author.id}"
        rolled, last_roll = self.random_waifu_counter.setdefault(key, (0, datetime.now()))
        left_rolls = total_rolls - rolled
        last_roll_interval = datetime.now() - last_roll

        if last_roll_interval.total_seconds() > config.ROLL_INTERVAL:
            rolled = 0
            left_rolls = total_rolls

        if left_rolls <= 0:
            tdelta = timedelta(seconds=config.ROLL_INTERVAL) - last_roll_interval
            return await ctx.send(
                f"You have no rolls left! Please try again in {tdelta}. "
                f"You can donate to the bot (see `{ctx.prefix}donate`) "
                "and get more rolls <a:thanks:699004469610020964>"
            )

        self.random_waifu_counter[key] = (rolled + 1, datetime.now())

        query = database.Waifu.select().order_by(sa.sql.func.random())
        waifu = await engine.fetch_one(query=query)

        query = (
            database.PurchasedWaifu.select()
            .where(database.PurchasedWaifu.c.waifu_id == waifu[database.Waifu.c.id])
            .where(database.PurchasedWaifu.c.guild == ctx.guild.id)
        )
        db_purchaser = await engine.fetch_one(query=query)
        purchaseable = db_purchaser is None
        purchaser = None
        if db_purchaser is not None:
            purchaser = ctx.guild.get_member(
                db_purchaser[database.PurchasedWaifu.c.member]
            ) or await ctx.guild.fetch_member(db_purchaser[database.PurchasedWaifu.c.member])

        gender = self.gender_table.get(waifu[database.Waifu.c.gender], "trap")
        name = waifu[database.Waifu.c.name]
        from_anime = waifu[database.Waifu.c.from_anime]
        price = int(waifu[database.Waifu.c.price] * config.PRICE_CUT)

        if purchaseable:
            description = (
                f"Hi! I am a {gender} from {from_anime}. "
                f"You need {price:,} <:PIC:668725298388271105> to buy me! "
                "React with the :heart: below to buy me! Hurry up, 10 seconds left."
            )
        else:
            if purchaser is not None:
                description = (
                    f"Hi! I am a {gender} from {from_anime}. "
                    f"I am already in a relationship with {purchaser}."
                )
            else:
                description = (
                    f"Hi! I am a {gender} from {from_anime}. "
                    "I am stuck with someone who bought me and left this server! "
                    f"Rescue me with `{ctx.prefix}rescuewaifus`."
                )

        embed = discord.Embed(
            title=name,
            description=description,
            color=ctx.author.colour,
        )

        images = []
        if waifu[database.Waifu.c.image_url] is not None:
            images = waifu[database.Waifu.c.image_url].split(",")
            embed.set_image(url=images[0])

        embed.add_field(name="From", value=from_anime, inline=False)
        embed.add_field(name="Cost", value=f"{price:,} <:PIC:668725298388271105>")
        embed.add_field(name="ID", value=waifu[database.Waifu.c.id])
        embed.add_field(name="Gender", value=gender)
        if len(images) > 1:
            embed.add_field(
                name="Image",
                inline=False,
                value=f"**Showing: 1/{len(images)}**",
            )
        if purchaser is not None:
            purchased_for = db_purchaser[database.PurchasedWaifu.c.purchased_for]
            embed.set_footer(
                text=f"Purchased by {purchaser} for {purchased_for} PIC.",
                icon_url=purchaser.avatar_url_as(size=128),
            )

        msg = await ctx.send(embed=embed)

        if not purchaseable:
            return

        await msg.add_reaction("❤")
        if len(images) > 1:
            await msg.add_reaction("⬅")
            await msg.add_reaction("➡")

        def check(reaction, user):
            return not user.bot and reaction.message.id == msg.id

        curr_page = 0
        purchased = False
        try:
            while not purchased:
                reaction, purchaser = await ctx.bot.wait_for(
                    "reaction_add", timeout=10.0, check=check
                )
                react_emoji = str(reaction.emoji)
                if react_emoji in ["➡", "⬅"]:
                    if react_emoji == "➡" and curr_page < len(images) - 1:
                        curr_page += 1
                    elif react_emoji == "⬅" and curr_page > 0:
                        curr_page -= 1

                    embed.set_image(url=images[curr_page])
                    embed.add_field(
                        name="Image",
                        inline=False,
                        value=f"**Showing: {curr_page + 1}/{len(images)}**",
                    )
                    await msg.edit(embed=embed)
                    await msg.remove_reaction(react_emoji, purchaser)
                elif react_emoji == "❤":
                    try:
                        await database.remove_money(purchaser, price)
                    except errors.NotEnoughBalance:
                        return await ctx.send(
                            "You don't have enough coins to buy me <:smug:575373306715439151>"
                        )
                    purchased = True
        except asyncio.TimeoutError:
            embed.description = "You were too late to buy me, bye-bye!"
            await msg.edit(embed=embed)
            try:
                await msg.clear_reactions()
            except discord.errors.Forbidden:
                pass
            return

        try:
            await msg.clear_reactions()
        except discord.errors.Forbidden:
            pass

        query = database.Member.select().where(database.Member.c.member == purchaser.id)
        buyer = await engine.fetch_one(query=query)
        await engine.execute(
            query=database.PurchasedWaifu.insert(None),
            values={
                "member_id": buyer[database.Member.c.id],
                "waifu_id": waifu[database.Waifu.c.id],
                "guild": ctx.guild.id,
                "member": buyer[database.Member.c.member],
                "purchased_for": price,
            },
        )
        embed.description = f"I am now in a relationship with {purchaser.name}!"
        await msg.edit(embed=embed)

        await ctx.send(
            "Successfully bought waifu at an unbelievable price "
            "<:SataniaThumb:575384688714317824>. Don't lewd them!"
        )

    @commands.command(name="rollsleft", aliases=["rolls"])
    @commands.guild_only()
    async def rolls_left(self, ctx):
        """
        Check how many rolls you have left. Resets every 3 hours
        """
        engine = await database.prepare_engine()

        query = database.Member.select().where(database.Member.c.member == ctx.author.id)
        db_member = await engine.fetch_one(query=query)
        member_tier = db_member[database.Member.c.tier]
        total_rolls = get_total_rolls(member_tier)

        key = f"{ctx.guild.id}:{ctx.author.id}"
        rolled, last_roll = self.random_waifu_counter.setdefault(key, (0, datetime.now()))
        last_roll_interval = datetime.now() - last_roll

        if last_roll_interval.total_seconds() > config.ROLL_INTERVAL:
            return await ctx.send(
                f"You have {total_rolls} available!\n"
                f"You can donate to the bot (see `{ctx.prefix}donate`) "
                "and get more rolls <a:thanks:699004469610020964>"
            )

        left_rolls = total_rolls - rolled

        tdelta = datetime.utcfromtimestamp(
            (timedelta(seconds=config.ROLL_INTERVAL) - last_roll_interval).total_seconds()
        ).strftime("%H Hours %M Minutes")

        left_rolls = "no" if left_rolls <= 0 else left_rolls
        await ctx.send(
            f"You have {left_rolls} rolls left! "
            f"Rolls reset in {tdelta}.\n"
            f"You can donate to the bot (see `{ctx.prefix}donate`) "
            "and get more rolls <a:thanks:699004469610020964>"
        )

    @commands.command(name="sellharem")
    @commands.guild_only()
    @commands.check(lock_command)
    async def sell_harem(self, ctx):
        """
        Sell your entire harem because you choose to get a life
        """
        engine = await database.prepare_engine()

        query = (
            database.PurchasedWaifu.select()
            .where(database.PurchasedWaifu.c.member == ctx.author.id)
            .where(database.PurchasedWaifu.c.guild == ctx.guild.id)
        )
        all_waifus = await engine.fetch_all(query=query)
        if len(all_waifus) == 0:
            return await ctx.send("You don't have any harem in the first place, sad!")

        total_cost = int(
            sum([i[database.PurchasedWaifu.c.purchased_for] for i in all_waifus])
            * config.SELL_WAIFU_DEPRECIATION
        )

        await ctx.send(
            "Are you sure you want to sell all your harem?\n"
            f"You will get back {total_cost} <:PIC:668725298388271105>.\n\n"
            "Type `confirm` to confirm in 60s or `exit` to cancel."
        )

        try:
            confirmed = await utils.wait_for_confirm(ctx)
            if not confirmed:
                return
        except asyncio.TimeoutError:
            return await ctx.send("Error: Timed out.")

        ids = [i[database.PurchasedWaifu.c.id] for i in all_waifus]
        await engine.execute(
            database.PurchasedWaifu.delete(None).where(database.PurchasedWaifu.c.id.in_(ids))
        )
        await database.add_money(ctx.author, total_cost)

        await ctx.send(f"Done! You got back {total_cost} <:PIC:668725298388271105>.")

    @commands.command("moneytrade", hidden=True)
    async def deprecated_moneytrade(self, ctx):
        await ctx.send(
            f"This command has been replaced with `{ctx.prefix}trade money`."
            f"\nPlease check out `{ctx.prefix}trade`!"
        )

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        await unlock_command(ctx)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await unlock_command(ctx)


def prepare_harem_page(purchased_waifus, waifu_data):
    txt = ""
    for i, row in purchased_waifus:
        data = waifu_data[row[database.PurchasedWaifu.c.waifu_id]]
        favorite_txt = " :heart:" if row[database.PurchasedWaifu.c.favorite] else ""
        txt += (
            f"{i}: **__{data[database.Waifu.c.name]}__**{favorite_txt}\n"
            f"**ID:** {data[database.Waifu.c.id]} | "
            f"**Purchased For:** {row[database.PurchasedWaifu.c.purchased_for]} "
            f"<:PIC:668725298388271105> | **From:** {data[database.Waifu.c.from_anime]}\n"
        )
    return txt


def generate_search_query(inp, limit=30):
    query = database.Waifu.select()
    if inp.isdigit():
        query = query.where(database.Waifu.c.id == int(inp))
    else:
        union_list = [
            sa.select([database.Waifu, database.Waifu.c.name.op("<->")(inp).label("sim")]),
            sa.select(
                [
                    database.Waifu,
                    database.Waifu.c.from_anime.op("<->")(inp).label("sim"),
                ]
            ),
        ]
        query = sa.union(*union_list)
        columns = [
            sa.column("id"),
            sa.column("name"),
            sa.column("from_anime"),
            sa.column("gender"),
            sa.column("price"),
            sa.column("description"),
            sa.column("image_url"),
        ]
        query = sa.select(
            [
                *columns,
                sa.sql.func.min(sa.column("sim")).label("sim"),
            ]
        ).select_from(query.alias("q"))
        query = query.group_by(*columns)
        query = query.order_by(sa.asc("sim"))
    query = query.limit(limit)
    return query


SORT_FILTER_REGEX = re.compile(r"([a-z]+)[_\-+]?([a-z]+)?")


def filter_harem(purchased_waifus, waifu_data, filter_opts):
    def sort_id(reverse=False):
        purchased_waifus.sort(key=lambda x: x[database.PurchasedWaifu.c.waifu_id], reverse=reverse)

    def sort_price(reverse=False):
        purchased_waifus.sort(
            key=lambda x: x[database.PurchasedWaifu.c.purchased_for], reverse=reverse
        )

    def sort_name(reverse=False):
        purchased_waifus.sort(
            key=lambda x: waifu_data[x[database.PurchasedWaifu.c.waifu_id]][database.Waifu.c.name],
            reverse=reverse,
        )

    def sort_series(reverse=False):
        purchased_waifus.sort(
            key=lambda x: waifu_data[x[database.PurchasedWaifu.c.waifu_id]][
                database.Waifu.c.from_anime
            ],
            reverse=reverse,
        )

    sort_headers = {
        "name": sort_name,
        "series": sort_series,
        "anime": sort_series,
        "id": sort_id,
        "price": sort_price,
    }
    sort_types = ("asc", "desc")
    gender_opts = {
        "waifu": "f",
        "husbando": "m",
        "female": "f",
        "male": "m",
    }

    for opt in filter_opts:
        opt = opt.lower()

        if opt in gender_opts:
            g_opt = gender_opts[opt]
            purchased_waifus = [
                x
                for x in purchased_waifus
                if waifu_data[x[database.PurchasedWaifu.c.waifu_id]][database.Waifu.c.gender]
                == g_opt
            ]
            continue

        s_opt = SORT_FILTER_REGEX.findall(opt)
        if len(s_opt) != 1:
            continue

        s_opt = s_opt[0]
        s_head = sort_headers.get(s_opt[0])
        if not s_head:
            continue

        s_type = s_opt[1]
        s_type = s_type if s_type in sort_types else sort_types[0]
        reverse = s_type == "desc"

        s_head(reverse)

        break  # only 1 sort type allowed

    purchased_waifus.sort(key=lambda x: x[database.PurchasedWaifu.c.favorite], reverse=True)

    return purchased_waifus


def get_total_rolls(member_tier):
    if member_tier >= config.DEV_TIER:
        return 3 * 3600  # Virtually unlimited for devs, lol.
    if member_tier >= config.DONATOR_TIER_2:
        return 90
    if member_tier >= config.DONATOR_TIER_1:
        return 30
    return 10
