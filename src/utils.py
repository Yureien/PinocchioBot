import asyncio
import functools

import discord
from discord.ext import commands

import config
import database
import errors

num_to_emote = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "keycap_ten",
}
num_to_uni_emote = {
    0: "0⃣",
    1: "1⃣",
    2: "2⃣",
    3: "3⃣",
    4: "4⃣",
    5: "5⃣",
    6: "6⃣",
    7: "7⃣",
    8: "8⃣",
    9: "9⃣",
    10: "🔟",
}
uni_emote_to_num = {
    "0⃣": 0,
    "1⃣": 1,
    "2⃣": 2,
    "3⃣": 3,
    "4⃣": 4,
    "5⃣": 5,
    "6⃣": 6,
    "7⃣": 7,
    "8⃣": 8,
    "9⃣": 9,
    "🔟": 10,
}


async def paginate_embed(ctx, embed, total_pages, modifier_func):
    og_msg = await ctx.send(embed=embed)
    if total_pages <= 1:
        return

    curr_page = 0

    await og_msg.add_reaction("⬅")
    await og_msg.add_reaction("➡")

    def check(reaction, user):
        return not user.bot and reaction.message.id == og_msg.id

    seen = False
    try:
        while not seen:
            reaction, user = await ctx.bot.wait_for("reaction_add", timeout=120.0, check=check)
            if str(reaction.emoji) == "➡":
                if curr_page < total_pages - 1:
                    curr_page += 1
                    await modifier_func(page_num=curr_page, direction="forward")
                    await og_msg.edit(embed=embed)
                try:
                    await og_msg.remove_reaction("➡", user)
                except discord.errors.Forbidden:
                    pass
            elif str(reaction.emoji) == "⬅":
                if curr_page > 0:
                    curr_page -= 1
                    await modifier_func(page_num=curr_page, direction="backward")
                    await og_msg.edit(embed=embed)
                try:
                    await og_msg.remove_reaction("⬅", user)
                except discord.errors.Forbidden:
                    pass
    except asyncio.TimeoutError:
        try:
            await og_msg.clear_reactions()
        except discord.errors.Forbidden:
            pass
        return


def chunks(list_, division):
    for i in range(0, len(list_), division):
        yield list_[i : i + division]


def smart_chunks(list_, max_line):
    _ll = []
    _l = []
    _wc = 0
    for i in list_:
        _wc += len(i)
        if _wc > max_line:
            _ll.append(_l)
            _l = []
            _wc = len(i)
        _l.append(i)
    if len(_l) > 0:
        _ll.append(_l)
    return _ll


async def wait_for_message(ctx, timeout=60, user=None):
    user = user or ctx.author

    def check(m_ctx):
        return m_ctx.channel.id == ctx.channel.id and m_ctx.author.id == user.id

    msg = await ctx.bot.wait_for("message", check=check, timeout=timeout)
    if msg.content.lower() in ["exit", "quit", "cancel"]:
        await ctx.send("Okay, exiting...")
        return False
    return msg.content


async def wait_for_confirm(ctx, max_times=3, timeout=60, user=None):
    sure = False
    while not sure and max_times > 0:
        resp = await wait_for_message(ctx, timeout=timeout, user=user)
        if resp is False or resp.lower() in (
            "no",
            "n",
            "false",
            "f",
            "0",
            "disable",
            "off",
            "refuse",
        ):
            return False
        if resp is not None and resp.lower() in (
            "yes",
            "y",
            "true",
            "t",
            "1",
            "enable",
            "on",
            "confirm",
        ):
            return True
        await ctx.send("Respond properly. Write `exit` to exit.")
        max_times -= 1
    await ctx.send("Exited max tries, exiting...")
    return False


def typing_indicator():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(self, ctx, *args, **kwargs):
            async with ctx.typing():
                await func(self, ctx, *args, **kwargs)

        return wrapped

    return wrapper


def ensure_bot_ready():
    def predicate(ctx):
        if not ctx.bot.is_ready():
            raise errors.BotNotReady
        return True

    return commands.check(predicate)


def check_tier_matches(tier):
    async def check(ctx):
        engine = await database.prepare_engine()
        member = ctx.author
        fetch_query = database.Member.select().where(database.Member.c.member == member.id)
        conn = await engine.fetch_one(query=fetch_query)
        member_tier = conn[database.Member.c.tier]
        can_access = member_tier >= tier

        if not can_access:
            if tier > config.DONATOR_TIER_2:
                await ctx.send(
                    "You do not have sufficient privileges to use this command! "
                    "This is a developer-only command."
                )
            else:
                await ctx.send(
                    "This is a donator-only command! Maybe try upgrading "
                    f"to a donator plan using `{ctx.prefix}donate`?"
                )

        return can_access

    return check
