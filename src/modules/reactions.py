import typing

import aiohttp
import discord
from discord.ext import commands

import config


def preset_gif_command(gif_name=None, action="", requires_mention=False):
    mention_type = typing.Union[discord.Member, str]
    if not requires_mention:
        mention_type = typing.Optional[mention_type]

    async def _gif(self, ctx, mentions: mention_type, *args):
        if isinstance(mentions, (discord.User, discord.Member)):
            mention_name = mentions.name if mentions != ctx.author else "themself ;-;"
        else:
            if mentions == "@here":
                mention_name = "everyone here!"
            elif mentions == "@everyone":
                mention_name = "everyone!"
            else:
                mention_name = f"{mentions} {' '.join(args)}"

        if requires_mention:
            title = f"{ctx.author.name} {action} {mention_name}"
        else:
            title = action.capitalize()

        gif_url = await self.get_gif_url(f"anime {gif_name}")
        embed = discord.Embed(title=title, color=ctx.author.colour)
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    reaction_help = (
        f"React to someone with {gif_name}!" if requires_mention else f"React with {gif_name}!"
    )
    return commands.command(gif_name, help=reaction_help)(_gif)


class ReactionCommands(commands.Cog, name="Reactions"):
    def __init__(self, bot):
        self.bot = bot
        self.tenor_anon_id = None

    async def get_gif_url(self, search_string):
        async with aiohttp.ClientSession() as session:
            if self.tenor_anon_id is None:
                async with session.get(
                    f"https://api.tenor.com/v1/anonid?key={config.TENOR_API_TOKEN}"
                ) as resp:
                    resp_json = await resp.json()
                    self.tenor_anon_id = resp_json["anon_id"]

            search_url = (
                "https://api.tenor.com/v1/random?limit=1&media_filter=minimal&"
                f"q={search_string}&key={config.TENOR_API_TOKEN}&anon_id={self.tenor_anon_id}"
            )
            async with session.get(search_url) as resp:
                resp_json = await resp.json()
                url = resp_json["results"][0]["media"][0]["gif"]["url"]
                return url

    @commands.command("gif")
    async def gif(self, ctx, search_str: typing.Optional[str]):
        gif_url = await self.get_gif_url(search_str)
        embed = discord.Embed(title=search_str.capitalize(), color=ctx.author.colour)
        embed.set_image(url=gif_url)
        embed.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url_as(size=64))
        await ctx.send(embed=embed)

    jojo = preset_gif_command("jojo", "*Jojo*")
    megumin = preset_gif_command("megumin", "*Explosion Loli*")
    satania = preset_gif_command("satania", "*Great Archdemon*")
    facepalm = preset_gif_command("facepalm", "*Facepalms*")
    cry = preset_gif_command("cry", "*Cries*")
    laugh = preset_gif_command("laugh", "*Laughs*")
    confused = preset_gif_command("confused", "*Confused*")
    pout = preset_gif_command("pout", "*Pouts*")
    dance = preset_gif_command("dance", "*Dances*")
    cuddle = preset_gif_command("cuddle", "*Cuddles*")
    nom = preset_gif_command("nom", "*Nom Nom*")
    lick = preset_gif_command("lick", "*Lick Lick*")
    think = preset_gif_command("think", "*think*")
    shrug = preset_gif_command("shrug", "*Shrugs*")
    owo = preset_gif_command("owo", "*OwO*")
    uwu = preset_gif_command("uwu", "*UwU*")
    eyeroll = preset_gif_command("eyeroll", "*Rolls eyes*")
    lewd = preset_gif_command("lewd", "*LEWD ALERT*")
    stare = preset_gif_command("stare", "*Stares*")
    triggered = preset_gif_command("triggered", "*Triggered*")
    hug = preset_gif_command("hug", "hugs", True)
    kiss = preset_gif_command("kiss", "kisses", True)
    pat = preset_gif_command("pat", "pats", True)
    bite = preset_gif_command("bite", "bites", True)
    stab = preset_gif_command("stab", "stabs", True)
    shoot = preset_gif_command("shoot", "shoots", True)
    seduce = preset_gif_command("seduce", "seduces", True)
    kick = preset_gif_command("kick", "kicks", True)
    slap = preset_gif_command("slap", "slaps", True)
    punch = preset_gif_command("punch", "punches", True)
    poke = preset_gif_command("poke", "pokes", True)
