import io

import aiohttp
import discord
from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont

import database


class TasksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        if self.bot.discoin_client:
            self.discoin_watcher.start()  # pylint: disable=no-member

    def cog_unload(self):
        if self.bot.discoin_client:
            self.discoin_watcher.cancel()  # pylint: disable=no-member

    @tasks.loop(seconds=30)
    async def discoin_watcher(self):
        await self.bot.wait_until_ready()

        transactions = await self.bot.discoin_client.fetch_transactions()
        for i in transactions:
            if i.handled:
                continue

            transaction = await self.bot.discoin_client.handle_transaction(i.id)
            user = self.bot.get_user(int(transaction.user_id))

            await database.add_money(user, round(transaction.payout))

            embed = discord.Embed(
                title=(
                    "<:Discoin:357656754642747403> Recieved "
                    f"{round(transaction.payout)} <:PIC:668725298388271105>!"
                ),
                description="Recieved coins via exchange!",
                timestamp=transaction.timestamp,
            )
            embed.add_field(
                name=f"{transaction.currency_from} Exchanged", value=transaction.amount
            )
            embed.add_field(
                name="Pinocchio Coins <:PIC:668725298388271105> (PIC) Recieved",
                value=round(transaction.payout),
            )
            embed.add_field(
                name="Transaction Receipt",
                inline=False,
                value=(
                    f"[{transaction.id}]"
                    f"(https://dash.discoin.zws.im/#/transactions/{transaction.id}/show)"
                ),
            )
            embed.set_footer(
                text=str(user),
                icon_url=user.avatar_url_as(size=128),
            )

            await user.send(embed=embed)


async def make_join_leave_image(image_url, header, subtitle):
    async with aiohttp.ClientSession() as session:
        async with session.get(str(image_url)) as resp:
            image_bytes = await resp.read()

    profile_pic = Image.open(io.BytesIO(image_bytes), "r")
    profile_pic = profile_pic.resize((160, 160), Image.ANTIALIAS)
    background = Image.open("assets/background_1.jpg", "r")
    font_1 = ImageFont.truetype("assets/DiscordFont.otf", 28)
    font_2 = ImageFont.truetype("assets/DiscordFont.otf", 20)
    bigsize = (profile_pic.size[0] * 3, profile_pic.size[1] * 3)
    mask = Image.new("L", bigsize, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + bigsize, fill=255)
    mask = mask.resize(profile_pic.size, Image.ANTIALIAS)
    profile_pic.putalpha(mask)
    background.paste(profile_pic, (240, 48), profile_pic)
    draw = ImageDraw.Draw(background)
    _w, _ = draw.textsize(header, font=font_1)
    draw.text(((640 - _w) / 2, 240), header, font=font_1)
    _w, _ = draw.textsize(subtitle, font=font_2)
    draw.text(((640 - _w) / 2, 290), subtitle, font=font_2)

    byte_io = io.BytesIO()
    background.save(byte_io, "PNG")
    byte_io.flush()
    byte_io.seek(0)

    return discord.File(fp=byte_io, filename="discord.png")


async def send_on_member_join(member):
    engine = await database.prepare_engine()

    query = database.Guild.select().where(database.Guild.c.guild == member.guild.id)
    db_guild = await engine.fetch_one(query=query)

    channel = member.guild.get_channel(db_guild[database.Guild.c.join_leave_channel])
    welcome_str = db_guild[database.Guild.c.welcome_str]
    if channel is None or welcome_str is None:
        return

    img = await make_join_leave_image(
        member.avatar_url,
        f"{member} has joined",
        welcome_str,
    )
    await channel.send(file=img)


async def send_on_member_leave(member):
    engine = await database.prepare_engine()

    query = database.Guild.select().where(database.Guild.c.guild == member.guild.id)
    db_guild = await engine.fetch_one(query=query)

    channel = member.guild.get_channel(db_guild[database.Guild.c.join_leave_channel])
    leave_str = db_guild[database.Guild.c.leave_str]
    if channel is None or leave_str is None:
        return

    img = await make_join_leave_image(
        member.avatar_url,
        f"{member} has left",
        leave_str,
    )
    await channel.send(file=img)
