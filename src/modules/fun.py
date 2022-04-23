import datetime
import html
import io
import json
import textwrap
import typing
from random import randint
from urllib.parse import quote

import aiohttp
import discord
import owoify
from discord.ext import commands
from PIL import Image, ImageDraw

import utils


class FunCommands(commands.Cog, name="Fun"):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.latest_xkcd_id = -1
        self.last_xkcd_latest_fetch = datetime.datetime.now()

    @commands.command(name="avatar")
    async def avatar(self, ctx, user: typing.Optional[discord.Member]):
        """
        View yours or someone else's avatar
        """
        user = user or ctx.author
        url = str(user.avatar_url_as(size=1024))
        embed = discord.Embed(
            title=f"{user}'s Avatar",
            url=url,
            colour=user.colour,
        )
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name="chucknorris")
    @utils.typing_indicator()
    async def chuck_norris(self, ctx):
        """
        A Chuck Norris about joke
        """
        resp_txt = await self._fetch_text("http://api.icndb.com/jokes/random", is_json=True)
        joke = resp_txt["value"]["joke"]
        joke = html.unescape(joke)
        await ctx.send(joke)

    @commands.command(name="dadjoke")
    @utils.typing_indicator()
    async def dad_joke(self, ctx):
        """
        A (bad) dad joke
        """
        headers = {"Accept": "application/json"}
        resp_txt = await self._fetch_text("https://icanhazdadjoke.com", headers, is_json=True)
        joke = resp_txt["joke"]
        await ctx.send(joke)

    @commands.command(name="catfact")
    @utils.typing_indicator()
    async def cat_fact(self, ctx):
        """
        Cat facts
        """
        resp_txt = await self._fetch_text("https://catfact.ninja/fact", is_json=True)
        fact = resp_txt["fact"]
        await ctx.send(fact)

    @commands.command(name="xkcd")
    @utils.typing_indicator()
    async def xkcd(self, ctx):
        """
        Random xkcd comic strip
        """
        now = datetime.datetime.now()
        if self.latest_xkcd_id == -1 or (now - self.last_xkcd_latest_fetch).days > 1:
            latest = await self._fetch_text("https://xkcd.com/info.0.json")
            last = json.loads(latest)["num"]
            self.latest_xkcd_id = last
            self.last_xkcd_latest_fetch = now
        rand_id = randint(1, self.latest_xkcd_id)
        random = await self._fetch_text(f"https://xkcd.com/{rand_id}/info.0.json")
        img_url = json.loads(random)["img"]
        embed = discord.Embed(
            title=f"XKCD #{rand_id}",
            url=f"https://xkcd.com/{rand_id}",
            colour=ctx.author.color,
        )
        embed.set_image(url=img_url)
        await ctx.send(embed=embed)

    @commands.command(name="lmgtfy")
    @utils.typing_indicator()
    async def lmgtfy(self, ctx, query: str):
        """
        Let me google that for you
        """
        url = f"https://lmgtfy.com/?q={quote(query)}"
        embed = discord.Embed(
            title="LMGTFY",
            colour=ctx.author.color,
            url=url,
            description="[{0}]({1})".format(query, url.replace("_", r"\_")),
        )
        await ctx.send(embed=embed)

    @commands.command(name="urbandictionary", aliases=["urbandict", "ud"])
    @utils.typing_indicator()
    async def urban_dictionary(self, ctx, query: str):
        """
        Search urban dictionary
        """
        resp_txt = await self._fetch_text(
            f"https://api.urbandictionary.com/v0/define?term={quote(query)}"
        )

        ud_reply = json.loads(resp_txt)["list"]
        if len(ud_reply) == 0:
            await ctx.send("No results found for this search string.")
            return

        exact_ud_reply = [i for i in ud_reply if i["word"].lower() == query.lower()]
        if len(exact_ud_reply) > 0:
            ud_reply = exact_ud_reply
        rand_id = randint(0, len(ud_reply) - 1)
        ud_def = ud_reply[rand_id]

        embed = discord.Embed(
            title=f"Urban Dictionary: {ud_def['word']}",
            url=ud_def["permalink"],
            colour=ctx.author.color,
        )
        definition = ud_def["definition"].replace("[", "").replace("]", "")
        if len(definition) > 1980:
            definition = definition[:1980] + "..."
        embed.description = f"**Definition**\n\n{definition}"

        example = ud_def["example"].replace("[", "").replace("]", "")
        if len(example) > 990:
            example = example[:990] + "..."
        embed.add_field(name="Example", inline=False, value=example)
        embed.add_field(name="Author", value=ud_def["author"])
        embed.add_field(
            name="Votes",
            value=f"{ud_def['thumbs_up']} :thumbsup: {ud_def['thumbs_down']} :thumbsdown:",
        )

        await ctx.send(embed=embed)

    @commands.command(name="8ball")
    @utils.typing_indicator()
    async def eight_ball(self, ctx):
        """
        Get life advice.
        """
        choices = [
            "Not so sure",
            "42",
            "Most likely",
            "Absolutely not",
            "Outlook is good",
            "I see good things happening",
            "Never",
            "Negative",
            "Could be",
            "Unclear, ask again",
            "Yes",
            "No",
            "Possible, but not probable",
        ]
        rand_id = randint(0, len(choices) - 1)
        await ctx.send(f"The 8-ball reads: {choices[rand_id]}")

    @commands.command(name="cowsay")
    @utils.typing_indicator()
    async def cowsay(self, ctx, text: str):
        """
        Cow says moo, and you can order the cow to speak for you
        """
        text = discord.utils.escape_mentions(text).replace("`", "\u200b`")
        await ctx.send("```css\n" + _cowsay(text) + "```")

    @commands.command(name="cook")
    @utils.typing_indicator()
    async def cook_user(self, ctx, user: discord.Member):
        """
        Cook someone tastily
        """
        profile_pic = Image.open(
            io.BytesIO(
                await self._get_bytes_from_url(str(user.avatar_url_as(format="png", size=256)))
            ),
            "r",
        )
        profile_pic = profile_pic.resize((294, 294), Image.ANTIALIAS)
        background = Image.open("assets/plate.jpg", "r")
        bigsize = (profile_pic.size[0] * 3, profile_pic.size[1] * 3)
        mask = Image.new("L", bigsize, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + bigsize, fill=255)
        mask = mask.resize(profile_pic.size, Image.ANTIALIAS)
        profile_pic.putalpha(mask)
        _w, _h = profile_pic.size
        pts = (348 - _w // 2, 231 - _h // 2)
        background.paste(profile_pic, pts, profile_pic)
        byte_io = io.BytesIO()
        background.save(byte_io, "PNG")
        byte_io.flush()
        byte_io.seek(0)

        await ctx.send(
            file=discord.File(fp=byte_io, filename=f'cooked_{user.name.replace(" ", "_")}.png')
        )

    @commands.command(name="hornyjail", aliases=["hjail"])
    @utils.typing_indicator()
    async def horny_jail(self, ctx, user: discord.Member):
        """
        Send someone to the horny jail
        """
        profile_pic = Image.open(
            io.BytesIO(
                await self._get_bytes_from_url(str(user.avatar_url_as(format="png", size=256)))
            ),
            "r",
        )
        profile_pic = profile_pic.resize((294, 294), Image.ANTIALIAS)
        background = Image.open("assets/hjail.png", "r")
        bigsize = (profile_pic.size[0] * 3, profile_pic.size[1] * 3)
        mask = Image.new("L", bigsize, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + bigsize, fill=255)
        mask = mask.resize(profile_pic.size, Image.ANTIALIAS)
        profile_pic.putalpha(mask)
        _w, _h = profile_pic.size
        pts = (1074 - _w // 2, 582 - _h // 2)
        background.paste(profile_pic, pts, profile_pic)
        byte_io = io.BytesIO()
        background.save(byte_io, "PNG")
        byte_io.flush()
        byte_io.seek(0)

        await ctx.send(
            file=discord.File(fp=byte_io, filename=f'jailed_{user.name.replace(" ", "_")}.png')
        )

    @commands.command(name="owoify")
    async def owoify_text(self, ctx, *, text: str):
        """
        Genyerate swomwe cursed OwO text
        """
        cursed_text = owoify.owoify(text, "owo")
        allowed_mentions = discord.AllowedMentions(everyone=False, users=False, roles=False)
        await ctx.send(cursed_text, allowed_mentions=allowed_mentions)

    @commands.command(name="uwuify")
    async def uwuify_text(self, ctx, *, text: str):
        """
        Genyewate swomwe cuwsed UwU text (◕ᴥ◕)
        """
        cursed_text = owoify.owoify(text, "uwu")
        allowed_mentions = discord.AllowedMentions(everyone=False, users=False, roles=False)
        await ctx.send(cursed_text, allowed_mentions=allowed_mentions)

    @commands.command(name="uvuify")
    async def uvuify_text(self, ctx, *, text: str):
        """
        Genyewate swowomwe cuwsed UvU text (╯°□°）╯︵ ┻━┻ pwease (・`ω´・)'
        """
        cursed_text = owoify.owoify(text, "uvu")
        allowed_mentions = discord.AllowedMentions(everyone=False, users=False, roles=False)
        await ctx.send(cursed_text, allowed_mentions=allowed_mentions)

    async def _fetch_text(self, url, headers=None, is_json=False):
        headers = headers or {}

        async with self.session.get(url, headers=headers) as resp:
            if is_json:
                return await resp.json()
            return await resp.text()

    async def _get_bytes_from_url(self, url):
        async with self.session.get(url) as resp:
            bytes_ = await resp.read()
            return bytes_


def _cowsay(string, length=40):
    return build_bubble(string, length) + build_cow()


def build_cow():
    return r"""
         \   ^__^
          \  (oo)\_______
             (__)\       )\/\\
                 ||----w |
                 ||     ||
    """


def build_bubble(string, length=40):
    bubble = []
    lines = normalize_text(string, length)
    bordersize = len(lines[0])
    bubble.append("  " + "-" * bordersize)
    for index, line in enumerate(lines):
        border = get_border(lines, index)
        bubble.append("%s %s %s" % (border[0], line, border[1]))
        bubble.append("  " + "-" * bordersize)
    return "\n".join(bubble)


def normalize_text(string, length):
    lines = textwrap.wrap(string, length)
    maxlen = len(max(lines, key=len))
    return [line.ljust(maxlen) for line in lines]


def get_border(lines, index):
    if len(lines) < 2:
        return ["<", ">"]
    if index == 0:
        return ["/", "\\"]
    if index == len(lines) - 1:
        return ["\\", "/"]
    return ["|", "|"]
